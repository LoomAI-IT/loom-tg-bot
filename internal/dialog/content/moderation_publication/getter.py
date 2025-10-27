from aiogram import Bot
from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method

from internal.dialog.helpers import StateManager

from internal.dialog.content.moderation_publication.helpers import (
    ImageManager, PublicationManager, SocialNetworkManager, DateTimeFormatter
)


class ModerationPublicationGetter(interface.IModerationPublicationGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            loom_employee_client: interface.ILoomEmployeeClient,
            loom_content_client: interface.ILoomContentClient,
            loom_domain: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.loom_content_client = loom_content_client
        self.loom_employee_client = loom_employee_client
        self.state_repo = state_repo
        self.loom_domain = loom_domain

        # Инициализация вспомогательных классов
        self.state_manager = StateManager(
            state_repo=self.state_repo
        )
        self._publication_manager = PublicationManager(
            self.logger,
            self.bot,
            self.loom_content_client,
        )
        self._image_manager = ImageManager(
            logger=self.logger,
            bot=self.bot,
            loom_domain=self.loom_domain,
        )
        self.__social_network_manger = SocialNetworkManager(
            logger=self.logger
        )
        self._datetime_formatter = DateTimeFormatter()

    @auto_log()
    @traced_method()
    async def get_moderation_list_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self.state_manager.get_state(dialog_manager)

        publications = await self.loom_content_client.get_publications_by_organization(
            organization_id=state.organization_id
        )

        moderation_publications = [
            pub.to_dict() for pub in publications
            if pub.moderation_status == "moderation"
        ]

        if not moderation_publications:
            self.logger.info("Нет публикаций на модерации")
            return {
                "has_publications": False,
                "publications_count": 0,
                "period_text": "",
            }

        dialog_manager.dialog_data["moderation_list"] = moderation_publications

        if "current_index" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["current_index"] = 0

        current_index = dialog_manager.dialog_data["current_index"]
        current_pub = model.Publication(**moderation_publications[current_index])

        creator = await self.loom_employee_client.get_employee_by_account_id(current_pub.creator_id)
        category = await self.loom_content_client.get_category_by_id(current_pub.category_id)

        # Подготавливаем медиа для изображения
        preview_image_media, image_url = self._image_manager.get_moderation_image_media(
            publication_id=current_pub.id,
            image_fid=current_pub.image_fid
        )

        data = {
            "has_publications": True,
            "creator_name": creator.name,
            "category_name": category.name,
            "created_at": self._datetime_formatter.format_datetime(current_pub.created_at),
            "publication_text": current_pub.text,
            "has_image": bool(current_pub.image_fid),
            "preview_image_media": preview_image_media,
            "current_index": current_index + 1,
            "total_count": len(moderation_publications),
            "has_prev": current_index > 0,
            "has_next": current_index < len(moderation_publications) - 1,
        }

        # Сохраняем данные текущей публикации для редактирования
        dialog_manager.dialog_data["original_publication"] = {
            "id": current_pub.id,
            "creator_id": current_pub.creator_id,
            "text": current_pub.text,
            "category_id": current_pub.category_id,
            "image_url": image_url,
            "has_image": bool(current_pub.image_fid),
            "moderation_status": current_pub.moderation_status,
            "created_at": current_pub.created_at,
        }

        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

        if not selected_networks:
            self.logger.info("Инициализация выбранных социальных сетей")

            social_networks = await self.loom_content_client.get_social_networks_by_organization(
                organization_id=state.organization_id
            )
            selected_networks = self.__social_network_manger.initialize_network_selection(
                social_networks=social_networks
            )
            dialog_manager.dialog_data["selected_social_networks"] = selected_networks

        # Копируем в рабочую версию, если ее еще нет
        if "working_publication" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["working_publication"] = dict(
                dialog_manager.dialog_data["original_publication"])

        return data

    @auto_log()
    @traced_method()
    async def get_reject_comment_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        original_pub = dialog_manager.dialog_data.get("original_publication", {})
        creator = await self.loom_employee_client.get_employee_by_account_id(original_pub["creator_id"])

        data = {
            "creator_name": creator.name,
            "has_comment": bool(dialog_manager.dialog_data.get("reject_comment")),
            "reject_comment": dialog_manager.dialog_data.get("reject_comment", ""),
        }

        return data

    @auto_log()
    @traced_method()
    async def get_edit_preview_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        if "working_publication" not in dialog_manager.dialog_data:
            self.logger.info("Инициализация рабочей публикации")
            dialog_manager.dialog_data["working_publication"] = dict(
                dialog_manager.dialog_data["original_publication"]
            )

        working_pub = dialog_manager.dialog_data["working_publication"]
        original_pub = dialog_manager.dialog_data["original_publication"]

        creator = await self.loom_employee_client.get_employee_by_account_id(working_pub["creator_id"])
        category = await self.loom_content_client.get_category_by_id(working_pub["category_id"])

        preview_image_media = self._image_manager.get_edit_preview_image_media(working_pub)

        has_multiple_images = False
        current_image_index = 0
        total_images = 0
        if working_pub.get("generated_images_url"):
            images_url = working_pub["generated_images_url"]
            current_image_index = working_pub.get("current_image_index", 0)
            total_images = len(images_url)
            has_multiple_images = total_images > 1

        data = {
            "creator_name": creator.name,
            "category_name": category.name,
            "created_at": self._datetime_formatter.format_datetime(original_pub["created_at"]),
            "publication_text": working_pub["text"],
            "has_image": working_pub.get("has_image", False),
            "preview_image_media": preview_image_media,
            "has_changes": self._publication_manager.has_changes(dialog_manager),
            "has_multiple_images": has_multiple_images,
            "current_image_index": current_image_index + 1,  # Показываем с 1
            "total_images": total_images,
        }

        return data

    @auto_log()
    @traced_method()
    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self.state_manager.get_state(dialog_manager)
        social_networks = await self.loom_content_client.get_social_networks_by_organization(
            organization_id=state.organization_id
        )

        telegram_connected = self.__social_network_manger.is_network_connected(social_networks, "telegram")
        vkontakte_connected = self.__social_network_manger.is_network_connected(social_networks, "vkontakte")

        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

        await self.__social_network_manger.setup_checkbox_states(
            dialog_manager=dialog_manager,
            social_networks=social_networks,
            selected_networks=selected_networks
        )

        data = {
            "telegram_connected": telegram_connected,
            "vkontakte_connected": vkontakte_connected,
            "no_connected_networks": not telegram_connected and not vkontakte_connected,
            "has_available_networks": telegram_connected or vkontakte_connected,
        }
        return data

    @auto_log()
    @traced_method()
    async def get_edit_text_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_pub = dialog_manager.dialog_data["working_publication"]
        return {
            "publication_text": working_pub["text"],
            "has_void_text": dialog_manager.dialog_data.get("has_void_text", False),
            "has_small_text": dialog_manager.dialog_data.get("has_small_text", False),
            "has_big_text": dialog_manager.dialog_data.get("has_big_text", False),
            "is_regenerating_text": dialog_manager.dialog_data.get("is_regenerating_text", False),
            "regenerate_prompt": dialog_manager.dialog_data.get("regenerate_prompt", ""),
            "has_regenerate_prompt": bool(dialog_manager.dialog_data.get("regenerate_prompt", "")),
            # Voice input support
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
            "has_void_regenerate_prompt": dialog_manager.dialog_data.get("has_void_regenerate_prompt", False),
            "has_small_regenerate_prompt": dialog_manager.dialog_data.get("has_small_regenerate_prompt", False),
            "has_big_regenerate_prompt": dialog_manager.dialog_data.get("has_big_regenerate_prompt", False),
        }

    @auto_log()
    @traced_method()
    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        preview_image_media = self._image_manager.get_edit_preview_image_media(working_pub)

        return {
            "preview_image_media": preview_image_media,
            "has_void_image_prompt": dialog_manager.dialog_data.get("has_void_image_prompt", False),
            "has_small_image_prompt": dialog_manager.dialog_data.get("has_small_image_prompt", False),
            "has_big_image_prompt": dialog_manager.dialog_data.get("has_big_image_prompt", False),
            "is_generating_image": dialog_manager.dialog_data.get("is_generating_image", False),
            "has_image": working_pub.get("has_image", False),
            "is_custom_image": working_pub.get("is_custom_image", False),
            "image_prompt": dialog_manager.dialog_data.get("image_prompt", ""),
            "has_image_prompt": dialog_manager.dialog_data.get("image_prompt", "") != "",
            # Voice input support
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
        }

    @auto_log()
    @traced_method()
    async def get_upload_image_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        return {
            "has_invalid_image_type": dialog_manager.dialog_data.get("has_invalid_image_type", False),
            "has_big_image_size": dialog_manager.dialog_data.get("has_big_image_size", False),
            "has_image_processing_error": dialog_manager.dialog_data.get("has_image_processing_error", False),
            "has_image": working_pub.get("has_image", False),
            "is_custom_image": working_pub.get("is_custom_image", False),
        }

    @auto_log()
    @traced_method()
    async def get_text_too_long_alert_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        publication_text = working_pub.get("text", "")
        current_text_length = len(publication_text)
        max_length_with_image = 1024

        return {
            "current_text_length": current_text_length,
            "max_length_with_image": max_length_with_image,
            "publication_text": publication_text,
            "has_previous_text": bool(dialog_manager.dialog_data.get("previous_text")),
        }

    @auto_log()
    @traced_method()
    async def get_publication_success_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        post_links = dialog_manager.dialog_data.get("post_links", {})

        telegram_link = post_links.get("telegram")
        vkontakte_link = post_links.get("vkontakte")

        return {
            "has_post_links": bool(post_links),
            "has_telegram_link": bool(telegram_link),
            "has_vkontakte_link": bool(vkontakte_link),
            "telegram_link": telegram_link or "",
            "vkontakte_link": vkontakte_link or "",
        }

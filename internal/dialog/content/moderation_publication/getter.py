from aiogram import Bot
from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method

from internal.dialog.helpers import StateManager

from internal.dialog.content.moderation_publication.helpers import (
    ImageManager, PublicationManager, SocialNetworkManager, DateTimeFormatter, DialogDataHelper, StateRestorer
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

        self.image_manager = ImageManager(
            logger=self.logger,
            bot=self.bot,
            loom_domain=self.loom_domain,
            loom_content_client=self.loom_content_client
        )
        self.state_restorer = StateRestorer(
            logger=self.logger,
            image_manager=self.image_manager
        )
        self.publication_manager = PublicationManager(
            self.logger,
            self.bot,
            self.loom_content_client,
            self.state_restorer,
            self.image_manager
        )
        self.social_network_manger = SocialNetworkManager(
            logger=self.logger
        )
        self._datetime_formatter = DateTimeFormatter()
        self.dialog_data_helper = DialogDataHelper()

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

        self.dialog_data_helper.set_moderation_list(dialog_manager, moderation_publications)
        self.dialog_data_helper.initialize_current_index_if_needed(dialog_manager)

        current_index = self.dialog_data_helper.get_current_index(dialog_manager)
        current_pub = model.Publication(**moderation_publications[current_index])

        creator = await self.loom_employee_client.get_employee_by_account_id(current_pub.creator_id)
        category = await self.loom_content_client.get_category_by_id(current_pub.category_id)

        # Подготавливаем медиа для изображения
        preview_image_media, image_url = self.image_manager.get_moderation_image_media(
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
        self.dialog_data_helper.set_original_publication(dialog_manager, {
            "id": current_pub.id,
            "creator_id": current_pub.creator_id,
            "text": current_pub.text,
            "category_id": current_pub.category_id,
            "image_url": image_url,
            "has_image": bool(current_pub.image_fid),
            "moderation_status": current_pub.moderation_status,
            "created_at": current_pub.created_at,
        })

        selected_networks = self.dialog_data_helper.get_selected_social_networks(dialog_manager)

        if not selected_networks:
            self.logger.info("Инициализация выбранных социальных сетей")

            social_networks = await self.loom_content_client.get_social_networks_by_organization(
                organization_id=state.organization_id
            )
            selected_networks = self.social_network_manger.initialize_network_selection(
                social_networks=social_networks
            )
            self.dialog_data_helper.set_selected_social_networks(dialog_manager, selected_networks)

        # Копируем в рабочую версию, если ее еще нет
        self.dialog_data_helper.initialize_working_from_original(dialog_manager)

        return data

    @auto_log()
    @traced_method()
    async def get_reject_comment_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        original_pub = self.dialog_data_helper.get_original_publication_safe(dialog_manager)
        creator = await self.loom_employee_client.get_employee_by_account_id(original_pub["creator_id"])

        return {
            "creator_name": creator.name,
            **self.dialog_data_helper.get_reject_comment_window_data(dialog_manager)
        }

    @auto_log()
    @traced_method()
    async def get_edit_preview_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        self.dialog_data_helper.initialize_working_from_original(dialog_manager)

        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)
        original_pub = self.dialog_data_helper.get_original_publication(dialog_manager)

        creator = await self.loom_employee_client.get_employee_by_account_id(working_pub["creator_id"])
        category = await self.loom_content_client.get_category_by_id(working_pub["category_id"])

        preview_image_media = self.image_manager.get_edit_preview_image_media(working_pub)

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
            "has_changes": self.publication_manager.has_changes(dialog_manager),
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

        telegram_connected = self.social_network_manger.is_network_connected(social_networks, "telegram")
        vkontakte_connected = self.social_network_manger.is_network_connected(social_networks, "vkontakte")

        selected_networks = self.dialog_data_helper.get_selected_social_networks(dialog_manager)

        await self.social_network_manger.setup_checkbox_states(
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
    async def get_edit_publication_text_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self.dialog_data_helper.get_edit_text_window_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_pub = self.dialog_data_helper.get_working_publication_safe(dialog_manager)
        preview_image_media = self.image_manager.get_edit_preview_image_media(working_pub)

        return {
            "preview_image_media": preview_image_media,
            **self.dialog_data_helper.get_image_menu_window_data(dialog_manager)
        }

    @auto_log()
    @traced_method()
    async def get_upload_image_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self.dialog_data_helper.get_upload_image_window_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_text_too_long_alert_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self.dialog_data_helper.get_text_too_long_alert_window_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_publication_success_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self.dialog_data_helper.get_publication_success_window_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_new_image_confirm_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        new_image_media, old_image_media, showing_old_image = \
            self.image_manager.get_new_image_confirm_media(dialog_manager)

        display_image_media = old_image_media if showing_old_image else new_image_media

        flags_data = self.dialog_data_helper.get_new_image_confirm_flags(dialog_manager)

        return {
            "new_image_media": display_image_media,
            "has_old_image": old_image_media is not None,
            "showing_old_image": showing_old_image,
            "showing_new_image": not showing_old_image,
            **flags_data
        }

    @auto_log()
    @traced_method()
    async def get_combine_images_choice_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self.dialog_data_helper.get_combine_images_choice_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_combine_images_upload_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        combine_current_image_media, combine_current_index, combine_images_count = \
            self.image_manager.get_combine_images_media(dialog_manager)

        flags_data = self.dialog_data_helper.get_combine_images_upload_flags(dialog_manager)

        return {
            "combine_current_index": combine_current_index + 1,
            "combine_current_image_media": combine_current_image_media,
            **flags_data
        }

    @auto_log()
    @traced_method()
    async def get_combine_images_prompt_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        combine_current_image_media, combine_current_index, combine_images_count = \
            self.image_manager.get_combine_images_media(dialog_manager)

        flags_data = self.dialog_data_helper.get_combine_images_prompt_flags(dialog_manager)

        return {
            "combine_current_index": combine_current_index + 1,
            "combine_current_image_media": combine_current_image_media,
            **flags_data
        }

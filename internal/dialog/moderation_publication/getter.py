import time
from datetime import datetime
from aiogram_dialog.api.entities import MediaId, MediaAttachment

from aiogram.types import ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from internal import interface, model
from pkg.trace_wrapper import traced_method


class ModerationPublicationGetter(interface.IModerationPublicationGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_employee_client: interface.ILoomEmployeeClient,
            loom_content_client: interface.ILoomContentClient,
            loom_domain: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_employee_client = loom_employee_client
        self.loom_content_client = loom_content_client
        self.loom_domain = loom_domain

    @traced_method()
    async def get_moderation_list_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        self.logger.info("Начало загрузки списка модерации")
        state = await self._get_state(dialog_manager)

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

        creator = await self.loom_employee_client.get_employee_by_account_id(
            current_pub.creator_id
        )

        category = await self.loom_content_client.get_category_by_id(
            current_pub.category_id
        )

        # Подготавливаем медиа для изображения
        preview_image_media = None
        image_url = None
        if current_pub.image_fid:
            self.logger.info("Загрузка изображения публикации")
            cache_buster = int(time.time())
            image_url = f"https://{self.loom_domain}/api/content/publication/{current_pub.id}/image/download?v={cache_buster}"

            preview_image_media = MediaAttachment(
                url=image_url,
                type=ContentType.PHOTO
            )

        data = {
            "has_publications": True,
            "creator_name": creator.name,
            "category_name": category.name,
            "created_at": self._format_datetime(current_pub.created_at),
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

            telegram_connected = self._is_network_connected(social_networks, "telegram")
            vkontakte_connected = self._is_network_connected(social_networks, "vkontakte")

            if vkontakte_connected:
                widget_id = "vkontakte_checkbox"
                autoselect = social_networks["vkontakte"][0].get("autoselect", False)
                selected_networks[widget_id] = autoselect

            if telegram_connected:
                widget_id = "telegram_checkbox"
                autoselect = social_networks["telegram"][0].get("autoselect", False)
                selected_networks[widget_id] = autoselect

            dialog_manager.dialog_data["selected_social_networks"] = selected_networks

        # Копируем в рабочую версию, если ее еще нет
        if "working_publication" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["working_publication"] = dict(
                dialog_manager.dialog_data["original_publication"])

        self.logger.info("Список модерации загружен")
        return data

    @traced_method()
    async def get_reject_comment_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        self.logger.info("Начало загрузки данных комментария отклонения")
        original_pub = dialog_manager.dialog_data.get("original_publication", {})

        creator = await self.loom_employee_client.get_employee_by_account_id(
            original_pub["creator_id"],
        )

        data = {
            "creator_name": creator.name,
            "has_comment": bool(dialog_manager.dialog_data.get("reject_comment")),
            "reject_comment": dialog_manager.dialog_data.get("reject_comment", ""),
        }

        self.logger.info("Данные комментария отклонения загружены")
        return data

    @traced_method()
    async def get_edit_preview_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        self.logger.info("Начало загрузки данных превью редактирования")

        if "working_publication" not in dialog_manager.dialog_data:
            self.logger.info("Инициализация рабочей публикации")
            dialog_manager.dialog_data["working_publication"] = dict(
                dialog_manager.dialog_data["original_publication"]
            )

        working_pub = dialog_manager.dialog_data["working_publication"]
        original_pub = dialog_manager.dialog_data["original_publication"]

        creator = await self.loom_employee_client.get_employee_by_account_id(
            working_pub["creator_id"]
        )

        category = await self.loom_content_client.get_category_by_id(
            working_pub["category_id"]
        )

        preview_image_media = self._get_edit_preview_image_media(working_pub)
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
            "created_at": self._format_datetime(original_pub["created_at"]),
            "publication_text": working_pub["text"],
            "has_image": working_pub.get("has_image", False),
            "preview_image_media": preview_image_media,
            "has_changes": self._has_changes(dialog_manager),
            "has_multiple_images": has_multiple_images,
            "current_image_index": current_image_index + 1,  # Показываем с 1
            "total_images": total_images,
        }

        self.logger.info("Данные превью редактирования загружены")
        return data

    @traced_method()
    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        self.logger.info("Начало загрузки данных выбора социальных сетей")
        state = await self._get_state(dialog_manager)

        social_networks = await self.loom_content_client.get_social_networks_by_organization(
            organization_id=state.organization_id
        )

        telegram_connected = self._is_network_connected(social_networks, "telegram")
        vkontakte_connected = self._is_network_connected(social_networks, "vkontakte")

        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

        if vkontakte_connected:
            self.logger.info("Установка состояния VK чекбокса")
            widget_id = "vkontakte_checkbox"
            vkontakte_checkbox: ManagedCheckbox = dialog_manager.find(widget_id)
            await vkontakte_checkbox.set_checked(selected_networks[widget_id])

        if telegram_connected:
            self.logger.info("Установка состояния Telegram чекбокса")
            widget_id = "telegram_checkbox"
            telegram_checkbox: ManagedCheckbox = dialog_manager.find(widget_id)
            await telegram_checkbox.set_checked(selected_networks[widget_id])

        data = {
            "telegram_connected": telegram_connected,
            "vkontakte_connected": vkontakte_connected,
            "no_connected_networks": not telegram_connected and not vkontakte_connected,
            "has_available_networks": telegram_connected or vkontakte_connected,
        }

        self.logger.info("Данные выбора социальных сетей загружены")
        return data

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
        }

    @traced_method()
    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        preview_image_media = self._get_edit_preview_image_media(working_pub)

        return {
            "preview_image_media": preview_image_media,
            "has_void_image_prompt": dialog_manager.dialog_data.get("has_void_image_prompt", False),
            "has_small_image_prompt": dialog_manager.dialog_data.get("has_small_image_prompt", False),
            "has_big_image_prompt": dialog_manager.dialog_data.get("has_big_image_prompt", False),
            "is_generating_image": dialog_manager.dialog_data.get("is_generating_image", False),
            "has_image": working_pub.get("has_image", False),
            "is_custom_image": working_pub.get("is_custom_image", False),
        }

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

    # Вспомогательные методы
    def _has_changes(self, dialog_manager: DialogManager) -> bool:
        original = dialog_manager.dialog_data.get("original_publication", {})
        working = dialog_manager.dialog_data.get("working_publication", {})

        if not original or not working:
            return False

        # Сравниваем текстовые поля
        fields_to_compare = ["name", "text", "tags"]
        for field in fields_to_compare:
            if original.get(field) != working.get(field):
                return True

        # Проверяем изменения изображения более детально

        # 1. Проверяем, изменилось ли наличие изображения
        if original.get("has_image", False) != working.get("has_image", False):
            return True

        # 2. Если есть пользовательское изображение - это всегда изменение
        if working.get("custom_image_file_id"):
            # Проверяем, было ли это изображение в оригинале
            if original.get("custom_image_file_id") != working.get("custom_image_file_id"):
                return True

        # 3. Проверяем изменение URL (новое сгенерированное изображение)
        original_url = original.get("image_url", "")
        working_url = working.get("image_url", "")

        # Игнорируем базовый URL и сравниваем только если оба не пустые
        if working_url and original_url:
            # Если URL изменился - это новое изображение
            if original_url != working_url:
                return True
        elif working_url != original_url:
            # Один пустой, другой нет - есть изменения
            return True

        return False

    def _get_edit_preview_image_media(self, working_pub: dict) -> MediaAttachment | None:
        preview_image_media = None

        if working_pub.get("has_image"):
            if working_pub.get("custom_image_file_id"):
                self.logger.info("Загрузка пользовательского изображения")
                preview_image_media = MediaAttachment(
                    file_id=MediaId(working_pub["custom_image_file_id"]),
                    type=ContentType.PHOTO
                )
            elif working_pub.get("generated_images_url"):
                self.logger.info("Загрузка сгенерированного изображения")

                images_url = working_pub["generated_images_url"]
                current_image_index = working_pub.get("current_image_index", 0)

                if current_image_index < len(images_url):
                    preview_image_media = MediaAttachment(
                        url=images_url[current_image_index],
                        type=ContentType.PHOTO
                    )
            elif working_pub.get("image_url"):
                self.logger.info("Загрузка изображения по URL")
                preview_image_media = MediaAttachment(
                    url=working_pub["image_url"],
                    type=ContentType.PHOTO
                )
        return preview_image_media

    def _is_network_connected(self, social_networks: dict, network_type: str) -> bool:
        if not social_networks:
            return False
        return network_type in social_networks and len(social_networks[network_type]) > 0

    def _format_datetime(self, dt: str) -> str:
        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            # Форматируем в читаемый вид
            return dt.strftime("%d.%m.%Y %H:%M")
        except:
            return dt

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]

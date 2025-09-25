import time
from datetime import datetime
from aiogram_dialog.api.entities import MediaId, MediaAttachment

from aiogram.types import ContentType
from aiogram_dialog import DialogManager

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ModerationPublicationGetter(interface.IModerationPublicationGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_content_client: interface.IKonturContentClient,
            kontur_domain: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client
        self.kontur_content_client = kontur_content_client
        self.kontur_domain = kontur_domain

    async def get_moderation_list_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ModerationPublicationGetter.get_moderation_list_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Получаем публикации на модерации для организации
                publications = await self.kontur_content_client.get_publications_by_organization(
                    organization_id=state.organization_id
                )

                # Фильтруем только те, что на модерации
                moderation_publications = [
                    pub.to_dict() for pub in publications
                    if pub.moderation_status == "moderation"
                ]

                if not moderation_publications:
                    return {
                        "has_publications": False,
                        "publications_count": 0,
                        "period_text": "",
                    }

                # Сохраняем список для навигации
                dialog_manager.dialog_data["moderation_list"] = moderation_publications

                # Устанавливаем текущий индекс (0 если не был установлен)
                if "current_index" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["current_index"] = 0

                current_index = dialog_manager.dialog_data["current_index"]
                current_pub = model.Publication(**moderation_publications[current_index])

                # Получаем информацию об авторе
                creator = await self.kontur_employee_client.get_employee_by_account_id(
                    current_pub.creator_id
                )

                # Получаем категорию
                category = await self.kontur_content_client.get_category_by_id(
                    current_pub.category_id
                )

                # Подготавливаем медиа для изображения
                preview_image_media = None
                image_url = None
                if current_pub.image_fid:
                    cache_buster = int(time.time())
                    image_url = f"https://{self.kontur_domain}/api/content/publication/{current_pub.id}/image/download?v={cache_buster}"

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

                # Копируем в рабочую версию, если ее еще нет
                if "working_publication" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["working_publication"] = dict(
                        dialog_manager.dialog_data["original_publication"])

                self.logger.info("Список модерации загружен")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_reject_comment_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ModerationPublicationGetter.get_reject_comment_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                original_pub = dialog_manager.dialog_data.get("original_publication", {})

                # Получаем информацию об авторе
                creator = await self.kontur_employee_client.get_employee_by_account_id(
                    original_pub["creator_id"],
                )

                data = {
                    "publication_name": original_pub["name"],
                    "creator_name": creator.name,
                    "has_comment": bool(dialog_manager.dialog_data.get("reject_comment")),
                    "reject_comment": dialog_manager.dialog_data.get("reject_comment", ""),
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_edit_preview_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ModerationPublicationGetter.get_edit_preview_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Инициализируем рабочую версию если ее нет
                if "working_publication" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["working_publication"] = dict(
                        dialog_manager.dialog_data["original_publication"]
                    )

                working_pub = dialog_manager.dialog_data["working_publication"]
                original_pub = dialog_manager.dialog_data["original_publication"]

                # Получаем информацию об авторе
                creator = await self.kontur_employee_client.get_employee_by_account_id(
                    working_pub["creator_id"]
                )

                # Получаем категорию
                category = await self.kontur_content_client.get_category_by_id(
                    working_pub["category_id"]
                )

                # Подготавливаем медиа для изображения
                preview_image_media = None
                has_multiple_images = False
                current_image_index = 0
                total_images = 0

                if working_pub.get("has_image"):
                    # Приоритет: пользовательское > сгенерированные множественные > одиночное
                    if working_pub.get("custom_image_file_id"):
                        preview_image_media = MediaAttachment(
                            file_id=MediaId(working_pub["custom_image_file_id"]),
                            type=ContentType.PHOTO
                        )
                    elif working_pub.get("generated_images_url"):
                        # Множественные сгенерированные изображения
                        images_url = working_pub["generated_images_url"]
                        current_image_index = working_pub.get("current_image_index", 0)
                        total_images = len(images_url)
                        has_multiple_images = total_images > 1

                        if current_image_index < len(images_url):
                            preview_image_media = MediaAttachment(
                                url=images_url[current_image_index],
                                type=ContentType.PHOTO
                            )
                    elif working_pub.get("image_url"):
                        preview_image_media = MediaAttachment(
                            url=working_pub["image_url"],
                            type=ContentType.PHOTO
                        )

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

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ModerationPublicationGetter.get_social_network_select_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Получаем подключенные социальные сети для организации
                social_networks = await self.kontur_content_client.get_social_networks_by_organization(
                    organization_id=state.organization_id
                )

                # Проверяем подключенные сети
                telegram_connected = self._is_network_connected(social_networks, "telegram")
                vkontakte_connected = self._is_network_connected(social_networks, "vkontakte")

                # Получаем текущие выбранные сети
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                data = {
                    "telegram_connected": telegram_connected,
                    "vkontakte_connected": vkontakte_connected,
                    "all_networks_connected": telegram_connected and vkontakte_connected,
                    "no_connected_networks": not telegram_connected and not vkontakte_connected,
                    "has_available_networks": telegram_connected or vkontakte_connected,
                    "has_selected_networks": has_selected_networks,
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_edit_text_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "has_void_text": dialog_manager.dialog_data.get("has_void_text", False),
            "has_small_text": dialog_manager.dialog_data.get("has_small_text", False),
            "has_big_text": dialog_manager.dialog_data.get("has_big_text", False),
            "is_regenerating_text": dialog_manager.dialog_data.get("is_regenerating_text", False),
            "regenerate_prompt": dialog_manager.dialog_data.get("regenerate_prompt", ""),
            "has_regenerate_prompt": bool(dialog_manager.dialog_data.get("regenerate_prompt", "")),
        }

    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        return {
            "has_void_image_prompt": dialog_manager.dialog_data.get("has_void_image_prompt", False),
            "has_small_image_prompt": dialog_manager.dialog_data.get("has_small_image_prompt", False),
            "has_big_image_prompt": dialog_manager.dialog_data.get("has_big_image_prompt", False),
            "is_generating_image": dialog_manager.dialog_data.get("is_generating_image", False),
            "has_image": working_pub.get("has_image", False),
            "is_custom_image": working_pub.get("is_custom_image", False),
        }

    async def get_upload_image_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        return {
            "has_invalid_image_type": dialog_manager.dialog_data.get("has_invalid_image_type", False),
            "has_big_image_size": dialog_manager.dialog_data.get("has_big_image_size", False),
            "has_image_processing_error": dialog_manager.dialog_data.get("has_image_processing_error", False),
            "has_image": working_pub.get("has_image", False),
            "is_custom_image": working_pub.get("is_custom_image", False),
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

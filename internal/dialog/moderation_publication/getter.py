import time
from datetime import datetime, timezone
from aiogram_dialog.api.entities import MediaId, MediaAttachment

from aiogram import Bot
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
                author = await self.kontur_employee_client.get_employee_by_account_id(
                    current_pub.creator_id
                )

                # Получаем категорию
                category = await self.kontur_content_client.get_category_by_id(
                    current_pub.category_id
                )

                # Форматируем теги
                tags = current_pub.tags or []
                tags_text = ", ".join(tags) if tags else ""

                # Рассчитываем время ожидания
                waiting_time = self._calculate_waiting_time_text(current_pub.created_at)

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

                # Определяем период
                period_text = self._get_period_text(moderation_publications)

                data = {
                    "has_publications": True,
                    "publications_count": len(moderation_publications),
                    "period_text": period_text,
                    "author_name": author.name,
                    "category_name": category.name,
                    "created_at": self._format_datetime(current_pub.created_at),
                    "has_waiting_time": bool(waiting_time),
                    "waiting_time": waiting_time,
                    "publication_name": current_pub.name,
                    "publication_text": current_pub.text,
                    "has_tags": bool(tags),
                    "publication_tags": tags_text,
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
                    "name": current_pub.name,
                    "text": current_pub.text,
                    "tags": current_pub.tags or [],
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

                self.logger.info("Список модерации загружен" )

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
                author = await self.kontur_employee_client.get_employee_by_account_id(
                    original_pub["creator_id"],
                )

                data = {
                    "publication_name": original_pub["name"],
                    "author_name": author.name,
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
                author = await self.kontur_employee_client.get_employee_by_account_id(
                    working_pub["creator_id"]
                )

                # Получаем категорию
                category = await self.kontur_content_client.get_category_by_id(
                    working_pub["category_id"]
                )

                # Форматируем теги
                tags = working_pub.get("tags", [])
                tags_text = ", ".join(tags) if tags else ""

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
                    "author_name": author.name,
                    "category_name": category.name,
                    "created_at": self._format_datetime(original_pub["created_at"]),
                    "publication_name": working_pub["name"],
                    "publication_text": working_pub["text"],
                    "has_tags": bool(tags),
                    "publication_tags": tags_text,
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

    async def get_regenerate_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {"regenerate_prompt": dialog_manager.dialog_data.get("regenerate_prompt", "")}

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

    def _is_network_connected(self, social_networks: dict, network_type: str) -> bool:
        if not social_networks:
            return False
        return network_type in social_networks and len(social_networks[network_type]) > 0

    async def get_edit_title_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        return {
            "current_title": working_pub.get("name", ""),
        }

    async def get_edit_tags_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        tags = working_pub.get("tags", [])
        return {
            "has_tags": bool(tags),
            "current_tags": ", ".join(tags) if tags else "",
        }

    async def get_edit_content_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        text = working_pub.get("text", "")
        return {
            "current_text_length": len(text),
        }

    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        return {
            "has_image": working_pub.get("has_image", False),
            "is_custom_image": working_pub.get("is_custom_image", False),
        }

    async def get_image_prompt_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "has_image_prompt": bool(dialog_manager.dialog_data.get("image_prompt")),
            "image_prompt": dialog_manager.dialog_data.get("image_prompt", ""),
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

    def _format_datetime(self, dt: str) -> str:
        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            # Форматируем в читаемый вид
            return dt.strftime("%d.%m.%Y %H:%M")
        except:
            return dt

    def _calculate_waiting_hours(self, created_at: str) -> int:
        try:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

            now = datetime.now(timezone.utc)
            delta = now - created_at
            return int(delta.total_seconds() / 3600)
        except:
            return 0

    def _calculate_waiting_time_text(self, created_at: str) -> str:
        hours = self._calculate_waiting_hours(created_at)

        if hours == 0:
            return "менее часа"
        elif hours == 1:
            return "1 час"
        elif hours < 24:
            return f"{hours} часов"
        else:
            days = hours // 24
            if days == 1:
                return "1 день"
            else:
                return f"{days} дней"

    def _get_period_text(self, publications: list) -> str:
        if not publications:
            return "Нет данных"

        # Находим самую старую и новую публикацию
        dates = []
        for pub in publications:
            if hasattr(pub, 'created_at') and pub.created_at:
                dates.append(pub.created_at)

        if not dates:
            return "Сегодня"

        # Простое определение периода на основе самой старой публикации
        oldest_date = min(dates)
        waiting_hours = self._calculate_waiting_hours(oldest_date)

        if waiting_hours < 24:
            return "За сегодня"
        elif waiting_hours < 48:
            return "За последние 2 дня"
        elif waiting_hours < 168:  # неделя
            return "За неделю"
        else:
            return "За месяц"

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
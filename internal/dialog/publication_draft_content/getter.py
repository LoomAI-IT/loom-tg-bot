import time
from datetime import datetime

from aiogram import Bot
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment
from aiogram.types import ContentType

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class PublicationDraftGetter(interface.IPublicationDraftGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_employee_client: interface.ILoomEmployeeClient,
            loom_content_client: interface.ILoomContentClient,
            loom_domain: str,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_employee_client = loom_employee_client
        self.loom_content_client = loom_content_client
        self.loom_domain = loom_domain

    async def get_publication_list_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """
        Получение данных для списка черновиков.
        Возвращает список всех черновиков пользователя.
        """
        with self.tracer.start_as_current_span(
                "PublicationDraftGetter.get_publication_list_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                
                # Получаем публикации организации и фильтруем черновики
                publications = await self.loom_content_client.get_publications_by_organization(
                    state.organization_id
                )
                drafts = [p for p in publications if getattr(p, "moderation_status", None) == "draft"]
                
                if not drafts:
                    self.logger.info("Нет черновиков публикаций")
                    return {
                        "has_publications": False,
                        "publications_count": 0,
                    }
                
                # Сохраняем список черновиков
                dialog_manager.dialog_data["draft_list"] = [pub.to_dict() for pub in drafts]
                
                # Инициализируем current_index если его нет
                if "current_index" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["current_index"] = 0
                
                current_index = dialog_manager.dialog_data["current_index"]
                current_draft = drafts[current_index]
                
                # Получаем данные об авторе и категории
                creator = await self.loom_employee_client.get_employee_by_account_id(current_draft.creator_id)
                category = await self.loom_content_client.get_category_by_id(current_draft.category_id)
                
                # Готовим превью изображения
                preview_image_media = None
                image_url = None
                has_image = bool(getattr(current_draft, "image_fid", None))
                if has_image:
                    cache_buster = int(time.time())
                    image_url = f"https://{self.loom_domain}/api/content/publication/{current_draft.id}/image/download?v={cache_buster}"
                    preview_image_media = MediaAttachment(
                        url=image_url,
                        type=ContentType.PHOTO
                    )
                
                # Инициализируем original_publication для текущего черновика
                dialog_manager.dialog_data["original_publication"] = {
                    "id": current_draft.id,
                    "creator_id": current_draft.creator_id,
                    "category_id": current_draft.category_id,
                    "text": current_draft.text,
                    "image_url": image_url,
                    "has_image": has_image,
                    "created_at": current_draft.created_at,
                }
                
                data = {
                    "has_publications": True,
                    "creator_name": creator.name,
                    "category_name": category.name,
                    "created_at": self._format_datetime(current_draft.created_at),
                    "publication_text": current_draft.text,
                    "has_image": has_image,
                    "preview_image_media": preview_image_media,
                    "current_index": current_index + 1,
                    "total_count": len(drafts),
                    "has_prev": current_index > 0,
                    "has_next": current_index < len(drafts) - 1,
                }
                
                self.logger.info(f"Отображаем черновик {current_index + 1} из {len(drafts)}")
                
                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_edit_preview_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """
        Получение данных для превью черновика.
        Показывает содержимое выбранного черновика.
        """
        with self.tracer.start_as_current_span(
                "PublicationDraftGetter.get_edit_preview_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                publication_id = int(dialog_manager.dialog_data.get("selected_publication_id"))
                
                # Получаем детали публикации
                publication = await self.loom_content_client.get_publication_by_id(publication_id)
                
                # Получаем категорию
                category = await self.loom_content_client.get_category_by_id(publication.category_id)
                
                # Навигация
                all_publication_ids = dialog_manager.dialog_data.get("all_publication_ids", [])
                current_index = all_publication_ids.index(publication_id) + 1 if publication_id in all_publication_ids else 1
                
                # Обновляем данные в dialog_data для редактирования
                # Разделяем текст на название и содержимое
                full_text = publication.text or ""
                if "\n\n" in full_text:
                    title, content = full_text.split("\n\n", 1)
                    dialog_manager.dialog_data["publication_title"] = title.strip()
                    dialog_manager.dialog_data["publication_content"] = content.strip()
                else:
                    dialog_manager.dialog_data["publication_title"] = publication.text_reference or "Без названия"
                    dialog_manager.dialog_data["publication_content"] = full_text
                dialog_manager.dialog_data["publication_tags"] = []
                dialog_manager.dialog_data["category_name"] = category.name
                dialog_manager.dialog_data["publication_category_id"] = publication.category_id
                dialog_manager.dialog_data["has_image"] = bool(getattr(publication, "image_fid", None))
                
                # Проверяем права пользователя
                state = await self._get_state(dialog_manager)
                employee = await self.loom_employee_client.get_employee_by_account_id(state.account_id)
                
                # Подготавливаем данные как в модерации
                has_image = bool(getattr(publication, "image_fid", None))
                if "working_publication" not in dialog_manager.dialog_data:
                    # Инициализируем original_publication
                    dialog_manager.dialog_data["original_publication"] = {
                        "id": publication.id,
                        "creator_id": publication.creator_id,
                        "category_id": publication.category_id,
                        "text": publication.text,
                        "image_url": f"https://{self.loom_domain}/api/content/publication/{publication.id}/image/download" if has_image else None,
                        "has_image": has_image,
                        "created_at": publication.created_at,
                    }
                    # Инициализируем working_publication как копию original
                    dialog_manager.dialog_data["working_publication"] = dict(dialog_manager.dialog_data["original_publication"])
                    dialog_manager.dialog_data["working_publication"].update({
                        "current_image_index": 0,
                        "user_image_file_id": None,
                        "generated_images_url": [],
                    })
                
                working_pub = dialog_manager.dialog_data["working_publication"]
                
                # Готовим превью изображения из working_publication
                preview_image_media = None
                if working_pub.get("has_image") and working_pub.get("image_url"):
                    # Добавляем cache buster если его нет
                    image_url = working_pub["image_url"]
                    if "?v=" not in image_url:
                        cache_buster = int(time.time())
                        image_url = f"{image_url}?v={cache_buster}"
                    
                    preview_image_media = MediaAttachment(
                        url=image_url,
                        type=ContentType.PHOTO
                    )
                original_pub = dialog_manager.dialog_data["original_publication"]
                
                # Получаем данные об авторе
                creator = await self.loom_employee_client.get_employee_by_account_id(publication.creator_id)
                
                data = {
                    "creator_name": creator.name,
                    "category_name": category.name,
                    "created_at": self._format_datetime(publication.created_at),
                    "publication_text": working_pub.get("text", publication.text),
                    "has_image": working_pub.get("has_image", False),
                    "preview_image_media": preview_image_media,
                    "has_changes": self._has_changes(dialog_manager),
                    "has_multiple_images": False,
                    "current_image_index": 1,
                    "total_images": 1,
                    
                    # Навигация между черновиками
                    "current_index": current_index,
                    "total_count": len(all_publication_ids),
                    "has_prev": current_index > 1,
                    "has_next": current_index < len(all_publication_ids),
                    "has_multiple_drafts": len(all_publication_ids) > 1,
                }
                
                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise
    
    async def get_edit_text_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Данные для редактирования текста."""
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        regenerate_prompt = dialog_manager.dialog_data.get("regenerate_prompt", "")
        
        return {
            "publication_text": working_pub.get("text", ""),
            "regenerate_prompt": regenerate_prompt,
            "has_regenerate_prompt": bool(regenerate_prompt and regenerate_prompt.strip()),
            "has_void_regenerate_prompt": dialog_manager.dialog_data.get("has_void_regenerate_prompt", False),
            "is_regenerating_text": dialog_manager.dialog_data.get("is_regenerating_text", False),
            "has_void_text": dialog_manager.dialog_data.get("has_void_text", False),
            "has_small_text": dialog_manager.dialog_data.get("has_small_text", False),
            "has_big_text": dialog_manager.dialog_data.get("has_big_text", False),
        }

    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Данные для управления изображениями."""
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        return {
            "has_image": working_pub.get("has_image", False),
        }

    async def get_upload_image_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Данные для загрузки изображения."""
        return {}

    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Данные для выбора соцсетей."""
        return {
            "telegram_connected": True,
            "vkontakte_connected": True,
            "has_available_networks": True,
        }
    
    async def get_publication_success_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Данные для окна успешной публикации."""
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
    
    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        """Получение состояния пользователя"""
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

    def _clean_html_for_telegram(self, text: str) -> str:
        """Очищает HTML для Telegram - убирает неподдерживаемые теги, оставляет поддерживаемые"""
        import re
        
        # Telegram поддерживает: <b>, <strong>, <i>, <em>, <u>, <s>, <strike>, <del>, <code>, <pre>, <a href="">
        # Убираем неподдерживаемые теги: <p>, <div>, <span>, <br>, <br/>, <h1>-<h6>, и т.д.
        
        # Заменяем <p> и </p> на переносы строк
        text = re.sub(r'<p[^>]*>', '\n', text)
        text = re.sub(r'</p>', '\n\n', text)
        
        # Заменяем <br> и <br/> на переносы строк
        text = re.sub(r'<br\s*/?>', '\n', text)
        
        # Убираем другие неподдерживаемые теги (но оставляем содержимое)
        unsupported_tags = ['div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote']
        for tag in unsupported_tags:
            text = re.sub(f'<{tag}[^>]*>', '', text)
            text = re.sub(f'</{tag}>', '', text)
        
        # Убираем лишние переносы строк
        text = re.sub(r'\n+', '\n', text)
        text = text.strip()
        
        return text

    def _has_changes(self, dialog_manager: DialogManager) -> bool:
        """Проверяет есть ли несохраненные изменения."""
        original = dialog_manager.dialog_data.get("original_publication", {})
        working = dialog_manager.dialog_data.get("working_publication", {})

        if not original or not working:
            return False

        # Сравниваем текстовые поля
        if original.get("text") != working.get("text"):
            return True

        # Проверяем изменения изображения
        if original.get("has_image", False) != working.get("has_image", False):
            return True

        # Проверяем изменение URL изображения
        original_url = original.get("image_url", "")
        working_url = working.get("image_url", "")

        if working_url and original_url:
            if original_url != working_url:
                return True
        elif working_url != original_url:
            return True

        return False

    def _format_datetime(self, dt: str) -> str:
        """Форматирует дату в читаемый вид."""
        from datetime import datetime
        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            # Форматируем в читаемый вид
            return dt.strftime("%d.%m.%Y %H:%M")
        except:
            return str(dt) if dt else ""
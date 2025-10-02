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
            bot: Bot,
            **kwargs
    ) -> dict:
        """
        📋 ДАННЫЕ для списка черновиков
        Возвращает список всех черновиков пользователя
        """
        with self.tracer.start_as_current_span(
                "PublicationDraftGetter.get_publication_list_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                
                # 📋 Получаем публикации организации и фильтруем черновики
                publications = await self.loom_content_client.get_publications_by_organization(
                    state.organization_id
                )
                drafts = [p for p in publications if getattr(p, "moderation_status", None) == "draft"]
                
                # 📝 Форматируем для отображения
                publications_data = []
                for draft in drafts:
                    # 📅 Форматируем дату
                    created_date = "неизвестно"
                    if hasattr(draft, 'created_at') and draft.created_at:
                        try:
                            if isinstance(draft.created_at, str):
                                dt = datetime.fromisoformat(draft.created_at)
                            else:
                                dt = draft.created_at
                            created_date = dt.strftime("%d.%m.%Y")
                        except:
                            created_date = "неизвестно"
                    
                    publications_data.append({
                        "id": draft.id,
                        "title": draft.text_reference or "Без названия",
                        "created_date": created_date,
                        "preview": draft.text[:50] + "..." if len(draft.text) > 50 else draft.text,
                    })
                
                # 💾 Сохраняем ID для навигации
                dialog_manager.dialog_data["all_publication_ids"] = [p["id"] for p in publications_data]
                
                data = {
                    "publications": publications_data,
                    "publications_count": len(publications_data),
                    "has_publications": len(publications_data) > 0,
                    "show_pager": len(publications_data) > 6,  # Показывать пагинацию если > 6
                }
                
                self.logger.info(f"Список черновиков загружен: {len(publications_data)} шт.")
                
                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_edit_preview_data(
            self,
            dialog_manager: DialogManager,
            bot: Bot,
            **kwargs
    ) -> dict:
        """
        👁️ ДАННЫЕ для превью черновика
        Показывает содержимое выбранного черновика
        """
        with self.tracer.start_as_current_span(
                "PublicationDraftGetter.get_edit_preview_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                publication_id = int(dialog_manager.dialog_data.get("selected_publication_id"))
                
                # 📖 Получаем детали публикации
                publication = await self.loom_content_client.get_publication_by_id(publication_id)
                
                # 🏷️ Получаем категорию
                category = await self.loom_content_client.get_category_by_id(publication.category_id)
                
                # 🎮 Навигация
                all_publication_ids = dialog_manager.dialog_data.get("all_publication_ids", [])
                current_index = all_publication_ids.index(publication_id) + 1 if publication_id in all_publication_ids else 1
                
                # 💾 Обновляем данные в dialog_data для редактирования
                dialog_manager.dialog_data["publication_title"] = publication.text_reference
                dialog_manager.dialog_data["publication_content"] = publication.text
                dialog_manager.dialog_data["publication_tags"] = []
                dialog_manager.dialog_data["category_name"] = category.name
                
                # 📊 Проверяем права пользователя
                state = await self._get_state(dialog_manager)
                employee = await self.loom_employee_client.get_employee_by_account_id(state.account_id)
                
                # 🖼️ Готовим превью изображения, если есть
                preview_image_media = None
                has_image = bool(getattr(publication, "image_fid", None))
                if has_image:
                    image_url = f"https://{self.loom_domain}/api/content/publication/{publication.id}/image/download"
                    preview_image_media = MediaAttachment(
                        url=image_url,
                        type=ContentType.PHOTO
                    )

                data = {
                    "publication_title": publication.name or "Без названия",
                    "publication_content": publication.text or "",
                    "publication_tags": ", ".join(publication.tags) if publication.tags else "Нет тегов",
                    "category_name": category.name,
                    "has_tags": bool(publication.tags),
                    "has_image": has_image,
                    
                    # 🎮 Навигация
                    "current_index": current_index,
                    "total_count": len(all_publication_ids),
                    "has_prev": current_index > 1,
                    "has_next": current_index < len(all_publication_ids),
                    
                    # 🔐 Права доступа
                    "requires_moderation": employee.required_moderation if employee else True,
                    "can_publish_directly": not employee.required_moderation if employee else False,
                    
                    # 🖼️ Изображение (если есть)
                    "preview_image_media": preview_image_media,
                }
                
                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    # 📝 ГЕТТЕРЫ для окон редактирования
    
    async def get_edit_text_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """📝 Данные для меню редактирования"""
        return {
            "current_title": dialog_manager.dialog_data.get("publication_title", ""),
            "current_content": dialog_manager.dialog_data.get("publication_content", ""),
        }

    async def get_regenerate_text_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """🔄 Данные для регенерации"""
        return {
            "regenerate_prompt": dialog_manager.dialog_data.get("regenerate_prompt", ""),
            "has_regenerate_prompt": "regenerate_prompt" in dialog_manager.dialog_data,
            "has_void_regenerate_prompt": dialog_manager.dialog_data.get("has_void_regenerate_prompt", False),
            "is_regenerating_text": dialog_manager.dialog_data.get("is_regenerating_text", False),
        }

    async def get_edit_title_data(
            self,
            dialog_manager: DialogManager,
            **kwargs  
    ) -> dict:
        """📝 Данные для редактирования названия"""
        return {
            "publication_title": dialog_manager.dialog_data.get("publication_title", ""),
            "has_void_title": dialog_manager.dialog_data.get("has_void_title", False),
        }

    async def get_edit_description_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """📝 Данные для редактирования описания"""
        return {
            "publication_description": dialog_manager.dialog_data.get("publication_description", ""),
        }

    async def get_edit_content_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """📄 Данные для редактирования контента"""
        return {
            "publication_content": dialog_manager.dialog_data.get("publication_content", ""),
            "has_void_content": dialog_manager.dialog_data.get("has_void_content", False),
        }

    async def get_edit_tags_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """🏷️ Данные для редактирования тегов"""
        tags = dialog_manager.dialog_data.get("publication_tags", [])
        tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        
        return {
            "publication_tags": tags_str,
        }

    async def get_edit_image_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """🖼️ Данные для управления изображениями"""
        return {
            "has_image": dialog_manager.dialog_data.get("has_image", False),
        }

    async def get_generate_image_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """🎨 Данные для генерации изображения"""
        return {
            "image_prompt": dialog_manager.dialog_data.get("image_prompt", ""),
            "has_image_prompt": "image_prompt" in dialog_manager.dialog_data,
        }

    async def get_upload_image_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """📤 Данные для загрузки изображения"""
        return {}

    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """🌐 Данные для выбора соцсетей"""
        return {
            "telegram_connected": True,  # TODO: Реальная проверка подключения
            "vkontakte_connected": True,
            "has_available_networks": True,
        }

    # 🛠️ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    
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
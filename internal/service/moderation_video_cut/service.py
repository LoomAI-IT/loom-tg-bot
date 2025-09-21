# internal/service/video_cut_moderation/service.py
import asyncio
from datetime import datetime, timezone
from typing import Any

from aiogram.enums import ParseMode
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class VideoCutModerationDialogService(interface.IVideoCutModerationDialogService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_organization_client: interface.IKonturOrganizationClient,
            kontur_content_client: interface.IKonturContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client
        self.kontur_organization_client = kontur_organization_client
        self.kontur_content_client = kontur_content_client

    async def get_moderation_list_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Получение данных для основного окна - сразу показываем первое видео"""
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.get_moderation_list_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Получаем видео-нарезки на модерации для организации
                video_cuts = await self.kontur_content_client.get_video_cuts_by_organization(
                    organization_id=state.organization_id
                )

                # Фильтруем только те, что на модерации
                moderation_video_cuts = [
                    video_cut.to_dict() for video_cut in video_cuts
                    if video_cut.moderation_status == "moderation"
                ]

                if not moderation_video_cuts:
                    return {
                        "has_video_cuts": False,
                        "video_cuts_count": 0,
                        "period_text": "",
                    }

                # Сохраняем список для навигации
                dialog_manager.dialog_data["moderation_list"] = moderation_video_cuts

                # Устанавливаем текущий индекс (0 если не был установлен)
                if "current_index" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["current_index"] = 0

                current_index = dialog_manager.dialog_data["current_index"]
                current_video_cut = model.VideoCut(**moderation_video_cuts[current_index])

                # Получаем информацию об авторе
                author = await self.kontur_employee_client.get_employee_by_account_id(
                    current_video_cut.creator_id
                )

                # Форматируем теги
                tags = current_video_cut.tags or []
                tags_text = ", ".join(tags) if tags else ""

                # Рассчитываем время ожидания
                waiting_time = self._calculate_waiting_time_text(current_video_cut.created_at)

                # Подготавливаем медиа для видео
                video_media = await self._get_video_media(current_video_cut)

                # Определяем период
                period_text = self._get_period_text(moderation_video_cuts)

                data = {
                    "has_video_cuts": True,
                    "video_cuts_count": len(moderation_video_cuts),
                    "period_text": period_text,
                    "author_name": author.name,
                    "created_at": self._format_datetime(current_video_cut.created_at),
                    "has_waiting_time": bool(waiting_time),
                    "waiting_time": waiting_time,
                    "youtube_reference": current_video_cut.youtube_video_reference or "Не указан",
                    "video_name": current_video_cut.name or "Без названия",
                    "video_description": current_video_cut.description or "Описание отсутствует",
                    "has_tags": bool(tags),
                    "video_tags": tags_text,
                    "has_video": bool(current_video_cut.video_fid),
                    "video_media": video_media,
                    "current_index": current_index + 1,
                    "total_count": len(moderation_video_cuts),
                    "has_prev": current_index > 0,
                    "has_next": current_index < len(moderation_video_cuts) - 1,
                }

                # Сохраняем данные текущего видео для редактирования
                dialog_manager.dialog_data["original_video_cut"] = {
                    "id": current_video_cut.id,
                    "creator_id": current_video_cut.creator_id,
                    "name": current_video_cut.name,
                    "description": current_video_cut.description,
                    "tags": current_video_cut.tags or [],
                    "youtube_video_reference": current_video_cut.youtube_video_reference,
                    "video_fid": current_video_cut.video_fid,
                    "moderation_status": current_video_cut.moderation_status,
                    "created_at": current_video_cut.created_at,
                    "youtube_source": current_video_cut.youtube_source,
                    "inst_source": current_video_cut.inst_source,
                }

                # Копируем в рабочую версию, если ее еще нет
                if "working_video_cut" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["working_video_cut"] = dict(
                        dialog_manager.dialog_data["original_video_cut"])

                self.logger.info(
                    "Список модерации видео загружен",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: self._get_chat_id(dialog_manager),
                        "video_cuts_count": len(moderation_video_cuts),
                        "current_index": current_index,
                    }
                )

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_navigate_video_cut(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.handle_navigate_video_cut",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                current_index = dialog_manager.dialog_data.get("current_index", 0)
                moderation_list = dialog_manager.dialog_data.get("moderation_list", [])

                # Определяем направление навигации
                if button.widget_id == "prev_video_cut":
                    new_index = max(0, current_index - 1)
                else:  # next_video_cut
                    new_index = min(len(moderation_list) - 1, current_index + 1)

                if new_index == current_index:
                    await callback.answer()
                    return

                # Обновляем индекс
                dialog_manager.dialog_data["current_index"] = new_index

                # Сбрасываем рабочие данные для нового видео
                dialog_manager.dialog_data.pop("working_video_cut", None)

                self.logger.info(
                    "Навигация по видео на модерации",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "from_index": current_index,
                        "to_index": new_index,
                    }
                )

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка навигации", show_alert=True)
                raise

    async def get_reject_comment_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.get_reject_comment_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                original_video_cut = dialog_manager.dialog_data.get("original_video_cut", {})

                # Получаем информацию об авторе
                author = await self.kontur_employee_client.get_employee_by_account_id(
                    original_video_cut["creator_id"],
                )

                data = {
                    "video_name": original_video_cut["name"] or "Без названия",
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

    async def handle_reject_comment_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            comment: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.handle_reject_comment_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                comment = comment.strip()

                if not comment:
                    await message.answer("❌ Комментарий не может быть пустым")
                    return

                if len(comment) < 10:
                    await message.answer("❌ Слишком короткий комментарий. Укажите причину подробнее.")
                    return

                if len(comment) > 500:
                    await message.answer("❌ Слишком длинный комментарий (макс. 500 символов)")
                    return

                dialog_manager.dialog_data["reject_comment"] = comment

                # Удаляем сообщение с комментарием
                await message.delete()

                self.logger.info(
                    "Комментарий отклонения видео введен",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "comment_length": len(comment),
                    }
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при сохранении комментария")
                raise

    async def handle_send_rejection(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.handle_send_rejection",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                original_video_cut = dialog_manager.dialog_data["original_video_cut"]
                video_cut_id = original_video_cut["id"]
                reject_comment = dialog_manager.dialog_data.get("reject_comment", "Нет комментария")

                # Отклоняем видео-нарезку через API
                await self.kontur_content_client.moderate_video_cut(
                    video_cut_id=video_cut_id,
                    moderator_id=state.account_id,
                    moderation_status="rejected",
                    moderation_comment=reject_comment,
                )

                # Отправляем уведомление автору
                creator_state = await self.state_repo.state_by_account_id(original_video_cut["creator_id"])
                if creator_state:
                    await self.bot.send_message(
                        chat_id=creator_state[0].tg_chat_id,
                        text=f"Ваша видео-нарезка: <b>{original_video_cut['name'] or 'Без названия'}</b> была отклонена с комментарием:\n<b>{reject_comment}</b>",
                        parse_mode=ParseMode.HTML,
                    )

                self.logger.info(
                    "Видео-нарезка отклонена",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "video_cut_id": video_cut_id,
                        "reason": reject_comment,
                    }
                )

                await callback.answer("❌ Видео-нарезка отклонена", show_alert=True)

                # Удаляем отклоненное видео из списка
                moderation_list = dialog_manager.dialog_data.get("moderation_list", [])
                current_index = dialog_manager.dialog_data.get("current_index", 0)

                if moderation_list and current_index < len(moderation_list):
                    moderation_list.pop(current_index)

                    # Корректируем индекс если нужно
                    if current_index >= len(moderation_list) and moderation_list:
                        dialog_manager.dialog_data["current_index"] = len(moderation_list) - 1
                    elif not moderation_list:
                        dialog_manager.dialog_data["current_index"] = 0

                    # Сбрасываем рабочие данные
                    dialog_manager.dialog_data.pop("working_video_cut", None)

                # Возвращаемся к основному окну
                await dialog_manager.switch_to(model.VideoCutModerationStates.moderation_list)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при отклонении", show_alert=True)
                raise

    async def get_edit_preview_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Получение данных для окна редактирования с превью"""
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.get_edit_preview_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Инициализируем рабочую версию если ее нет
                if "working_video_cut" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["working_video_cut"] = dict(
                        dialog_manager.dialog_data["original_video_cut"]
                    )

                working_video_cut = dialog_manager.dialog_data["working_video_cut"]
                original_video_cut = dialog_manager.dialog_data["original_video_cut"]

                # Получаем информацию об авторе
                author = await self.kontur_employee_client.get_employee_by_account_id(
                    working_video_cut["creator_id"]
                )

                # Форматируем теги
                tags = working_video_cut.get("tags", [])
                tags_text = ", ".join(tags) if tags else ""

                # Подготавливаем медиа для видео
                video_media = await self._get_video_media(model.VideoCut(**working_video_cut))

                data = {
                    "author_name": author.name,
                    "created_at": self._format_datetime(original_video_cut["created_at"]),
                    "youtube_reference": working_video_cut["youtube_video_reference"] or "Не указан",
                    "video_name": working_video_cut["name"] or "Без названия",
                    "video_description": working_video_cut["description"] or "Описание отсутствует",
                    "has_tags": bool(tags),
                    "video_tags": tags_text,
                    "has_video": bool(working_video_cut.get("video_fid")),
                    "video_media": video_media,
                    "has_changes": self._has_changes(dialog_manager),
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_edit_title_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.handle_edit_title_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                new_title = text.strip()

                if not new_title:
                    await message.answer("❌ Название не может быть пустым")
                    return

                if len(new_title) > 100:  # YouTube Shorts лимит
                    await message.answer("❌ Слишком длинное название (макс. 100 символов для YouTube)")
                    return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_video_cut"]["name"] = new_title

                await message.answer("✅ Название обновлено!")
                await dialog_manager.switch_to(model.VideoCutModerationStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при сохранении названия")
                raise

    async def handle_edit_description_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.handle_edit_description_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                new_description = text.strip()

                if not new_description:
                    await message.answer("❌ Описание не может быть пустым")
                    return

                if len(new_description) > 2200:  # Instagram лимит
                    await message.answer("❌ Слишком длинное описание (макс. 2200 символов для Instagram)")
                    return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_video_cut"]["description"] = new_description

                await message.answer("✅ Описание обновлено!")
                await dialog_manager.switch_to(model.VideoCutModerationStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при сохранении описания")
                raise

    async def handle_edit_tags_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.handle_edit_tags_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                tags_raw = text.strip()

                if not tags_raw:
                    new_tags = []
                else:
                    # Парсим теги
                    new_tags = [tag.strip() for tag in tags_raw.split(",")]
                    new_tags = [tag for tag in new_tags if tag]

                    if len(new_tags) > 15:  # YouTube лимит
                        await message.answer("❌ Слишком много тегов (макс. 15 для YouTube)")
                        return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_video_cut"]["tags"] = new_tags

                await message.answer(f"✅ Теги обновлены ({len(new_tags)} шт.)")
                await dialog_manager.switch_to(model.VideoCutModerationStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при сохранении тегов")
                raise

    async def handle_save_edits(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.handle_save_edits",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                if not self._has_changes(dialog_manager):
                    await callback.answer("ℹ️ Нет изменений для сохранения", show_alert=True)
                    return

                await callback.answer()
                loading_message = await callback.message.answer("💾 Сохраняю изменения...")

                # Сохраняем изменения
                await self._save_video_cut_changes(dialog_manager)

                # Обновляем оригинальную версию
                dialog_manager.dialog_data["original_video_cut"] = dict(dialog_manager.dialog_data["working_video_cut"])

                await loading_message.edit_text("✅ Изменения сохранены!")
                await asyncio.sleep(2)
                try:
                    await loading_message.delete()
                except:
                    pass

                await dialog_manager.switch_to(model.VideoCutModerationStates.moderation_list)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка сохранения", show_alert=True)
                raise

    async def handle_back_to_moderation_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.handle_back_to_moderation_list",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.switch_to(model.VideoCutModerationStates.moderation_list)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_toggle_social_network(
            self,
            callback: CallbackQuery,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.handle_toggle_social_network",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Инициализируем словарь выбранных соцсетей если его нет
                if "selected_social_networks" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["selected_social_networks"] = {}

                network_id = checkbox.widget_id
                is_checked = checkbox.is_checked()

                # Сохраняем состояние чекбокса
                dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

                self.logger.info(
                    "Видео-платформа переключена в модерации",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "network": network_id,
                        "selected": is_checked,
                        "all_selected": dialog_manager.dialog_data["selected_social_networks"]
                    }
                )

                await callback.answer()
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_publish_with_selected_networks(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.handle_publish_with_selected_networks",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Проверяем, что выбрана хотя бы одна платформа
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                if not has_selected_networks:
                    await callback.answer(
                        "⚠️ Выберите хотя бы одну видео-платформу для публикации",
                        show_alert=True
                    )
                    return

                await self._publish_moderated_video_cut(callback, dialog_manager)
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при публикации", show_alert=True)
                raise

    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.get_social_network_select_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Получаем подключенные социальные сети для организации
                social_networks = await self.kontur_content_client.get_social_networks_by_organization(
                    organization_id=state.organization_id
                )

                # Проверяем подключенные сети
                youtube_connected = self._is_network_connected(social_networks, "youtube")
                instagram_connected = self._is_network_connected(social_networks, "instagram")

                # Получаем текущие выбранные сети
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                data = {
                    "youtube_connected": youtube_connected,
                    "instagram_connected": instagram_connected,
                    "no_connected_networks": not youtube_connected and not instagram_connected,
                    "has_available_networks": youtube_connected or instagram_connected,
                    "has_selected_networks": has_selected_networks,
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_back_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService.handle_back_to_content_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_edit_title_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_video_cut = dialog_manager.dialog_data.get("working_video_cut", {})
        return {
            "current_title": working_video_cut.get("name", ""),
        }

    async def get_edit_description_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_video_cut = dialog_manager.dialog_data.get("working_video_cut", {})
        description = working_video_cut.get("description", "")
        return {
            "current_description_length": len(description),
        }

    async def get_edit_tags_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_video_cut = dialog_manager.dialog_data.get("working_video_cut", {})
        tags = working_video_cut.get("tags", [])
        return {
            "has_tags": bool(tags),
            "current_tags": ", ".join(tags) if tags else "",
        }

    # Вспомогательные методы

    def _has_changes(self, dialog_manager: DialogManager) -> bool:
        original = dialog_manager.dialog_data.get("original_video_cut", {})
        working = dialog_manager.dialog_data.get("working_video_cut", {})

        if not original or not working:
            return False

        # Сравниваем основные поля
        fields_to_compare = ["name", "description", "tags"]
        for field in fields_to_compare:
            if original.get(field) != working.get(field):
                return True

        return False

    def _is_network_connected(self, social_networks: dict, network_type: str) -> bool:
        if not social_networks:
            return False
        return network_type in social_networks and len(social_networks[network_type]) > 0

    async def _save_video_cut_changes(self, dialog_manager: DialogManager) -> None:
        working_video_cut = dialog_manager.dialog_data["working_video_cut"]
        video_cut_id = working_video_cut["id"]

        await self.kontur_content_client.change_video_cut(
            video_cut_id=video_cut_id,
            name=working_video_cut["name"],
            description=working_video_cut["description"],
            tags=working_video_cut.get("tags", []),
        )

        self.logger.info(
            "Изменения видео-нарезки в модерации сохранены",
            {
                "video_cut_id": video_cut_id,
                "has_changes": self._has_changes(dialog_manager),
            }
        )

    async def _publish_moderated_video_cut(
            self,
            callback: CallbackQuery,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationDialogService._publish_moderated_video_cut",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await callback.answer()
                loading_message = await callback.message.answer("🚀 Публикую видео...")

                # Если есть несохраненные изменения, сохраняем их перед публикацией
                if self._has_changes(dialog_manager):
                    await self._save_video_cut_changes(dialog_manager)

                original_video_cut = dialog_manager.dialog_data["original_video_cut"]
                video_cut_id = original_video_cut["id"]
                state = await self._get_state(dialog_manager)

                # Получаем выбранные видео-платформы
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                youtube_source = selected_networks.get("youtube_checkbox", False)
                inst_source = selected_networks.get("instagram_checkbox", False)

                # Обновляем видео-нарезку с выбранными платформами
                await self.kontur_content_client.change_video_cut(
                    video_cut_id=video_cut_id,
                    youtube_source=youtube_source,
                    inst_source=inst_source,
                )

                # Одобряем видео-нарезку
                await self.kontur_content_client.moderate_video_cut(
                    video_cut_id=video_cut_id,
                    moderator_id=state.account_id,
                    moderation_status="approved",
                )

                # Формируем сообщение о публикации
                published_networks = []
                if youtube_source:
                    published_networks.append("📺 YouTube Shorts")
                if inst_source:
                    published_networks.append("📸 Instagram Reels")

                networks_text = ", ".join(published_networks)

                self.logger.info(
                    "Видео-нарезка одобрена и опубликована",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "video_cut_id": video_cut_id,
                        "youtube_source": youtube_source,
                        "inst_source": inst_source,
                    }
                )

                await loading_message.edit_text(
                    f"🚀 Видео-нарезка успешно опубликована!\n\n"
                    f"📋 Опубликовано в: {networks_text}"
                )

                await asyncio.sleep(3)
                try:
                    await loading_message.delete()
                except:
                    pass

                # Удаляем опубликованное видео из списка
                moderation_list = dialog_manager.dialog_data.get("moderation_list", [])
                current_index = dialog_manager.dialog_data.get("current_index", 0)

                if moderation_list and current_index < len(moderation_list):
                    moderation_list.pop(current_index)

                    # Корректируем индекс если нужно
                    if current_index >= len(moderation_list) and moderation_list:
                        dialog_manager.dialog_data["current_index"] = len(moderation_list) - 1
                    elif not moderation_list:
                        dialog_manager.dialog_data["current_index"] = 0

                    # Сбрасываем рабочие данные
                    dialog_manager.dialog_data.pop("working_video_cut", None)
                    dialog_manager.dialog_data.pop("selected_social_networks", None)

                # Возвращаемся к списку модерации
                await dialog_manager.switch_to(model.VideoCutModerationStates.moderation_list)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    def _format_datetime(self, dt: str) -> str:
        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            # Форматируем в читаемый вид
            return dt.strftime("%d.%m.%Y %H:%M")
        except:
            return str(dt)

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

    def _get_period_text(self, video_cuts: list) -> str:
        if not video_cuts:
            return "Нет данных"

        # Находим самое старое и новое видео
        dates = []
        for video_cut in video_cuts:
            if hasattr(video_cut, 'created_at') and video_cut.created_at:
                dates.append(video_cut.created_at)

        if not dates:
            return "Сегодня"

        # Простое определение периода на основе самого старого видео
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
        chat_id = self._get_chat_id(dialog_manager)
        return await self._get_state_by_chat_id(chat_id)

    async def _get_state_by_chat_id(self, chat_id: int) -> model.UserState:
        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]

    def _get_chat_id(self, dialog_manager: DialogManager) -> int:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            return dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            return dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

    async def _get_video_media(self, video_cut: model.VideoCut) -> MediaAttachment | None:
        video_media = None
        if video_cut.video_fid:
            cached_file = await self.state_repo.get_cache_file(video_cut.video_name)
            if cached_file:
                video_media = MediaAttachment(
                    file_id=MediaId(cached_file[0].file_id),
                    type=ContentType.VIDEO,
                )
        return video_media
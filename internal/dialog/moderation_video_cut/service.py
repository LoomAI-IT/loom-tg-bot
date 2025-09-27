from typing import Any

from aiogram.enums import ParseMode
from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class VideoCutModerationService(interface.IVideoCutModerationService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.loom_content_client = loom_content_client

    async def handle_navigate_video_cut(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationService.handle_navigate_video_cut",
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

                self.logger.info("Навигация по видео на модерации")

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка навигации", show_alert=True)
                raise

    async def handle_reject_comment_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            comment: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationService.handle_reject_comment_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                dialog_manager.dialog_data.pop("has_void_reject_comment", None)
                dialog_manager.dialog_data.pop("has_small_reject_comment", None)
                dialog_manager.dialog_data.pop("has_big_reject_comment", None)

                comment = comment.strip()
                if not comment:
                    dialog_manager.dialog_data["has_void_reject_comment"] = True
                    return

                if len(comment) < 10:
                    dialog_manager.dialog_data["has_small_reject_comment"] = True
                    return

                if len(comment) > 500:
                    dialog_manager.dialog_data["has_big_reject_comment"] = True
                    return

                dialog_manager.dialog_data["reject_comment"] = comment

                self.logger.info("Комментарий отклонения видео введен")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                raise

    async def handle_send_rejection(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationService.handle_send_rejection",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)

                original_video_cut = dialog_manager.dialog_data["original_video_cut"]
                video_cut_id = original_video_cut["id"]
                reject_comment = dialog_manager.dialog_data.get("reject_comment", "Нет комментария")

                # Отклоняем видео-нарезку через API
                await self.loom_content_client.moderate_video_cut(
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

                self.logger.info("Видео-нарезка отклонена")

                await callback.answer("❌ Видео-нарезка отклонена", show_alert=True)

                await self._remove_current_video_cut_from_list(dialog_manager)
                await dialog_manager.switch_to(model.VideoCutModerationStates.moderation_list)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка при отклонении", show_alert=True)
                raise

    async def handle_edit_title(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationService.handle_edit_title",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                dialog_manager.dialog_data.pop("has_void_title", None)
                dialog_manager.dialog_data.pop("has_big_title", None)

                new_title = message.html_text
                if not new_title:
                    dialog_manager.dialog_data["has_void_title"] = True
                    return

                if len(new_title) > 100:  # YouTube Shorts лимит
                    dialog_manager.dialog_data["has_big_title"] = True
                    return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_video_cut"]["name"] = new_title

                await dialog_manager.switch_to(model.VideoCutModerationStates.edit_preview)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_edit_description(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationService.handle_edit_description",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                dialog_manager.dialog_data.pop("has_void_description", None)
                dialog_manager.dialog_data.pop("has_big_description", None)

                new_description = message.html_text
                if not new_description:
                    dialog_manager.dialog_data["has_void_description"] = True
                    return

                if len(new_description) > 1000:  # Instagram лимит
                    dialog_manager.dialog_data["has_big_description"] = True
                    return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_video_cut"]["description"] = new_description

                await dialog_manager.switch_to(model.VideoCutModerationStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_edit_tags(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationService.handle_edit_tags",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                dialog_manager.dialog_data.pop("has_void_tags", None)

                tags_raw = text.strip()
                if not tags_raw:
                    new_tags = []
                else:
                    # Парсим теги
                    new_tags = [tag.strip() for tag in tags_raw.split(",")]
                    new_tags = [tag for tag in new_tags if tag]

                    if len(new_tags) > 15:  # YouTube лимит
                        dialog_manager.dialog_data["has_void_tags"] = True
                        return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_video_cut"]["tags"] = new_tags
                await dialog_manager.switch_to(model.VideoCutModerationStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_save_edits(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationService.handle_save_edits",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                if not self._has_changes(dialog_manager):
                    await callback.answer("ℹ️ Нет изменений для сохранения", show_alert=True)
                    return

                await self._save_video_cut_changes(dialog_manager)

                # Обновляем оригинальную версию
                dialog_manager.dialog_data["original_video_cut"] = dict(dialog_manager.dialog_data["working_video_cut"])

                await callback.answer("Изменения сохранены", show_alert=True)

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
                "VideoCutModerationService.handle_back_to_moderation_list",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await dialog_manager.switch_to(model.VideoCutModerationStates.moderation_list)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_toggle_social_network(
            self,
            callback: CallbackQuery,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationService.handle_toggle_social_network",
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

                self.logger.info("Видео-платформа переключена в модерации")

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_publish_now(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationService.handle_publish_now",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                if not has_selected_networks:
                    await callback.answer(
                        "⚠️ Выберите хотя бы одну видео-платформу для публикации",
                        show_alert=True
                    )
                    return

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
                await self.loom_content_client.change_video_cut(
                    video_cut_id=video_cut_id,
                    youtube_source=youtube_source,
                    inst_source=inst_source,
                )

                # Одобряем видео-нарезку
                await self.loom_content_client.moderate_video_cut(
                    video_cut_id=video_cut_id,
                    moderator_id=state.account_id,
                    moderation_status="approved",
                )

                await callback.answer("Опубликовано", show_alert=True)

                await self._remove_current_video_cut_from_list(dialog_manager)
                await dialog_manager.switch_to(model.VideoCutModerationStates.moderation_list)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка при публикации", show_alert=True)
                raise

    async def handle_back_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutModerationService.handle_back_to_content_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                if await self._check_alerts(dialog_manager):
                    return

                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def _remove_current_video_cut_from_list(self, dialog_manager: DialogManager) -> None:
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

    async def _save_video_cut_changes(self, dialog_manager: DialogManager) -> None:
        working_video_cut = dialog_manager.dialog_data["working_video_cut"]
        video_cut_id = working_video_cut["id"]

        await self.loom_content_client.change_video_cut(
            video_cut_id=video_cut_id,
            name=working_video_cut["name"],
            description=working_video_cut["description"],
            tags=working_video_cut.get("tags", []),
        )

    async def _check_alerts(self, dialog_manager: DialogManager) -> bool:
        state = await self._get_state(dialog_manager)
        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=True
        )

        vizard_alerts = await self.state_repo.get_vizard_video_cut_alert_by_state_id(
            state_id=state.id
        )
        if vizard_alerts:
            await dialog_manager.start(
                model.GenerateVideoCutStates.video_generated_alert,
                mode=StartMode.RESET_STACK
            )
            return True

        return False

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

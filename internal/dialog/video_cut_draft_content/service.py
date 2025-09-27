from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class VideoCutsDraftService(interface.IVideoCutsDraftService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_content_client = loom_content_client

    async def handle_navigate_video_cut(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_navigate_video_cut",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                current_index = dialog_manager.dialog_data.get("current_index", 0)
                video_cuts_list = dialog_manager.dialog_data.get("video_cuts_list", [])

                # Определяем направление навигации
                if button.widget_id == "prev_video_cut":
                    new_index = max(0, current_index - 1)
                else:  # next_video_cut
                    new_index = min(len(video_cuts_list) - 1, current_index + 1)

                if new_index == current_index:
                    await callback.answer()
                    return

                # Обновляем индекс
                dialog_manager.dialog_data["current_index"] = new_index

                # Сбрасываем рабочие данные для нового черновика
                dialog_manager.dialog_data.pop("working_video_cut", None)
                self.logger.info("Навигация по черновикам видео")

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка навигации", show_alert=True)
                raise

    async def handle_delete_video_cut(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_delete_video_cut",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                original_video_cut = dialog_manager.dialog_data["original_video_cut"]
                video_cut_id = original_video_cut["id"]

                await self.loom_content_client.delete_video_cut(
                    video_cut_id=video_cut_id
                )

                self.logger.info("Черновик видео удален")
                await callback.answer("🗑 Черновик удален", show_alert=True)

                await self._remove_current_video_cut_from_list(dialog_manager)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка удаления", show_alert=True)
                raise

    async def handle_save_changes(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_save_changes",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                if not self._has_changes(dialog_manager):
                    await callback.answer("ℹ️ Нет изменений для сохранения", show_alert=True)
                    return

                # Сохраняем изменения
                await self._save_video_cut_changes(dialog_manager)

                # Обновляем оригинальную версию
                dialog_manager.dialog_data["original_video_cut"] = dict(dialog_manager.dialog_data["working_video_cut"])
                await callback.answer("Изменения сохранены", show_alert=True)

                await dialog_manager.switch_to(model.VideoCutsDraftStates.video_cut_list)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка сохранения", show_alert=True)
                raise

    async def handle_edit_title(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_edit_title_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()
                new_title = message.html_text

                if not new_title:
                    dialog_manager.dialog_data["has_void_title"] = True
                    return
                dialog_manager.dialog_data.pop("has_void_title", None)

                if len(new_title) > 100:
                    dialog_manager.dialog_data["has_big_title"] = True
                    return
                dialog_manager.dialog_data.pop("has_big_title", None)

                dialog_manager.dialog_data["working_video_cut"]["name"] = new_title

                await dialog_manager.switch_to(model.VideoCutsDraftStates.edit_preview)
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
                "VideoCutsDraftService.handle_edit_description_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT
                await message.delete()

                new_description = message.html_text

                if not new_description:
                    dialog_manager.dialog_data["has_void_description"] = True
                    return
                dialog_manager.dialog_data.pop("has_void_description", None)

                if len(new_description) > 2200:
                    dialog_manager.dialog_data["has_big_description"] = True
                    return
                dialog_manager.dialog_data.pop("has_big_description", None)

                dialog_manager.dialog_data["working_video_cut"]["description"] = new_description

                await dialog_manager.switch_to(model.VideoCutsDraftStates.edit_preview)
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
                "VideoCutsDraftService.handle_edit_tags_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()
                tags_raw = text.strip()

                if not tags_raw:
                    new_tags = []
                else:
                    # Парсим теги
                    new_tags = [tag.strip() for tag in tags_raw.split(",")]
                    new_tags = [tag for tag in new_tags if tag]

                    if len(new_tags) > 15:  # YouTube лимит
                        dialog_manager.dialog_data["has_many_tags"] = True
                        return
                    dialog_manager.dialog_data.pop("has_many_tags", None)

                dialog_manager.dialog_data["working_video_cut"]["tags"] = new_tags

                await dialog_manager.switch_to(model.VideoCutsDraftStates.edit_preview)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_back_to_video_cut_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_back_to_video_cut_list",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await dialog_manager.switch_to(model.VideoCutsDraftStates.video_cut_list)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_send_to_moderation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_send_to_moderation_with_networks",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                if self._has_changes(dialog_manager):
                    await self._save_video_cut_changes(dialog_manager)


                original_video_cut = dialog_manager.dialog_data["original_video_cut"]
                video_cut_id = original_video_cut["id"]

                await self.loom_content_client.send_video_cut_to_moderation(
                    video_cut_id=video_cut_id
                )

                self.logger.info("Черновик видео отправлен на модерацию с выбранными соцсетями")
                await callback.answer(f"📤 Отправлено на модерацию!", show_alert=True)

                await self._remove_current_video_cut_from_list(dialog_manager)

                await dialog_manager.switch_to(model.VideoCutsDraftStates.video_cut_list)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка отправки", show_alert=True)
                raise

    async def handle_publish_now(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_publish_with_selected_networks",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                if not has_selected_networks:
                    await callback.answer(
                        "⚠️ Выберите хотя бы одну социальную сеть для публикации",
                        show_alert=True
                    )
                    return

                if self._has_changes(dialog_manager):
                    await self._save_video_cut_changes(dialog_manager)

                await self._save_selected_networks(dialog_manager)

                state = await self._get_state(dialog_manager)
                original_video_cut = dialog_manager.dialog_data["original_video_cut"]
                video_cut_id = original_video_cut["id"]

                # Публикуем немедленно через API
                await self.loom_content_client.moderate_video_cut(
                    video_cut_id=video_cut_id,
                    moderator_id=state.account_id,
                    moderation_status="approved",
                )

                self.logger.info("Черновик видео опубликован с выбранными соцсетями")
                await callback.answer("Черновик видео опубликован с выбранными соцсетями", show_alert=True)

                await self._remove_current_video_cut_from_list(dialog_manager)

                await dialog_manager.switch_to(model.VideoCutsDraftStates.video_cut_list)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка публикации", show_alert=True)
                raise

    async def handle_toggle_social_network(
            self,
            callback: CallbackQuery,
            checkbox: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_toggle_social_network",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Инициализируем словарь выбранных соцсетей если его нет
                if "selected_social_networks" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["selected_social_networks"] = {}

                network_id = checkbox.widget_id
                is_checked = checkbox.is_checked()

                # Сохраняем состояние чекбокса
                dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

                self.logger.info( "Социальная сеть переключена в черновиках видео")

                await callback.answer()
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_back_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_back_to_content_menu",
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

    # Вспомогательные методы
    def _has_changes(self, dialog_manager: DialogManager) -> bool:
        original = dialog_manager.dialog_data.get("original_video_cut", {})
        working = dialog_manager.dialog_data.get("working_video_cut", {})

        if not original or not working:
            return False

        # Сравниваем основные поля
        fields_to_compare = ["name", "description", "tags", "youtube_source", "inst_source"]
        for field in fields_to_compare:
            if original.get(field) != working.get(field):
                return True

        return False

    async def _save_selected_networks(self, dialog_manager: DialogManager) -> None:
        working_video_cut = dialog_manager.dialog_data["working_video_cut"]
        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

        # Обновляем выбранные платформы
        youtube_selected = selected_networks.get("youtube_checkbox", False)
        instagram_selected = selected_networks.get("instagram_checkbox", False)

        working_video_cut["youtube_source"] = youtube_selected
        working_video_cut["inst_source"] = instagram_selected

        # Сохраняем изменения через API
        await self._save_video_cut_changes(dialog_manager)

    async def _save_video_cut_changes(self, dialog_manager: DialogManager) -> None:
        working_video_cut = dialog_manager.dialog_data["working_video_cut"]
        video_cut_id = working_video_cut["id"]
        youtube_source = working_video_cut.get("youtube_source")
        inst_source = working_video_cut.get("inst_source")

        await self.loom_content_client.change_video_cut(
            video_cut_id=video_cut_id,
            name=working_video_cut["name"],
            description=working_video_cut["description"],
            tags=working_video_cut.get("tags", []),
            youtube_source=youtube_source,
            inst_source=inst_source
        )

    async def _remove_current_video_cut_from_list(self, dialog_manager: DialogManager) -> None:
        video_cuts_list = dialog_manager.dialog_data.get("video_cuts_list", [])
        current_index = dialog_manager.dialog_data.get("current_index", 0)

        if video_cuts_list and current_index < len(video_cuts_list):
            video_cuts_list.pop(current_index)

            # Корректируем индекс если нужно
            if current_index >= len(video_cuts_list) and video_cuts_list:
                dialog_manager.dialog_data["current_index"] = len(video_cuts_list) - 1
            elif not video_cuts_list:
                dialog_manager.dialog_data["current_index"] = 0

            # Сбрасываем рабочие данные
            dialog_manager.dialog_data.pop("working_video_cut", None)
            dialog_manager.dialog_data.pop("original_video_cut", None)

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

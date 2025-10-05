import re
from typing import Any
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, StartMode, ShowMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class GenerateVideoCutService(interface.IGenerateVideoCutService):
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

    async def handle_youtube_link_input(
            self,
            message: Message,
            message_input: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GenerateVideoCutService.handle_youtube_link_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало обработки ввода YouTube ссылки")

                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()
                youtube_url = message.text.strip()

                dialog_manager.dialog_data.pop("has_invalid_youtube_url", None)

                # Валидация YouTube ссылки
                if not self._is_valid_youtube_url(youtube_url):
                    self.logger.info("YouTube ссылка не прошла валидацию")
                    dialog_manager.dialog_data["has_invalid_youtube_url"] = True
                    return

                # Получаем состояние пользователя
                state = await self._get_state(dialog_manager)

                dialog_manager.dialog_data["is_processing_video"] = True

                await self.loom_content_client.generate_video_cut(
                    state.organization_id,
                    state.account_id,
                    youtube_url,
                )

                self.logger.info("Завершение обработки ввода YouTube ссылки")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GenerateVideoCutService.handle_go_to_content_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало перехода в меню контента")

                dialog_manager.show_mode = ShowMode.EDIT

                if await self._check_alerts(dialog_manager):
                    self.logger.info("Найдены алерты, переход к их отображению")
                    return

                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK,
                )

                await callback.answer("✅ Открываю меню контента")

                self.logger.info("Завершение перехода в меню контента")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_video_drafts(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GenerateVideoCutService.handle_go_to_video_drafts",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало перехода в черновики видео-нарезок")

                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)

                await self.state_repo.delete_vizard_video_cut_alert(
                    state.id
                )

                await dialog_manager.start(
                    model.VideoCutsDraftStates.video_cut_list,
                    mode=StartMode.RESET_STACK
                )

                await callback.answer("✅ Открываю черновики")

                self.logger.info("Завершение перехода в черновики видео-нарезок")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GenerateVideoCutService.handle_go_to_main_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало перехода в главное меню")

                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)

                await self.state_repo.delete_vizard_video_cut_alert(
                    state.id
                )

                await dialog_manager.start(
                    model.MainMenuStates.main_menu,
                    mode=StartMode.RESET_STACK
                )

                await callback.answer("🏠 Возвращаюсь в главное меню")

                self.logger.info("Завершение перехода в главное меню")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

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

    def _is_valid_youtube_url(self, url: str) -> bool:
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        return bool(youtube_regex.match(url))

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
from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ContentMenuService(interface.IContentMenuService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client

    async def handle_go_to_publication_generation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ContentMenuService.handle_go_to_publication_generation",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                # Запускаем диалог генерации публикации
                await dialog_manager.start(
                    model.GeneratePublicationStates.select_category,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Пользователь перешел к созданию публикации")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при переходе к созданию публикации", show_alert=True)
                raise

    async def handle_go_to_video_cut_generation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ContentMenuService.handle_go_to_video_cut_generation",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                # Запускаем диалог генерации видео-нарезки
                await dialog_manager.start(
                    model.GenerateVideoCutStates.input_youtube_link,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Пользователь перешел к созданию видео-нарезки")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при переходе к созданию видео-нарезки", show_alert=True)
                raise

    async def handle_go_to_publication_drafts(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ContentMenuService.handle_go_to_publication_drafts",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                # Запускаем диалог черновиков публикаций
                await dialog_manager.start(
                    model.PublicationDraftContentStates.drafts_list,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Пользователь перешел к черновикам публикаций")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при переходе к черновикам публикаций", show_alert=True)
                raise

    async def handle_go_to_video_drafts(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ContentMenuService.handle_go_to_video_drafts",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                # Запускаем диалог черновиков видео-нарезок
                await dialog_manager.start(
                    model.VideoCutsDraftStates.video_cut_list,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Пользователь перешел к черновикам видео-нарезок")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при переходе к черновикам видео", show_alert=True)
                raise

    async def handle_go_to_publication_moderation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ContentMenuService.handle_go_to_publication_moderation",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Проверяем права доступа к модерации
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                can_moderate = (
                        employee.role in ["moderator", "admin", "owner"] or
                        employee.edit_employee_perm_permission
                )

                if not can_moderate:
                    self.logger.warning("Пользователю отказано в доступе к модерации публикаций")
                    await callback.answer(
                        "❌ У вас нет прав для доступа к модерации",
                        show_alert=True
                    )
                    return

                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                # Запускаем диалог модерации публикаций
                await dialog_manager.start(
                    model.ModerationPublicationStates.moderation_list,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Пользователь перешел к модерации публикаций")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при переходе к модерации публикаций", show_alert=True)
                raise

    async def handle_go_to_video_moderation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ContentMenuService.handle_go_to_video_moderation",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Проверяем права доступа к модерации
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                can_moderate = (
                        employee.role in ["moderator", "admin", "owner"] or
                        employee.edit_employee_perm_permission
                )

                if not can_moderate:
                    self.logger.warning("Пользователю отказано в доступе к модерации видео")
                    await callback.answer(
                        "❌ У вас нет прав для доступа к модерации",
                        show_alert=True
                    )
                    return

                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                # Запускаем диалог модерации видео-нарезок
                await dialog_manager.start(
                    model.VideoCutModerationStates.moderation_list,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Пользователь перешел к модерации видео-нарезок")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при переходе к модерации видео", show_alert=True)
                raise

    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ContentMenuService.handle_go_to_main_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.MainMenuStates.main_menu,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Пользователь перешел в главное меню")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ContentMenuService.handle_go_to_content_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Пользователь перешел в контент меню")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        """Получить состояние текущего пользователя"""
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

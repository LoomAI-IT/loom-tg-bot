from typing import Any


from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode, ShowMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ContentMenuService(interface.IContentMenuService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_employee_client: interface.ILoomEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_employee_client = loom_employee_client


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
                self.logger.info("Начало перехода к созданию публикации")

                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)
                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                await dialog_manager.start(
                    model.GeneratePublicationStates.select_category,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Завершение перехода к созданию публикации")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось перейти к созданию публикации. Попробуйте позже", show_alert=True)
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
                self.logger.info("Начало перехода к созданию видео-нарезки")

                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)
                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                await dialog_manager.start(
                    model.GenerateVideoCutStates.input_youtube_link,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Завершение перехода к созданию видео-нарезки")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось перейти к созданию видео-нарезки. Попробуйте позже", show_alert=True)
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
                self.logger.info("Начало перехода к черновикам публикаций")

                await callback.answer("Функция черновиков публикаций находится в разработке", show_alert=True)

                self.logger.info("Завершение перехода к черновикам публикаций")
                span.set_status(Status(StatusCode.OK))
                return

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
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
                self.logger.info("Начало перехода к черновикам видео-нарезок")

                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)
                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                await dialog_manager.start(
                    model.VideoCutsDraftStates.video_cut_list,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Завершение перехода к черновикам видео-нарезок")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
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
                self.logger.info("Начало перехода к модерации публикаций")

                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)

                employee = await self.loom_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                can_moderate = employee.role in ["moderator", "admin"]

                if not can_moderate:
                    self.logger.info("Отказ в доступе: недостаточно прав для модерации публикаций")
                    await callback.answer(
                        "У вас нет прав для доступа к модерации публикаций",
                        show_alert=True
                    )
                    return

                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                await dialog_manager.start(
                    model.ModerationPublicationStates.moderation_list,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Завершение перехода к модерации публикаций")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
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
                self.logger.info("Начало перехода к модерации видео-нарезок")

                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)

                employee = await self.loom_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                can_moderate = employee.role in ["moderator", "admin"]

                if not can_moderate:
                    self.logger.info("Отказ в доступе: недостаточно прав для модерации видео-нарезок")
                    await callback.answer(
                        "У вас нет прав для доступа к модерации видео",
                        show_alert=True
                    )
                    return

                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                await dialog_manager.start(
                    model.VideoCutModerationStates.moderation_list,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Завершение перехода к модерации видео-нарезок")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
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
                self.logger.info("Начало перехода в главное меню")

                dialog_manager.show_mode = ShowMode.EDIT

                await dialog_manager.start(
                    model.MainMenuStates.main_menu,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Завершение перехода в главное меню")
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
                self.logger.info("Начало перехода в меню контента")

                dialog_manager.show_mode = ShowMode.EDIT

                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Завершение перехода в меню контента")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

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

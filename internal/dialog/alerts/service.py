from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode, ShowMode


from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class AlertsService(interface.IAlertsService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo

    @auto_log()
    @traced_method()
    async def handle_go_to_video_drafts(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        state = await self._get_state(dialog_manager)

        await self.state_repo.delete_vizard_video_cut_alert(
            state.id
        )

        await dialog_manager.start(
            model.VideoCutsDraftStates.video_cut_list,
            mode=StartMode.RESET_STACK
        )

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        state = await self._get_state(dialog_manager)

        await self._delete_current_alert(dialog_manager.current_context().state, state.id)
        next_alert_state = await self._get_next_alert_by_priority(state.id)

        if next_alert_state:
            await dialog_manager.start(next_alert_state, mode=StartMode.RESET_STACK)
        else:
            await self.state_repo.change_user_state(
                state_id=state.id,
                can_show_alerts=True
            )
            await dialog_manager.start(
                model.MainMenuStates.main_menu,
                mode=StartMode.RESET_STACK
            )

        await callback.answer()

    async def _delete_current_alert(self, current_state: Any, state_id: int) -> None:
        if current_state == model.AlertsStates.publication_approved_alert:
            await self.state_repo.delete_publication_approved_alert(state_id)
        elif current_state == model.AlertsStates.publication_rejected_alert:
            await self.state_repo.delete_publication_rejected_alert(state_id)
        elif current_state == model.AlertsStates.video_generated_alert:
            await self.state_repo.delete_vizard_video_cut_alert(state_id)

    async def _get_next_alert_by_priority(self, state_id: int) -> Any | None:
        if await self.state_repo.get_publication_approved_alert_by_state_id(state_id):
            return model.AlertsStates.publication_approved_alert

        if await self.state_repo.get_publication_rejected_alert_by_state_id(state_id):
            return model.AlertsStates.publication_rejected_alert

        if await self.state_repo.get_vizard_video_cut_alert_by_state_id(state_id):
            return model.AlertsStates.video_generated_alert

        return None

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

from aiogram_dialog import DialogManager, StartMode

from internal import interface, model


class _AlertsChecker:
    def __init__(self, state_repo: interface.IStateRepo):
        self.state_repo = state_repo

    async def check_alerts(
            self,
            dialog_manager: DialogManager,
            state: model.UserState
    ) -> bool:
        publication_approved_alerts = await self.state_repo.get_publication_approved_alert_by_state_id(
            state_id=state.id
        )
        if publication_approved_alerts:
            await dialog_manager.start(
                model.AlertsStates.publication_approved_alert,
                mode=StartMode.RESET_STACK
            )
            return True

        publication_rejected_alerts = await self.state_repo.get_publication_rejected_alert_by_state_id(
            state_id=state.id
        )
        if publication_rejected_alerts:
            await dialog_manager.start(
                model.AlertsStates.publication_rejected_alert,
                mode=StartMode.RESET_STACK
            )
            return True

        vizard_alerts = await self.state_repo.get_vizard_video_cut_alert_by_state_id(
            state_id=state.id
        )
        if vizard_alerts:
            await dialog_manager.start(
                model.AlertsStates.video_generated_alert,
                mode=StartMode.RESET_STACK
            )
            return True

        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=True
        )

        return False

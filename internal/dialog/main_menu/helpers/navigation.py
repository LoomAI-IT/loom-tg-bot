from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from internal import interface, model


class NavigationManager:
    def __init__(
            self,
            state_repo: interface.IStateRepo,
    ):
        self.state_repo = state_repo

    async def navigate_to_content(
            self,
            callback: CallbackQuery,
            dialog_manager: DialogManager,
            state: model.UserState
    ) -> None:
        await self.state_repo.change_user_state(
            state_id=state.id,
            show_error_recovery=False
        )

        await dialog_manager.start(
            state=model.ContentMenuStates.content_menu,
            mode=StartMode.RESET_STACK
        )

        await callback.answer()

    async def navigate_to_organization(
            self,
            callback: CallbackQuery,
            dialog_manager: DialogManager,
            state: model.UserState
    ) -> None:
        await self.state_repo.change_user_state(
            state_id=state.id,
            show_error_recovery=False
        )

        await dialog_manager.start(
            state=model.OrganizationMenuStates.organization_menu,
            mode=StartMode.RESET_STACK
        )

        await callback.answer()

    async def navigate_to_personal_profile(
            self,
            callback: CallbackQuery,
            dialog_manager: DialogManager,
            state: model.UserState
    ) -> None:
        await self.state_repo.change_user_state(
            state_id=state.id,
            show_error_recovery=False
        )

        await dialog_manager.start(
            state=model.PersonalProfileStates.personal_profile,
            mode=StartMode.RESET_STACK
        )

        await callback.answer()

from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method

from internal.dialog.helpers import StateManager
from internal.dialog.organization.organization_menu.helpers import PermissionChecker


class OrganizationMenuService(interface.IOrganizationMenuService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            llm_chat_repo: interface.ILLMChatRepo,
            loom_employee_client: interface.ILoomEmployeeClient
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.llm_chat_repo = llm_chat_repo
        self.loom_employee_client = loom_employee_client

        # Инициализация приватных сервисов
        self.state_manager = StateManager(state_repo)
        self.permission_checker = PermissionChecker(self.logger, loom_employee_client)

    @auto_log()
    @traced_method()
    async def handle_go_to_employee_settings(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        state = await self.state_manager.get_state(dialog_manager)

        if not await self.permission_checker.check_employee_settings_permission(state, callback):
            return

        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=False
        )

        await dialog_manager.start(
            state=model.ChangeEmployeeStates.employee_list,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_update_organization(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        await callback.answer("В разработке", show_alert=True)
        return
        # self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        #
        # state = await self.state_manager.get_state(dialog_manager)
        #
        # if not await self.permission_checker.check_update_organization_permission(state, callback):
        #     return
        #
        # await callback.answer()
        #
        # await self._chat_manager.clear_chat(state.id)
        #
        # await dialog_manager.start(
        #     model.UpdateOrganizationStates.update_organization,
        #     mode=StartMode.RESET_STACK
        # )

    @auto_log()
    @traced_method()
    async def handle_go_to_update_category(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager)

        if not await self.permission_checker.check_update_category_permission(state, callback):
            return

        await callback.answer()

        chat = await self.llm_chat_repo.get_chat_by_state_id(state.id)
        if chat:
            await self.llm_chat_repo.delete_chat(chat_id=chat[0].id)

        await dialog_manager.start(
            state=model.UpdateCategoryStates.select_category,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_add_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        state = await self.state_manager.get_state(dialog_manager)

        if not await self.permission_checker.check_add_employee_permission(state, callback):
            return

        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=False
        )

        await dialog_manager.start(
            state=model.AddEmployeeStates.enter_account_id,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_top_up_balance(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        await callback.answer("Функция в разработке", show_alert=True)

    @auto_log()
    @traced_method()
    async def handle_go_to_social_networks(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await dialog_manager.start(state=model.AddSocialNetworkStates.select_network)

    @auto_log()
    @traced_method()
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        await dialog_manager.start(
            state=model.MainMenuStates.main_menu,
            mode=StartMode.RESET_STACK
        )

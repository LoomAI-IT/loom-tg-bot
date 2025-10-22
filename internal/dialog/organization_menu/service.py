from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode, ShowMode

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


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

    @auto_log()
    @traced_method()
    async def handle_go_to_employee_settings(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        state = await self._get_state(dialog_manager)

        employee = await self.loom_employee_client.get_employee_by_account_id(
            state.account_id,
        )

        if not employee.edit_employee_perm_permission:
            self.logger.info("Отказано в доступе")
            await callback.answer("Недостаточно прав для управления сотрудниками", show_alert=True)
            return

        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=False
        )

        await dialog_manager.start(
            model.ChangeEmployeeStates.employee_list,
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
        # dialog_manager.show_mode = ShowMode.EDIT
        #
        # state = await self._get_state(dialog_manager)
        #
        # employee = await self.loom_employee_client.get_employee_by_account_id(
        #     state.account_id
        # )
        #
        # if not employee.setting_category_permission:
        #     self.logger.info("Отказано в доступе")
        #     await callback.answer("У вас нет прав обновлять организацию", show_alert=True)
        #     return
        #
        # await callback.answer()
        #
        # chat = await self.llm_chat_repo.get_chat_by_state_id(state.id)
        # if chat:
        #     await self.llm_chat_repo.delete_chat(chat[0].id)
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
        dialog_manager.show_mode = ShowMode.EDIT

        state = await self._get_state(dialog_manager)

        employee = await self.loom_employee_client.get_employee_by_account_id(
            state.account_id
        )

        if not employee.setting_category_permission:
            self.logger.info("Отказано в доступе")
            await callback.answer("У вас нет прав обновлять рубрики", show_alert=True)
            return

        await callback.answer()

        await dialog_manager.start(
            model.UpdateCategoryStates.select_category,
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
        state = await self._get_state(dialog_manager)

        employee = await self.loom_employee_client.get_employee_by_account_id(
            state.account_id,
        )

        if not employee.add_employee_permission:
            self.logger.info("Отказано в доступе")
            await callback.answer("Недостаточно прав для добавления сотрудников", show_alert=True)
            return

        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=False
        )

        await dialog_manager.start(
            model.AddEmployeeStates.enter_account_id,
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
        dialog_manager.show_mode = ShowMode.EDIT
        await dialog_manager.start(model.AddSocialNetworkStates.select_network)

    @auto_log()
    @traced_method()
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        await dialog_manager.start(
            model.MainMenuStates.main_menu,
            mode=StartMode.RESET_STACK
        )


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

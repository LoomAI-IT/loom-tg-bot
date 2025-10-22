import uuid
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode, ShowMode

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class IntroService(interface.IIntroService):

    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            llm_chat_repo: interface.ILLMChatRepo,
            loom_account_client: interface.ILoomAccountClient,
            loom_employee_client: interface.ILoomEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.llm_chat_repo = llm_chat_repo
        self.loom_account_client = loom_account_client
        self.loom_employee_client = loom_employee_client

    @auto_log()
    @traced_method()
    async def accept_user_agreement(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.dialog_data["user_agreement_accepted"] = True
        await dialog_manager.switch_to(model.IntroStates.privacy_policy)

    @auto_log()
    @traced_method()
    async def accept_privacy_policy(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.dialog_data["privacy_policy_accepted"] = True
        await dialog_manager.switch_to(model.IntroStates.data_processing)

    @auto_log()
    @traced_method()
    async def accept_data_processing(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager,
    ) -> None:
        chat_id = callback.message.chat.id

        dialog_manager.dialog_data["data_processing_accepted"] = True

        authorized_data = await self.loom_account_client.register_from_tg(
            uuid.uuid4().hex,
            uuid.uuid4().hex,
        )

        state = (await self.state_repo.state_by_id(chat_id))[0]

        await self.state_repo.change_user_state(
            state.id,
            account_id=authorized_data.account_id,
            access_token=authorized_data.access_token,
            refresh_token=authorized_data.refresh_token
        )

        await dialog_manager.switch_to(model.IntroStates.intro)

    @auto_log()
    @traced_method()
    async def go_to_create_organization(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await callback.answer()

        state = await self._get_state(dialog_manager)

        chat = await self.llm_chat_repo.get_chat_by_state_id(state.id)
        if chat:
            await self.llm_chat_repo.delete_chat(chat[0].id)

        await dialog_manager.start(
            model.CreateOrganizationStates.create_organization,
            mode=StartMode.RESET_STACK
        )

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            chat_id = None

        state = (await self.state_repo.state_by_id(chat_id))[0]
        return state

from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class IntroGetter(interface.IIntroGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            domain: str,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.domain = domain

    @auto_log()
    @traced_method()
    async def get_agreement_data(self, **kwargs) -> dict:
        data = {
            "user_agreement_link": f"https://{self.domain}/agreement",
            "privacy_policy_link": f"https://{self.domain}/privacy",
            "data_processing_link": f"https://{self.domain}/data-processing",
        }

        return data

    @auto_log()
    @traced_method()
    async def get_user_status(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        user = dialog_manager.event.from_user

        state = await self._get_state(dialog_manager)

        data = {
            "name": user.first_name or "Пользователь",
            "username": user.username,
            "account_id": state.account_id,
        }
        return data

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            chat_id = None

        state = (await self.state_repo.state_by_id(chat_id))[0]
        return state

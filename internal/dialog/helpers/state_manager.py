from aiogram_dialog import DialogManager, ShowMode

from internal import interface, model


class StateManager:
    def __init__(self, state_repo: interface.IStateRepo):
        self.state_repo = state_repo

    @staticmethod
    def set_show_mode(
            dialog_manager: DialogManager,
            edit: bool = False,
            delete_and_send: bool = False,
            send: bool = False,
            no_update: bool = False,
    ) -> None:
        if edit:
            dialog_manager.show_mode = ShowMode.EDIT
        elif delete_and_send:
            dialog_manager.show_mode = ShowMode.DELETE_AND_SEND
        elif send:
            dialog_manager.show_mode = ShowMode.SEND
        elif no_update:
            dialog_manager.show_mode = ShowMode.NO_UPDATE

    async def get_state(self, dialog_manager: DialogManager) -> model.UserState:
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

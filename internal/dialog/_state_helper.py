from aiogram_dialog import DialogManager, ShowMode

from internal import interface, model


class _StateHelper:
    def __init__(self, state_repo: interface.IStateRepo):
        self.state_repo = state_repo

    @staticmethod
    def set_edit_mode(dialog_manager: DialogManager) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

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

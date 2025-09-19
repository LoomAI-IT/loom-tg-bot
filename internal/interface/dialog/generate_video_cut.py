from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import Message


class IGenerateVideoCutDialog(Protocol):
    def get_dialog(self) -> Dialog: pass

    def get_youtube_link_input_window(self) -> Window: pass


class IGenerateVideoCutDialogService(Protocol):
    async def get_youtube_input_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    async def handle_youtube_link_input(
            self,
            message: Message,
            message_input: Any,
            dialog_manager: DialogManager
    ) -> None: pass
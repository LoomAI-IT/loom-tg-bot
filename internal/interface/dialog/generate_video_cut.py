from abc import abstractmethod
from typing import Protocol, Any
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, Dialog, Window


class IGenerateVideoCutDialog(Protocol):

    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_youtube_link_input_window(self) -> Window: pass


class IGenerateVideoCutService(Protocol):

    @abstractmethod
    async def handle_youtube_link_input(
            self,
            message: Message,
            message_input: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass


class IGenerateVideoCutGetter(Protocol):

    @abstractmethod
    async def get_youtube_input_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

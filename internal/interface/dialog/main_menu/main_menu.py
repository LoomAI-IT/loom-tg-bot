from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from aiogram_dialog.widgets.input import MessageInput


class IMainMenuDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_main_menu_window(self) -> Window:
        pass


class IMainMenuService(Protocol):
    @abstractmethod
    async def handle_go_to_content(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_generate_publication_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_organization(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_personal_profile(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass


class IMainMenuGetter(Protocol):
    @abstractmethod
    async def get_main_menu_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

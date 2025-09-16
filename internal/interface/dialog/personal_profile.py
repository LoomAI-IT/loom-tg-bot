from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from internal import model


class IPersonalProfileDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_personal_profile_window(self) -> Window: pass

    @abstractmethod
    def get_faq_window(self) -> Window: pass

    @abstractmethod
    def get_support_window(self) -> Window: pass


class IPersonalProfileDialogService(Protocol):
    @abstractmethod
    async def get_personal_profile_data(
            self,
            dialog_manager: DialogManager,
            user_state: model.UserState,
    ) -> dict: pass

    @abstractmethod
    async def handle_go_faq(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_go_to_support(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass
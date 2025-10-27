from abc import abstractmethod
from typing import Protocol, Any

from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery


class IPersonalProfileDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_personal_profile_window(self) -> Window: pass

    @abstractmethod
    def get_faq_window(self) -> Window: pass

    @abstractmethod
    def get_support_window(self) -> Window: pass


class IPersonalProfileService(Protocol):

    @abstractmethod
    async def handle_go_faq(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_support(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_back_to_profile(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass


class IPersonalProfileGetter(Protocol):
    @abstractmethod
    async def get_personal_profile_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

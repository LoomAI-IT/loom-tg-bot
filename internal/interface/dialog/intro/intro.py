from abc import abstractmethod
from typing import Protocol, Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, Dialog, Window


class IIntroDialog(Protocol):

    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_welcome_window(self) -> Window: pass

    @abstractmethod
    def get_user_agreement_window(self) -> Window: pass

    @abstractmethod
    def get_privacy_policy_window(self) -> Window: pass

    @abstractmethod
    def get_data_processing_window(self) -> Window: pass

    @abstractmethod
    def get_intro_window(self) -> Window: pass


class IIntroService(Protocol):
    @abstractmethod
    async def accept_user_agreement(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def accept_privacy_policy(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def accept_data_processing(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager,
    ) -> None:
        pass

    @abstractmethod
    async def go_to_create_organization(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass


class IIntroGetter(Protocol):

    @abstractmethod
    async def get_agreement_data(self) -> dict:
        pass

    @abstractmethod
    async def get_user_status(
            self,
            dialog_manager: DialogManager
    ) -> dict:
        pass

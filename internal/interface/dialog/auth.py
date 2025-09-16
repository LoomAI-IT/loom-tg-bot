from abc import abstractmethod
from typing import Protocol, Any

from aiogram import Bot
from aiogram.fsm.state import StatesGroup
from aiogram_dialog import DialogManager, Dialog
from aiogram.types import CallbackQuery, Update

from internal import model


class IAuthDialogController(Protocol):
    """Интерфейс для обработчиков авторизации"""

    @abstractmethod
    async def accept_user_agreement(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        """Принять пользовательское соглашение"""
        pass

    @abstractmethod
    async def accept_privacy_policy(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        """Принять политику конфиденциальности"""
        pass

    @abstractmethod
    async def accept_data_processing(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        """Принять согласие на обработку данных"""
        pass

    @abstractmethod
    async def handle_access_denied(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        """Обработать отказ в доступе"""
        pass


class IAuthDialogService(Protocol):
    """Интерфейс для получения данных авторизации"""

    @abstractmethod
    async def get_agreement_data(self) -> dict: pass

    @abstractmethod
    async def get_user_status(
            self,
            dialog_manager: DialogManager,
            user_state: model.UserState,
    ) -> dict: pass


class IAuthDialog(Protocol):
    """Интерфейс для диалога авторизации"""

    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_states(self) -> type[StatesGroup]:
        pass

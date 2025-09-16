from abc import abstractmethod
from typing import Protocol, Any

from aiogram.fsm.state import StatesGroup
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram.types import CallbackQuery


class IAuthDialogWindows(Protocol):
    """Интерфейс для окон авторизации"""

    @abstractmethod
    def get_user_agreement_window(self) -> Window:
        """Окно пользовательского соглашения"""
        pass

    @abstractmethod
    def get_privacy_policy_window(self) -> Window:
        """Окно политики конфиденциальности"""
        pass

    @abstractmethod
    def get_data_processing_window(self) -> Window:
        """Окно согласия на обработку данных"""
        pass

    @abstractmethod
    def get_welcome_window(self) -> Window:
        """Приветственное окно"""
        pass

    @abstractmethod
    def get_access_denied_window(self) -> Window:
        """Окно отказа в доступе"""
        pass


class IAuthDialogHandler(Protocol):
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
    async def get_agreement_data(self, dialog_manager: DialogManager) -> dict:
        """Получает данные для окна соглашений"""
        pass

    @abstractmethod
    async def get_user_status(self, dialog_manager: DialogManager) -> dict:
        """Получает статус пользователя"""
        pass


class IAuthDialog(Protocol):
    """Интерфейс для диалога авторизации"""

    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_states(self) -> type[StatesGroup]:
        pass

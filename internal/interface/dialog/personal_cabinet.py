from abc import abstractmethod
from typing import Protocol

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, Window


class IPersonalCabinetDialogGetter(Protocol):
    """Интерфейс для получения данных личного кабинета"""

    @abstractmethod
    async def get_profile_data(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        """Получает данные профиля пользователя"""
        pass

    @abstractmethod
    async def get_organization_data(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        """Получает данные организации"""
        pass

    @abstractmethod
    async def get_permissions(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        """Получает права пользователя"""
        pass

    @abstractmethod
    async def get_social_networks(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        """Получает подключенные соцсети"""
        pass


class IPersonalCabinetDialogHandler(Protocol):
    """Интерфейс для обработчиков личного кабинета"""

    @abstractmethod
    async def connect_vk(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def connect_telegram(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def connect_youtube(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def connect_instagram(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def disconnect_social_network(self, callback: CallbackQuery, button: Any,
                                        dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def confirm_disconnect(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass


class IPersonalCabinetDialogWindows(Protocol):
    """Интерфейс для окон личного кабинета"""

    @abstractmethod
    def get_profile_window(self) -> Window:
        pass

    @abstractmethod
    def get_account_window(self) -> Window:
        pass

    @abstractmethod
    def get_social_networks_window(self) -> Window:
        pass

    @abstractmethod
    def get_disconnect_confirmation_window(self) -> Window:
        pass
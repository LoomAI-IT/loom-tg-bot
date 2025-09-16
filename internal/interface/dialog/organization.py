from abc import abstractmethod
from typing import Protocol

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, Window



class IOrganizationDialogGetter(Protocol):
    """Интерфейс для получения данных организации"""

    @abstractmethod
    async def get_organization_profile(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_employees_list(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_rubrics_list(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_balance_info(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_social_platforms(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass


class IOrganizationDialogHandler(Protocol):
    """Интерфейс для обработчиков организации"""

    @abstractmethod
    async def add_employee_by_id(self, message: Message, widget: Any, dialog_manager: DialogManager, text: str) -> None:
        pass

    @abstractmethod
    async def remove_employee(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def confirm_remove_employee(self, callback: CallbackQuery, button: Any,
                                      dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def toggle_permission(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def save_employee_permissions(self, callback: CallbackQuery, button: Any,
                                        dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def top_up_balance(self, message: Message, widget: Any, dialog_manager: DialogManager, text: str) -> None:
        pass

    @abstractmethod
    async def toggle_autoposting(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def toggle_moderation(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass


class IOrganizationDialogWindows(Protocol):
    """Интерфейс для окон организации"""

    @abstractmethod
    def get_profile_window(self) -> Window:
        pass

    @abstractmethod
    def get_users_management_window(self) -> Window:
        pass

    @abstractmethod
    def get_add_user_window(self) -> Window:
        pass

    @abstractmethod
    def get_user_permissions_window(self) -> Window:
        pass

    @abstractmethod
    def get_remove_user_confirmation_window(self) -> Window:
        pass

    @abstractmethod
    def get_balance_window(self) -> Window:
        pass

    @abstractmethod
    def get_social_networks_settings_window(self) -> Window:
        pass

    @abstractmethod
    def get_rubrics_window(self) -> Window:
        pass
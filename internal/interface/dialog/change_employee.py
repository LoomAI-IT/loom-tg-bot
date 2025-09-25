from abc import abstractmethod
from typing import Protocol, Any

from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message


class IChangeEmployeeDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_employee_list_window(self) -> Window:
        pass

    @abstractmethod
    def get_employee_detail_window(self) -> Window:
        pass

    @abstractmethod
    def get_change_permissions_window(self) -> Window:
        pass

    @abstractmethod
    def get_confirm_delete_window(self) -> Window:
        pass

    @abstractmethod
    def get_change_role_window(self) -> Window:
        pass


class IChangeEmployeeService(Protocol):
    # Обработчики списка сотрудников
    @abstractmethod
    async def handle_select_employee(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            employee_id: str
    ) -> None:
        pass

    @abstractmethod
    async def handle_search_employee(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            search_query: str
    ) -> None:
        pass

    @abstractmethod
    async def handle_clear_search(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_refresh_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    # Обработчики навигации
    @abstractmethod
    async def handle_navigate_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_organization_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    # Обработчики разрешений
    @abstractmethod
    async def handle_toggle_permission(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_save_permissions(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_reset_permissions(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    # Обработчики изменения роли
    @abstractmethod
    async def handle_show_role_change(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_select_role(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            role: str
    ) -> None:
        pass

    @abstractmethod
    async def handle_reset_role_selection(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_confirm_role_change(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    # Обработчики удаления
    @abstractmethod
    async def handle_delete_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass


class IChangeEmployeeGetter(Protocol):

    @abstractmethod
    async def get_employee_list_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        pass

    @abstractmethod
    async def get_employee_detail_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        pass

    @abstractmethod
    async def get_permissions_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        pass

    @abstractmethod
    async def get_delete_confirmation_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        pass

    @abstractmethod
    async def get_role_change_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        pass
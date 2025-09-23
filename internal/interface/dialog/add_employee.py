from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message


class IAddEmployeeDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_enter_account_id_window(self) -> Window: pass

    @abstractmethod
    def get_enter_name_window(self) -> Window: pass

    @abstractmethod
    def get_enter_role_window(self) -> Window: pass

    @abstractmethod
    def get_set_permissions_window(self) -> Window: pass

    @abstractmethod
    def get_confirm_employee_window(self) -> Window: pass


class IAddEmployeeService(Protocol):
    @abstractmethod
    async def handle_account_id_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            account_id: str
    ) -> None: pass

    @abstractmethod
    async def handle_name_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            name: str
    ) -> None: pass

    @abstractmethod
    async def handle_role_selection(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            role: str
    ) -> None: pass

    @abstractmethod
    async def handle_toggle_permission(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_create_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_go_to_organization_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

class IAddEmployeeGetter(Protocol):
    @abstractmethod
    async def get_enter_account_id_data(self) -> dict: pass

    @abstractmethod
    async def get_enter_name_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_enter_role_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_permissions_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_confirm_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

from abc import abstractmethod
from typing import Protocol, Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, Dialog, Window


class IOrganizationMenuDialog(Protocol):

    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_organization_menu_window(self) -> Window: pass


class IOrganizationMenuService(Protocol):
    @abstractmethod
    async def handle_go_to_employee_settings(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_add_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_top_up_balance(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_social_networks(
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


class IOrganizationMenuGetter(Protocol):

    @abstractmethod
    async def get_organization_menu_data(
            self,
            dialog_manager: DialogManager
    ) -> dict:
        pass

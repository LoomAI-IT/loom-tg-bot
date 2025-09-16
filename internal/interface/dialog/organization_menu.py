from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from internal import model


class IOrganizationMenuDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_organization_menu_window(self) -> Window: pass

class IPersonalProfileService(Protocol):
    @abstractmethod
    async def get_organization_menu_data(
            self,
            dialog_manager: DialogManager,
            user_state: model.UserState,
            **kwargs
    ) -> dict: pass

    @abstractmethod
    async def handle_go_to_add_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_go_to_add_social_network(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

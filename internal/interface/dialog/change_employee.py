from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from internal import model


class IChangeEmployeeDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_search_employee_window(self) -> Window: pass

    @abstractmethod
    def get_employee_list_window(self) -> Window: pass

    @abstractmethod
    def get_change_employee_window(self) -> Window: pass

class IPersonalProfileService(Protocol):
    @abstractmethod
    async def get_employee_data(
            self,
            dialog_manager: DialogManager,
            user_state: model.UserState,
            **kwargs
    ) -> dict: pass

    @abstractmethod
    async def handle_go_to_employee_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass
from typing import Protocol
from abc import abstractmethod

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from internal import model


class IUpdateOrganizationDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_update_organization_window(self) -> Window:
        pass

    @abstractmethod
    def get_confirm_cancel_window(self) -> Window:
        pass

    @abstractmethod
    def get_organization_result_window(self) -> Window:
        pass


class IUpdateOrganizationService(Protocol):
    @abstractmethod
    async def handle_user_message(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_confirm_cancel(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        pass


class IUpdateOrganizationGetter(Protocol):
    @abstractmethod
    async def get_update_organization_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

class IUpdateOrganizationPromptGenerator(Protocol):
    @abstractmethod
    async def get_update_organization_system_prompt(self, organization: model.Organization) -> str:
        pass

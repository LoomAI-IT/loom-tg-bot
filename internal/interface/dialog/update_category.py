from typing import Protocol, Any
from abc import abstractmethod

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from internal import model


class IUpdateCategoryDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_update_category_window(self) -> Window:
        pass

    @abstractmethod
    def get_category_result_window(self) -> Window:
        pass


class IUpdateCategoryService(Protocol):
    @abstractmethod
    async def handle_user_message(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_select_category(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            category_id: str
    ) -> None: pass

    @abstractmethod
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        pass


class IUpdateCategoryGetter(Protocol):
    @abstractmethod
    async def get_update_category_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_select_category_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass


class IUpdateCategoryPromptGenerator(Protocol):
    @abstractmethod
    async def get_update_category_system_prompt(
            self,
            organization: model.Organization,
            category: model.Category
    ) -> str:
        pass

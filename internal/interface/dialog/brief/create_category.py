from typing import Protocol
from abc import abstractmethod

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from internal import model


class ICreateCategoryDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_create_category_window(self) -> Window:
        pass

    @abstractmethod
    def get_confirm_cancel_window(self) -> Window:
        pass

    @abstractmethod
    def get_category_result_window(self) -> Window:
        pass


class ICreateCategoryService(Protocol):
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


class ICreateCategoryGetter(Protocol):
    @abstractmethod
    async def get_create_category_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass


class ICreateCategoryPromptGenerator(Protocol):
    @abstractmethod
    async def get_create_category_system_prompt(self, organization: model.Organization) -> str:
        pass

class ITrainCategoryPromptGenerator(Protocol):
    @abstractmethod
    async def get_train_category_system_prompt(self, organization: model.Organization, category: model.Category) -> str:
        pass

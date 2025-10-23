from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from aiogram_dialog.widgets.input import MessageInput


class IContentMenuDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_content_menu_window(self) -> Window: pass

    @abstractmethod
    def get_content_type_selection_window(self) -> Window: pass

    @abstractmethod
    def get_drafts_type_selection_window(self) -> Window: pass

    @abstractmethod
    def get_moderation_type_selection_window(self) -> Window: pass


class IContentMenuGetter(Protocol):

    @abstractmethod
    async def get_content_menu_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_drafts_type_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_moderation_type_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass


class IContentMenuService(Protocol):

    @abstractmethod
    async def handle_go_to_publication_generation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_video_cut_generation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_publication_drafts(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_video_drafts(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_publication_moderation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_video_moderation(
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

    @abstractmethod
    async def handle_go_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

# internal/interface/dialog/moderation_publication.py
from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from internal import model


class IModerationPublicationDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_moderation_list_window(self) -> Window: pass

    @abstractmethod
    def get_publication_review_window(self) -> Window: pass

    @abstractmethod
    def get_reject_comment_window(self) -> Window: pass


class IModerationPublicationDialogService(Protocol):
    @abstractmethod
    async def get_moderation_list_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def handle_select_publication(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            publication_id: str
    ) -> None: pass

    @abstractmethod
    async def get_publication_review_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def handle_navigate_publication(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_approve_publication(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_reject_publication(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_edit_before_approve(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_reject_comment_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            comment: str
    ) -> None: pass

    @abstractmethod
    async def handle_send_rejection(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_back_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def get_reject_comment_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass
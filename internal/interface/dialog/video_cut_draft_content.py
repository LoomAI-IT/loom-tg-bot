# internal/interface/dialog/video_cut_draft_content.py
from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from internal import model


class IVideoCutDraftContentDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_video_drafts_list_window(self) -> Window: pass

    @abstractmethod
    def get_video_draft_detail_window(self) -> Window: pass

    @abstractmethod
    def get_edit_video_draft_window(self) -> Window: pass


class IVideoCutDraftContentDialogService(Protocol):
    @abstractmethod
    async def get_video_drafts_list_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def handle_select_video_draft(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            video_id: str
    ) -> None: pass

    @abstractmethod
    async def get_video_draft_detail_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def handle_navigate_video(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_edit_video_draft(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_delete_video_draft(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_send_to_moderation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_publish_video(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_edit_title(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            title: str
    ) -> None: pass

    @abstractmethod
    async def handle_edit_description(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            description: str
    ) -> None: pass

    @abstractmethod
    async def handle_toggle_platform(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_save_video_changes(
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
    async def get_edit_video_draft_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass
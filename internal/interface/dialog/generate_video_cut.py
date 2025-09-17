# internal/interface/dialog/generate_video_cut.py
from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from internal import model


class IGenerateVideoCutDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_input_youtube_link_window(self) -> Window: pass

    @abstractmethod
    def get_processing_window(self) -> Window: pass

    @abstractmethod
    def get_video_preview_window(self) -> Window: pass

    @abstractmethod
    def get_edit_video_details_window(self) -> Window: pass

    @abstractmethod
    def get_select_platforms_window(self) -> Window: pass


class IGenerateVideoCutDialogService(Protocol):
    @abstractmethod
    async def handle_youtube_link_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            link: str
    ) -> None: pass

    @abstractmethod
    async def get_processing_status(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_video_preview_data(
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
    async def handle_delete_video(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_toggle_platform(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_add_to_drafts(
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
    async def handle_publish(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def get_platforms_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass
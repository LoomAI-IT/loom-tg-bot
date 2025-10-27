from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import ManagedCheckbox


class IVideoCutModerationDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_moderation_list_window(self) -> Window: pass

    @abstractmethod
    def get_reject_comment_window(self) -> Window: pass

    # Окна редактирования с превью видео
    @abstractmethod
    def get_edit_preview_window(self) -> Window: pass

    @abstractmethod
    def get_edit_title_window(self) -> Window: pass

    @abstractmethod
    def get_edit_description_window(self) -> Window: pass

    @abstractmethod
    def get_edit_tags_window(self) -> Window: pass

    @abstractmethod
    def get_social_network_select_window(self) -> Window: pass


class IVideoCutModerationService(Protocol):

    @abstractmethod
    async def handle_navigate_video_cut(
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

    # Обработчики редактирования полей
    @abstractmethod
    async def handle_edit_title(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None: pass

    @abstractmethod
    async def handle_edit_description(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None: pass

    @abstractmethod
    async def handle_edit_tags(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None: pass

    @abstractmethod
    async def handle_save_edits(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_back_to_moderation_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    # Обработчики выбора социальных сетей
    @abstractmethod
    async def handle_toggle_social_network(
            self,
            callback: CallbackQuery,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_publish_now(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    # Навигация
    @abstractmethod
    async def handle_back_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

class IVideoCutModerationGetter(Protocol):
    @abstractmethod
    async def get_moderation_list_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_reject_comment_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_edit_preview_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    # Дополнительные геттеры для окон редактирования
    @abstractmethod
    async def get_edit_title_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_edit_description_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_edit_tags_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

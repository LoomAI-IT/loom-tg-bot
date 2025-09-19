from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from aiogram_dialog.widgets.input import MessageInput


class IVideoCutsDraftDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_video_cut_list_window(self) -> Window: pass

    @abstractmethod
    def get_edit_preview_window(self) -> Window: pass

    @abstractmethod
    def get_edit_title_window(self) -> Window: pass

    @abstractmethod
    def get_edit_description_window(self) -> Window: pass

    @abstractmethod
    def get_edit_tags_window(self) -> Window: pass

    @abstractmethod
    def get_publication_settings_window(self) -> Window: pass


class IVideoCutsDraftDialogService(Protocol):
    # Обработчики для списка черновиков
    @abstractmethod
    async def get_video_cut_list_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def handle_navigate_video_cut(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    # Основные действия с черновиками
    @abstractmethod
    async def handle_send_to_moderation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_publish_now(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_delete_video_cut(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    # Обработчики для окна редактирования с превью
    @abstractmethod
    async def get_edit_preview_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def handle_save_changes(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    # Обработчики редактирования полей
    @abstractmethod
    async def handle_edit_title_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None: pass

    @abstractmethod
    async def handle_edit_description_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None: pass

    @abstractmethod
    async def handle_edit_tags_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None: pass

    # Обработчики настроек публикации
    @abstractmethod
    async def handle_toggle_platform(
            self,
            callback: CallbackQuery,
            checkbox: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_schedule_publication(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    # Навигация
    @abstractmethod
    async def handle_back_to_video_cut_list(
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

    @abstractmethod
    async def get_publication_settings_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass
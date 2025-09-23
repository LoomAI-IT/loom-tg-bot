from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import ManagedCheckbox


class IModerationPublicationDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_moderation_list_window(self) -> Window: pass

    @abstractmethod
    def get_reject_comment_window(self) -> Window: pass

    # Окна редактирования с новым UX
    @abstractmethod
    def get_edit_preview_window(self) -> Window: pass

    # Новое меню редактирования текста
    @abstractmethod
    def get_edit_text_menu_window(self) -> Window: pass

    @abstractmethod
    def get_regenerate_text_window(self) -> Window: pass

    @abstractmethod
    def get_edit_title_window(self) -> Window: pass

    @abstractmethod
    def get_edit_tags_window(self) -> Window: pass

    @abstractmethod
    def get_edit_content_window(self) -> Window: pass

    @abstractmethod
    def get_edit_image_menu_window(self) -> Window: pass

    @abstractmethod
    def get_generate_image_window(self) -> Window: pass

    @abstractmethod
    def get_upload_image_window(self) -> Window: pass

    @abstractmethod
    def get_social_network_select_window(self) -> Window: pass


class IModerationPublicationService(Protocol):

    @abstractmethod
    async def handle_navigate_publication(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_toggle_social_network(
            self,
            callback: CallbackQuery,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_prev_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_next_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_publish_with_selected_networks(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_publish_publication(
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
    async def handle_regenerate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_regenerate_text_with_prompt(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            prompt: str
    ) -> None: pass

    @abstractmethod
    async def handle_edit_title_save(
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

    @abstractmethod
    async def handle_edit_content_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None: pass

    @abstractmethod
    async def handle_generate_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_generate_image_with_prompt(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            prompt: str
    ) -> None: pass

    @abstractmethod
    async def handle_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_remove_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
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

    # Навигация
    @abstractmethod
    async def handle_back_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass


class IModerationPublicationGetter(Protocol):
    @abstractmethod
    async def get_moderation_list_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_social_network_select_data(
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
    async def get_regenerate_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_edit_title_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_edit_tags_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_edit_content_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_image_prompt_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

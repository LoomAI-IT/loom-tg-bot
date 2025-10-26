from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import ManagedCheckbox, Button


class IGeneratePublicationDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_select_category_window(self) -> Window: pass

    @abstractmethod
    def get_input_text_window(self) -> Window: pass

    @abstractmethod
    def get_generation_window(self) -> Window: pass

    @abstractmethod
    def get_preview_window(self) -> Window: pass

    @abstractmethod
    def get_edit_text_menu_window(self) -> Window: pass

    @abstractmethod
    def get_image_menu_window(self) -> Window: pass

    @abstractmethod
    def get_upload_image_window(self) -> Window: pass

    @abstractmethod
    def get_social_network_select_window(self) -> Window: pass

    @abstractmethod
    def get_edit_text_window(self) -> Window: pass

    @abstractmethod
    def get_text_too_long_alert_window(self) -> Window: pass

    @abstractmethod
    def get_publication_success_window(self) -> Window: pass

    @abstractmethod
    def get_combine_images_choice_window(self) -> Window: pass

    @abstractmethod
    def get_combine_images_upload_window(self) -> Window: pass

    @abstractmethod
    def get_combine_images_prompt_window(self) -> Window: pass

    @abstractmethod
    def get_new_image_confirm_window(self) -> Window: pass


class IGeneratePublicationService(Protocol):

    @abstractmethod
    async def handle_select_category(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            category_id: str
    ) -> None: pass

    @abstractmethod
    async def handle_go_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass


    @abstractmethod
    async def handle_generate_publication_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_generate_text_with_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_generate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def go_to_create_category(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_regenerate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_regenerate_text_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_edit_text(
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
    async def handle_edit_image_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
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
    async def handle_publish_now(
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
    async def handle_compress_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_remove_photo_from_long_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_combine_images_start(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_combine_with_current(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_combine_from_scratch(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_combine_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_prev_combine_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_next_combine_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_delete_combine_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_back_from_combine_upload(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_combine_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_execute_combine(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_new_image_confirm_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_combine_from_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_confirm_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_reject_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass


class IGeneratePublicationGetter(Protocol):

    @abstractmethod
    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_preview_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_input_text_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_categories_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass


    @abstractmethod
    async def get_edit_text_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_upload_image_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_text_too_long_alert_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_publication_success_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_combine_images_choice_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_combine_images_upload_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_combine_images_prompt_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_new_image_confirm_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

# internal/interface/dialog/generate_publication.py
from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message
from internal import model


class IGeneratePublicationDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_select_category_window(self) -> Window: pass

    @abstractmethod
    def get_input_text_window(self) -> Window: pass

    @abstractmethod
    def get_choose_image_option_window(self) -> Window: pass

    @abstractmethod
    def get_image_generation_window(self) -> Window: pass

    @abstractmethod
    def get_preview_window(self) -> Window: pass

    @abstractmethod
    def get_select_publish_location_window(self) -> Window: pass


class IGeneratePublicationDialogService(Protocol):
    @abstractmethod
    async def get_categories_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def handle_select_category(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            category_id: str
    ) -> None: pass

    @abstractmethod
    async def handle_text_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None: pass

    @abstractmethod
    async def handle_voice_input(
            self,
            message: Message,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_choose_with_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_choose_text_only(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_auto_generate_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_custom_prompt_image(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            prompt: str
    ) -> None: pass

    @abstractmethod
    async def handle_upload_image(
            self,
            message: Message,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_delete_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_edit_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_edit_image(
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
    async def handle_publish(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_select_publish_location(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def get_preview_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass

    @abstractmethod
    async def get_publish_locations_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict: pass
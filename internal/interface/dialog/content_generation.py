from abc import abstractmethod
from typing import Protocol

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, Window


class IContentGenerationDialogGetter(Protocol):
    """Интерфейс для получения данных генерации контента"""

    @abstractmethod
    async def get_content_types(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_rubrics(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_generated_content(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_publish_platforms(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass


class IContentGenerationDialogHandler(Protocol):
    """Интерфейс для обработчиков генерации контента"""

    @abstractmethod
    async def select_content_type(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def select_rubric(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def input_text_prompt(self, message: Message, widget: Any, dialog_manager: DialogManager, text: str) -> None:
        pass

    @abstractmethod
    async def generate_image_auto(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def input_image_prompt(self, message: Message, widget: Any, dialog_manager: DialogManager, text: str) -> None:
        pass

    @abstractmethod
    async def upload_image(self, message: Message, widget: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def delete_image(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def edit_text(self, message: Message, widget: Any, dialog_manager: DialogManager, text: str) -> None:
        pass

    @abstractmethod
    async def save_to_drafts(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def send_to_moderation(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def publish_content(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def select_publish_platforms(self, callback: CallbackQuery, button: Any,
                                       dialog_manager: DialogManager) -> None:
        pass


class IContentGenerationDialogWindows(Protocol):
    """Интерфейс для окон генерации контента"""

    @abstractmethod
    def get_select_type_window(self) -> Window:
        pass

    @abstractmethod
    def get_select_rubric_window(self) -> Window:
        pass

    @abstractmethod
    def get_text_input_window(self) -> Window:
        pass

    @abstractmethod
    def get_image_generation_window(self) -> Window:
        pass

    @abstractmethod
    def get_image_prompt_window(self) -> Window:
        pass

    @abstractmethod
    def get_preview_window(self) -> Window:
        pass

    @abstractmethod
    def get_edit_text_window(self) -> Window:
        pass

    @abstractmethod
    def get_publish_options_window(self) -> Window:
        pass
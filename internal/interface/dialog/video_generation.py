from abc import abstractmethod
from typing import Protocol

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, Window


class IVideoGenerationDialogGetter(Protocol):
    """Интерфейс для получения данных генерации видео"""

    @abstractmethod
    async def get_processing_status(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_video_list(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_current_video(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_publish_platforms(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass


class IVideoGenerationDialogHandler(Protocol):
    """Интерфейс для обработчиков генерации видео"""

    @abstractmethod
    async def input_youtube_link(self, message: Message, widget: Any, dialog_manager: DialogManager, text: str) -> None:
        pass

    @abstractmethod
    async def check_processing_status(self, callback: CallbackQuery, button: Any,
                                      dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def navigate_videos(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def edit_video_title(self, message: Message, widget: Any, dialog_manager: DialogManager, text: str) -> None:
        pass

    @abstractmethod
    async def edit_video_description(self, message: Message, widget: Any, dialog_manager: DialogManager,
                                     text: str) -> None:
        pass

    @abstractmethod
    async def delete_video(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def confirm_delete_video(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def publish_video(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def send_video_to_moderation(self, callback: CallbackQuery, button: Any,
                                       dialog_manager: DialogManager) -> None:
        pass


class IVideoGenerationDialogWindows(Protocol):
    """Интерфейс для окон генерации видео"""

    @abstractmethod
    def get_link_input_window(self) -> Window:
        pass

    @abstractmethod
    def get_processing_window(self) -> Window:
        pass

    @abstractmethod
    def get_videos_list_window(self) -> Window:
        pass

    @abstractmethod
    def get_video_preview_window(self) -> Window:
        pass

    @abstractmethod
    def get_edit_title_window(self) -> Window:
        pass

    @abstractmethod
    def get_edit_description_window(self) -> Window:
        pass

    @abstractmethod
    def get_delete_confirmation_window(self) -> Window:
        pass

    @abstractmethod
    def get_publish_options_window(self) -> Window:
        pass
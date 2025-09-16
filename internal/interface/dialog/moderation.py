from abc import abstractmethod
from typing import Protocol

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, Window


class IModerationDialogGetter(Protocol):
    """Интерфейс для получения данных модерации"""

    @abstractmethod
    async def get_moderation_queue(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_content_for_review(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_moderation_statistics(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass


class IModerationDialogHandler(Protocol):
    """Интерфейс для обработчиков модерации"""

    @abstractmethod
    async def select_content_for_review(self, callback: CallbackQuery, button: Any,
                                        dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def approve_content(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def reject_content(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def reject_with_comment(self, message: Message, widget: Any, dialog_manager: DialogManager,
                                  text: str) -> None:
        pass

    @abstractmethod
    async def edit_before_approve(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def navigate_moderation_queue(self, callback: CallbackQuery, button: Any,
                                        dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def publish_approved_content(self, callback: CallbackQuery, button: Any,
                                       dialog_manager: DialogManager) -> None:
        pass


class IModerationDialogWindows(Protocol):
    """Интерфейс для окон модерации"""

    @abstractmethod
    def get_queue_window(self) -> Window:
        pass

    @abstractmethod
    def get_content_review_window(self) -> Window:
        pass

    @abstractmethod
    def get_rejection_comment_window(self) -> Window:
        pass

    @abstractmethod
    def get_edit_before_approve_window(self) -> Window:
        pass

    @abstractmethod
    def get_publication_confirmation_window(self) -> Window:
        pass
from abc import abstractmethod
from typing import Protocol

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, Window


class IDraftsDialogGetter(Protocol):
    """Интерфейс для получения данных черновиков"""

    @abstractmethod
    async def get_drafts_list(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_draft_details(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_draft_count(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        pass


class IDraftsDialogHandler(Protocol):
    """Интерфейс для обработчиков черновиков"""

    @abstractmethod
    async def select_draft(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def edit_draft(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def delete_draft(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def confirm_delete_draft(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def publish_draft(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def send_draft_to_moderation(self, callback: CallbackQuery, button: Any,
                                       dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def navigate_drafts(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass


class IDraftsDialogWindows(Protocol):
    """Интерфейс для окон черновиков"""

    @abstractmethod
    def get_drafts_list_window(self) -> Window:
        pass

    @abstractmethod
    def get_draft_preview_window(self) -> Window:
        pass

    @abstractmethod
    def get_draft_edit_window(self) -> Window:
        pass

    @abstractmethod
    def get_delete_confirmation_window(self) -> Window:
        pass
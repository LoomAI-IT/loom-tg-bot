# internal/interface/dialog/main_menu.py
from abc import abstractmethod
from typing import Protocol

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, Window


class IMainMenuDialogGetter(Protocol):
    """Интерфейс для получения данных главного меню"""

    @abstractmethod
    async def get_menu_items(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        """Получает пункты меню в зависимости от прав пользователя"""
        pass

    @abstractmethod
    async def get_user_info(self, dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
        """Получает информацию о пользователе"""
        pass


class IMainMenuDialogHandler(Protocol):
    """Интерфейс для обработчиков главного меню"""

    @abstractmethod
    async def open_personal_cabinet(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def open_content_generation(self, callback: CallbackQuery, button: Any,
                                      dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def open_drafts(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def open_moderation(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def open_video_section(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def open_publications(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def open_faq(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass

    @abstractmethod
    async def open_support(self, callback: CallbackQuery, button: Any, dialog_manager: DialogManager) -> None:
        pass


class IMainMenuDialogWindows(Protocol):
    """Интерфейс для окон главного меню"""

    @abstractmethod
    def get_main_menu_window(self) -> Window:
        pass

    @abstractmethod
    def get_faq_window(self) -> Window:
        pass

    @abstractmethod
    def get_support_window(self) -> Window:
        pass
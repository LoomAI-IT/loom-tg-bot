from abc import abstractmethod
from typing import Protocol, Any
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, Dialog, Window


class IAlertsDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog: pass

    @abstractmethod
    def get_video_generated_alert_window(self) -> Window:
        pass

    @abstractmethod
    def get_publication_approved_alert_window(self) -> Window:
        pass


class IAlertsService(Protocol):

    @abstractmethod
    async def handle_go_to_video_drafts(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass


class IAlertsGetter(Protocol):

    @abstractmethod
    async def get_video_alert_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

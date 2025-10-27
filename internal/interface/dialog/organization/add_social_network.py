from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery, Message


class IAddSocialNetworkDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_select_network_window(self) -> Window:
        pass

    @abstractmethod
    def get_telegram_main_window(self) -> Window:
        pass

    @abstractmethod
    def get_telegram_connect_window(self) -> Window:
        pass

    @abstractmethod
    def get_telegram_edit_window(self) -> Window:
        pass

    @abstractmethod
    def get_vkontakte_setup_window(self) -> Window:
        pass

    @abstractmethod
    def get_youtube_setup_window(self) -> Window:
        pass

    @abstractmethod
    def get_instagram_setup_window(self) -> Window:
        pass


class IAddSocialNetworkService(Protocol):
    # Обработчики ввода данных для telegram
    @abstractmethod
    async def handle_telegram_channel_username_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            telegram_channel_username: str
    ) -> None:
        pass

    @abstractmethod
    async def handle_new_telegram_channel_username_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            new_telegram_channel_username: str
    ) -> None:
        pass

    # Обработчики подключения и сохранения telegram
    @abstractmethod
    async def handle_save_telegram_connection(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_save_telegram_changes(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_back_from_edit(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    # Обработчик отключения telegram
    @abstractmethod
    async def handle_disconnect_telegram(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    # Навигация
    @abstractmethod
    async def handle_go_to_organization_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass


class IAddSocialNetworkGetter(Protocol):
    @abstractmethod
    async def get_select_network_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_telegram_main_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_telegram_connect_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_telegram_edit_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_vkontakte_setup_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_youtube_setup_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_instagram_setup_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_telegram_change_username_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass
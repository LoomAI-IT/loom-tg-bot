from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox


class _SocialNetworkHelper:
    def __init__(self, logger):
        self.logger = logger

    def is_network_connected(self, social_networks: dict, network_type: str) -> bool:
        if not social_networks:
            return False
        return network_type in social_networks and len(social_networks[network_type]) > 0

    def initialize_network_selection(
            self,
            social_networks: dict
    ) -> dict[str, bool]:
        selected_networks = {}

        vkontakte_connected = self.is_network_connected(social_networks, "vkontakte")
        telegram_connected = self.is_network_connected(social_networks, "telegram")

        if vkontakte_connected:
            widget_id = "vkontakte_checkbox"
            autoselect = social_networks["vkontakte"][0].get("autoselect", False)
            selected_networks[widget_id] = autoselect

        if telegram_connected:
            widget_id = "telegram_checkbox"
            autoselect = social_networks["telegram"][0].get("autoselect", False)
            selected_networks[widget_id] = autoselect

        return selected_networks

    async def setup_checkbox_states(
            self,
            dialog_manager: DialogManager,
            social_networks: dict,
            selected_networks: dict[str, bool]
    ) -> None:
        vkontakte_connected = self.is_network_connected(social_networks, "vkontakte")
        telegram_connected = self.is_network_connected(social_networks, "telegram")

        if vkontakte_connected:
            self.logger.info("Установка состояния VK чекбокса")
            widget_id = "vkontakte_checkbox"
            vkontakte_checkbox: ManagedCheckbox = dialog_manager.find(widget_id)
            await vkontakte_checkbox.set_checked(selected_networks[widget_id])

        if telegram_connected:
            self.logger.info("Установка состояния Telegram чекбокса")
            widget_id = "telegram_checkbox"
            telegram_checkbox: ManagedCheckbox = dialog_manager.find(widget_id)
            await telegram_checkbox.set_checked(selected_networks[widget_id])

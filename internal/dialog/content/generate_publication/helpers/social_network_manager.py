from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from internal import interface


class SocialNetworkManager:
    def __init__(
            self,
            logger,
            loom_content_client: interface.ILoomContentClient
    ):
        self.logger = logger
        self.loom_content_client = loom_content_client

    def is_network_connected(self, social_networks: dict, network_type: str) -> bool:

        if not social_networks:
            return False
        return network_type in social_networks and len(social_networks[network_type]) > 0

    async def load_and_setup_default_networks(
            self,
            dialog_manager: DialogManager,
            organization_id: int
    ) -> dict[str, bool]:
        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

        if not selected_networks:
            self.logger.info("Загрузка соцсетей по умолчанию")
            social_networks = await self.loom_content_client.get_social_networks_by_organization(
                organization_id=organization_id
            )

            telegram_connected = self.is_network_connected(social_networks, "telegram")
            vkontakte_connected = self.is_network_connected(social_networks, "vkontakte")

            if vkontakte_connected:
                widget_id = "vkontakte_checkbox"
                autoselect = social_networks["vkontakte"][0].get("autoselect", False)
                selected_networks[widget_id] = autoselect

            if telegram_connected:
                widget_id = "telegram_checkbox"
                autoselect = social_networks["telegram"][0].get("autoselect", False)
                selected_networks[widget_id] = autoselect

            dialog_manager.dialog_data["selected_social_networks"] = selected_networks

        return selected_networks

    async def get_social_network_data(
            self,
            dialog_manager: DialogManager,
            organization_id: int
    ) -> dict:
        social_networks = await self.loom_content_client.get_social_networks_by_organization(
            organization_id=organization_id
        )

        telegram_connected = self.is_network_connected(social_networks, "telegram")
        vkontakte_connected = self.is_network_connected(social_networks, "vkontakte")

        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

        if vkontakte_connected:
            self.logger.info("Установка состояния чекбокса VK")
            widget_id = "vkontakte_checkbox"
            vkontakte_checkbox: ManagedCheckbox = dialog_manager.find(widget_id)
            await vkontakte_checkbox.set_checked(selected_networks.get(widget_id, False))

        if telegram_connected:
            self.logger.info("Установка состояния чекбокса Telegram")
            widget_id = "telegram_checkbox"
            telegram_checkbox: ManagedCheckbox = dialog_manager.find(widget_id)
            await telegram_checkbox.set_checked(selected_networks.get(widget_id, False))

        return {
            "telegram_connected": telegram_connected,
            "vkontakte_connected": vkontakte_connected,
            "no_connected_networks": not telegram_connected and not vkontakte_connected,
            "has_available_networks": telegram_connected or vkontakte_connected,
        }

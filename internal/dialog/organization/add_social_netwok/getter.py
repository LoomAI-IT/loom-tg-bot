from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class AddSocialNetworkGetter(interface.IAddSocialNetworkGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_content_client = loom_content_client

    @auto_log()
    @traced_method()
    async def get_select_network_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self._get_state(dialog_manager)

        social_networks = await self.loom_content_client.get_social_networks_by_organization(
            organization_id=state.organization_id
        )

        # Determine status for each network
        telegram_status = self._get_network_status(social_networks, "telegram")
        vkontakte_status = self._get_network_status(social_networks, "vkontakte")
        youtube_status = self._get_network_status(social_networks, "youtube")
        instagram_status = self._get_network_status(social_networks, "instagram")

        data = {
            "telegram_status": telegram_status,
            "vkontakte_status": vkontakte_status,
            "youtube_status": youtube_status,
            "instagram_status": instagram_status,
        }

        return data

    @auto_log()
    @traced_method()
    async def get_telegram_main_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:

        state = await self._get_state(dialog_manager)
        social_networks = await self.loom_content_client.get_social_networks_by_organization(
            organization_id=state.organization_id
        )

        telegram_connected = self._is_network_connected(social_networks, "telegram")
        telegram_data = social_networks.get("telegram", [{}])[0] if telegram_connected else {}

        data = {
            "telegram_connected": telegram_connected,
            "telegram_not_connected": not telegram_connected,
            "telegram_channel_username": telegram_data.get("tg_channel_username", ""),
            "telegram_autoselect": telegram_data.get("autoselect", False),
        }

        return data

    @auto_log()
    @traced_method()
    async def get_telegram_connect_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "telegram_channel_username": dialog_manager.dialog_data.get("telegram_channel_username", ""),
            "has_telegram_channel_username": dialog_manager.dialog_data.get("has_telegram_channel_username", False),
            "has_void_telegram_channel_username": dialog_manager.dialog_data.get(
                "has_void_telegram_channel_username",
                False
            ),
            "has_invalid_telegram_channel_username": dialog_manager.dialog_data.get(
                "has_invalid_telegram_channel_username",
                False
            ),
            "has_invalid_telegram_permission": dialog_manager.dialog_data.get("has_invalid_telegram_permission", False),
        }

    @auto_log()
    @traced_method()
    async def get_telegram_edit_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self._get_state(dialog_manager)

        social_networks = await self.loom_content_client.get_social_networks_by_organization(
            organization_id=state.organization_id
        )

        telegram_data = social_networks["telegram"][0]
        original_autoselect = telegram_data["autoselect"]
        original_username = telegram_data["tg_channel_username"]

        # Инициализация состояний при первом входе
        autoselect_checkbox = dialog_manager.find("telegram_autoselect_checkbox")
        if "original_state" not in dialog_manager.dialog_data:
            self.logger.info("Инициализация состояний редактирования")
            dialog_manager.dialog_data["original_state"] = {
                "telegram_channel_username": original_username,
                "autoselect": original_autoselect,
            }

            dialog_manager.dialog_data["working_state"] = {
                "telegram_channel_username": original_username,
                "autoselect": original_autoselect,
            }

            await autoselect_checkbox.set_checked(original_autoselect)

        working_state = dialog_manager.dialog_data["working_state"]
        working_state["autoselect"] = autoselect_checkbox.is_checked()
        dialog_manager.dialog_data["working_state"] = working_state

        data = {
            "telegram_channel_username": working_state["telegram_channel_username"],
            "has_telegram_autoselect": working_state["autoselect"],
            "has_changes": self._has_changes(dialog_manager),
            "has_new_telegram_channel_username": (
                    working_state["telegram_channel_username"] !=
                    dialog_manager.dialog_data["original_state"]["telegram_channel_username"]
            ),
        }

        return data

    @auto_log()
    @traced_method()
    async def get_telegram_change_username_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self._get_state(dialog_manager)

        social_networks = await self.loom_content_client.get_social_networks_by_organization(
            organization_id=state.organization_id
        )

        telegram_data = social_networks.get("telegram", [{}])[0]
        data = {
            "telegram_channel_username": telegram_data.get("tg_channel_username", ""),
            "has_void_telegram_channel_username": dialog_manager.dialog_data.get(
                "has_void_telegram_channel_username",
                False
            ),
            "has_invalid_telegram_channel_username": dialog_manager.dialog_data.get(
                "has_invalid_telegram_channel_username",
                False
            ),
            "has_invalid_telegram_permission": dialog_manager.dialog_data.get(
                "has_invalid_telegram_permission",
                False
            ),
        }
        return data

    @auto_log()
    @traced_method()
    async def get_vkontakte_setup_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {}

    @auto_log()
    @traced_method()
    async def get_youtube_setup_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {}

    @auto_log()
    @traced_method()
    async def get_instagram_setup_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {}

    def _has_changes(self, dialog_manager: DialogManager) -> bool:
        original = dialog_manager.dialog_data.get("original_state", {})
        working = dialog_manager.dialog_data.get("working_state", {})

        if not original or not working:
            return False

        for field in ["telegram_channel_username", "autoselect"]:
            if original.get(field) != working.get(field):
                return True

        return False

    def _get_network_status(self, social_networks: dict, network_type: str) -> str:
        if not self._is_network_connected(social_networks, network_type):
            return "not_connected"

        network_data = social_networks[network_type][0]
        autoselect = network_data.get("autoselect", False)

        return "connected_autoselect" if autoselect else "connected_no_autoselect"

    def _is_network_connected(self, social_networks: dict, network_type: str) -> bool:
        if not social_networks:
            return False
        return network_type in social_networks and len(social_networks[network_type]) > 0

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]

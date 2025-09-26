from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class AddSocialNetworkGetter(interface.IAddSocialNetworkGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_content_client: interface.IKonturContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_content_client = kontur_content_client

    async def get_select_network_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkGetter.get_select_network_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Get social networks data from API
                social_networks = await self.kontur_content_client.get_social_networks_by_organization(
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

                self.logger.info("Social networks status loaded")
                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_telegram_main_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkGetter.get_telegram_main_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Get social networks data
                social_networks = await self.kontur_content_client.get_social_networks_by_organization(
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

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_telegram_connect_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "telegram_channel_username": dialog_manager.dialog_data.get("telegram_channel_username", ""),
            "has_telegram_channel_username": dialog_manager.dialog_data.get("has_telegram_channel_username", False),

            # Error flags
            "has_void_telegram_channel_username": dialog_manager.dialog_data.get("has_void_telegram_channel_username",
                                                                                 False),
            "has_invalid_telegram_channel_username": dialog_manager.dialog_data.get(
                "has_invalid_telegram_channel_username", False),
            "has_telegram_channel_not_found": dialog_manager.dialog_data.get("has_telegram_channel_not_found", False),
        }

    async def get_telegram_edit_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkGetter.get_telegram_edit_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                social_networks = await self.kontur_content_client.get_social_networks_by_organization(
                    organization_id=state.organization_id
                )

                autoselect = social_networks["telegram"][0]["autoselect"]
                telegram_channel_username = social_networks["telegram"][0]["tg_channel_username"]

                dialog_manager.dialog_data["original_state"] = {
                    "telegram_channel_username": telegram_channel_username,
                    "autoselect": autoselect,
                }

                if not dialog_manager.dialog_data.get("working_state"):
                    autoselect_checkbox: ManagedCheckbox = dialog_manager.find("telegram_autoselect_checkbox")
                    if autoselect_checkbox:
                        await autoselect_checkbox.set_checked(autoselect)

                    dialog_manager.dialog_data["working_state"] = dialog_manager.dialog_data["original_state"]
                else:
                    autoselect = dialog_manager.dialog_data["working_state"]["autoselect"]
                    telegram_channel_username = dialog_manager.dialog_data["working_state"]["telegram_channel_username"]

                data = {
                    "telegram_channel_username": telegram_channel_username,
                    "has_telegram_autoselect": autoselect,
                    "has_changes": self._has_changes(dialog_manager),
                    "has_new_telegram_channel_username": self._has_changes(dialog_manager),
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_telegram_change_username_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkGetter.get_telegram_change_username_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Get current telegram data
                social_networks = await self.kontur_content_client.get_social_networks_by_organization(
                    organization_id=state.organization_id
                )

                telegram_data = social_networks.get("telegram", [{}])[0]
                data = {
                    "telegram_channel_username": telegram_data.get("tg_channel_username", ""),
                    "has_void_telegram_channel_username": dialog_manager.dialog_data.get(
                        "has_void_telegram_channel_username",
                        False),
                    "has_invalid_telegram_channel_username": dialog_manager.dialog_data.get(
                        "has_invalid_telegram_channel_username",
                        False),
                    "has_telegram_channel_not_found": dialog_manager.dialog_data.get("has_telegram_channel_not_found",
                                                                                     False),
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_vkontakte_setup_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        # Static data for development placeholder
        return {}

    async def get_youtube_setup_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        # Static data for development placeholder
        return {}

    async def get_instagram_setup_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        # Static data for development placeholder
        return {}

    def _has_changes(self, dialog_manager: DialogManager) -> bool:
        original = dialog_manager.dialog_data.get("original_state", {})
        working = dialog_manager.dialog_data.get("working_state", {})

        if not original or not working:
            return False

        # Сравниваем текстовые поля
        fields_to_compare = ["telegram_channel_username", "autoselect"]
        for field in fields_to_compare:
            if original.get(field) != working.get(field):
                return True

        return False

    # Helper methods
    def _get_network_status(self, social_networks: dict, network_type: str) -> str:
        """
        Returns status string for Case widget selector:
        - 'connected_autoselect': network is connected and has autoselect enabled
        - 'connected_no_autoselect': network is connected but autoselect is disabled
        - 'not_connected': network is not connected
        """
        if not self._is_network_connected(social_networks, network_type):
            return "not_connected"

        network_data = social_networks[network_type][0]
        autoselect = network_data.get("autoselect", False)

        return "connected_autoselect" if autoselect else "connected_no_autoselect"

    def _is_network_connected(self, social_networks: dict, network_type: str) -> bool:
        """Check if a specific network type is connected"""
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

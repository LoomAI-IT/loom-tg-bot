import re
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class AddSocialNetworkService(interface.IAddSocialNetworkService):
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
    async def handle_telegram_channel_username_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            telegram_channel_username: str
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT
        await message.delete()

        error_flags = [
            "has_void_telegram_channel_username",
            "has_invalid_telegram_channel_username",
            "has_invalid_telegram_permission",
        ]
        for flag in error_flags:
            dialog_manager.dialog_data.pop(flag, None)

        telegram_channel_username = telegram_channel_username.strip()
        if not telegram_channel_username:
            self.logger.info("Username пустой")
            dialog_manager.dialog_data["has_void_telegram_channel_username"] = True
            return

        if telegram_channel_username.startswith("@"):
            telegram_channel_username = telegram_channel_username[1:]

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$", telegram_channel_username):
            self.logger.info("Username не соответствует формату")
            dialog_manager.dialog_data["has_invalid_telegram_channel_username"] = True
            return

        has_telegram_permission = await self.loom_content_client.check_telegram_channel_permission(
            telegram_channel_username
        )
        if not has_telegram_permission:
            self.logger.info("Нет прав доступа к каналу")
            dialog_manager.dialog_data["has_invalid_telegram_permission"] = True
            return

        # For now, we just save the username
        dialog_manager.dialog_data["telegram_channel_username"] = telegram_channel_username
        dialog_manager.dialog_data["has_telegram_channel_username"] = True

    @auto_log()
    @traced_method()
    async def handle_save_telegram_connection(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        telegram_channel_username = dialog_manager.dialog_data.get("telegram_channel_username", "")
        if not telegram_channel_username:
            self.logger.info("Username канала отсутствует")
            await callback.answer()
            return

        autoselect_checkbox: ManagedCheckbox = dialog_manager.find("autoselect_checkbox")
        autoselect = autoselect_checkbox.is_checked() if autoselect_checkbox else False

        state = await self._get_state(dialog_manager)

        await self.loom_content_client.create_telegram(
            organization_id=state.organization_id,
            telegram_channel_username=telegram_channel_username,
            autoselect=autoselect
        )

        await callback.answer(f"Telegram канал '@{telegram_channel_username}' подключен", show_alert=True)

        await dialog_manager.switch_to(model.AddSocialNetworkStates.telegram_main)

    @auto_log()
    @traced_method()
    async def handle_disconnect_telegram(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        state = await self._get_state(dialog_manager)

        await self.loom_content_client.delete_telegram(
            organization_id=state.organization_id
        )

        # Очищаем dialog_data после удаления
        dialog_manager.dialog_data.clear()

        await callback.answer("Telegram канал отключен", show_alert=True)
    @auto_log()
    @traced_method()
    async def handle_toggle_telegram_autoselect(
            self,
            callback: CallbackQuery,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None:
        new_value = checkbox.is_checked()

        if "working_state" not in dialog_manager.dialog_data:
            self.logger.info("Инициализация working_state")
            state = await self._get_state(dialog_manager)
            social_networks = await self.loom_content_client.get_social_networks_by_organization(
                organization_id=state.organization_id
            )
            telegram_data = social_networks["telegram"][0]

            dialog_manager.dialog_data["working_state"] = {
                "telegram_channel_username": telegram_data["tg_channel_username"],
                "autoselect": new_value,  # Используем новое значение
            }
        else:
            dialog_manager.dialog_data["working_state"]["autoselect"] = new_value

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_save_telegram_changes(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        # Берем данные из working_state, а не из чекбокса
        working_state = dialog_manager.dialog_data.get("working_state", {})
        autoselect = working_state.get("autoselect", None)
        new_telegram_channel_username = working_state.get("telegram_channel_username", None)

        state = await self._get_state(dialog_manager)

        await self.loom_content_client.update_telegram(
            organization_id=state.organization_id,
            autoselect=autoselect,
            telegram_channel_username=new_telegram_channel_username,
        )

        # Очищаем dialog_data после успешного сохранения
        dialog_manager.dialog_data.pop("original_state", None)
        dialog_manager.dialog_data.pop("working_state", None)

        await callback.answer("Настройки Telegram обновлены", show_alert=True)
        await dialog_manager.switch_to(model.AddSocialNetworkStates.telegram_main)

    @auto_log()
    @traced_method()
    async def handle_back_from_edit(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        # Очищаем временные данные при выходе без сохранения
        dialog_manager.dialog_data.pop("original_state", None)
        dialog_manager.dialog_data.pop("working_state", None)

        if await self._check_alerts(dialog_manager):
            self.logger.info("Переход к алертам")
            return

        await dialog_manager.switch_to(model.AddSocialNetworkStates.telegram_main, ShowMode.EDIT)

    @auto_log()
    @traced_method()
    async def handle_new_telegram_channel_username_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            new_telegram_channel_username: str
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await message.delete()

        error_flags = [
            "has_void_new_telegram_channel_username",
            "has_invalid_new_telegram_channel_username",
            "has_invalid_telegram_permission",
        ]
        for flag in error_flags:
            dialog_manager.dialog_data.pop(flag, None)

        # Validation
        new_telegram_channel_username = new_telegram_channel_username.strip()
        if not new_telegram_channel_username:
            self.logger.info("Новый username пустой")
            dialog_manager.dialog_data["has_void_new_telegram_channel_username"] = True
            return

        # Remove @ if present
        if new_telegram_channel_username.startswith("@"):
            new_telegram_channel_username = new_telegram_channel_username[1:]

        # Validate username format
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$", new_telegram_channel_username):
            self.logger.info("Новый username не соответствует формату")
            dialog_manager.dialog_data["has_invalid_new_telegram_channel_username"] = True
            return

        has_telegram_permission = await self.loom_content_client.check_telegram_channel_permission(
            new_telegram_channel_username
        )
        if not has_telegram_permission:
            self.logger.info("Нет прав доступа к новому каналу")
            dialog_manager.dialog_data["has_invalid_telegram_permission"] = True
            return

        dialog_manager.dialog_data["working_state"]["telegram_channel_username"] = new_telegram_channel_username
        await dialog_manager.switch_to(model.AddSocialNetworkStates.telegram_edit)

    @auto_log()
    @traced_method()
    async def handle_go_to_organization_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        if await self._check_alerts(dialog_manager):
            self.logger.info("Переход к алертам")
            return

        await dialog_manager.start(
            model.OrganizationMenuStates.organization_menu,
            mode=StartMode.RESET_STACK
        )

    async def _check_alerts(self, dialog_manager: DialogManager) -> bool:
        state = await self._get_state(dialog_manager)

        publication_approved_alerts = await self.state_repo.get_publication_approved_alert_by_state_id(
            state_id=state.id
        )
        if publication_approved_alerts:
            await dialog_manager.start(
                model.AlertsStates.publication_approved_alert,
                mode=StartMode.RESET_STACK
            )
            return True

        publication_rejected_alerts = await self.state_repo.get_publication_rejected_alert_by_state_id(
            state_id=state.id
        )
        if publication_rejected_alerts:
            await dialog_manager.start(
                model.AlertsStates.publication_rejected_alert,
                mode=StartMode.RESET_STACK
            )
            return True

        vizard_alerts = await self.state_repo.get_vizard_video_cut_alert_by_state_id(
            state_id=state.id
        )
        if vizard_alerts:
            await dialog_manager.start(
                model.AlertsStates.video_generated_alert,
                mode=StartMode.RESET_STACK
            )
            return True

        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=True
        )

        return False

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

import re
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class AddSocialNetworkService(interface.IAddSocialNetworkService):
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

    async def handle_go_to_connect_telegram(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkService.handle_go_to_connect_telegram",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                dialog_manager.dialog_data.pop("telegram_channel_username", None)
                dialog_manager.dialog_data.pop("has_telegram_channel_username", None)
                dialog_manager.dialog_data.pop("has_void_telegram_channel_username", None)
                dialog_manager.dialog_data.pop("has_invalid_telegram_channel_username", None)
                dialog_manager.dialog_data.pop("has_channel_not_found", None)

                await dialog_manager.switch_to(model.AddSocialNetworkStates.telegram_connect, ShowMode.EDIT)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_telegram_channel_username_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            telegram_channel_username: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkService.handle_telegram_channel_username_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT
                await message.delete()

                error_flags = [
                    "has_void_telegram_channel_username",
                    "has_invalid_telegram_channel_username",
                    "has_channel_not_found",
                ]
                for flag in error_flags:
                    dialog_manager.dialog_data.pop(flag, None)

                telegram_channel_username = telegram_channel_username.strip()
                if not telegram_channel_username:
                    dialog_manager.dialog_data["has_void_telegram_channel_username"] = True
                    return

                if telegram_channel_username.startswith("@"):
                    telegram_channel_username = telegram_channel_username[1:]

                if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$", telegram_channel_username):
                    dialog_manager.dialog_data["has_invalid_telegram_channel_username"] = True
                    return

                # TODO: Add channel verification here when bot integration is ready
                # For now, we just save the username
                dialog_manager.dialog_data["telegram_channel_username"] = telegram_channel_username
                dialog_manager.dialog_data["has_telegram_channel_username"] = True

                self.logger.info(f"telegram channel username entered: {telegram_channel_username}")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_save_telegram_connection(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkService.handle_save_telegram_connection",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                telegram_channel_username = dialog_manager.dialog_data.get("telegram_channel_username", "")
                if not telegram_channel_username:
                    await callback.answer("❌ Сначала введите username канала", show_alert=True)
                    return

                autoselect_checkbox: ManagedCheckbox = dialog_manager.find("autoselect_checkbox")
                autoselect = autoselect_checkbox.is_checked() if autoselect_checkbox else False

                state = await self._get_state(dialog_manager)

                await self.kontur_content_client.create_telegram(
                    organization_id=state.organization_id,
                    telegram_channel_username=telegram_channel_username,
                    autoselect=autoselect
                )

                await callback.answer("✅ telegram канал успешно подключен!", show_alert=True)
                self.logger.info(f"telegram channel connected: @{telegram_channel_username}, autoselect: {autoselect}")

                await dialog_manager.switch_to(model.AddSocialNetworkStates.telegram_main)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Не удалось подключить канал", show_alert=True)
                raise

    async def handle_disconnect_telegram(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkService.handle_disconnect_telegram",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Get current user state
                state = await self._get_state(dialog_manager)

                # Delete telegram connection
                await self.kontur_content_client.delete_telegram(
                    organization_id=state.organization_id
                )

                await callback.answer("✅ telegram канал отключен", show_alert=True)
                self.logger.info("telegram channel disconnected")

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка при отключении канала", show_alert=True)
                raise

    async def handle_toggle_telegram_autoselect(
            self,
            callback: CallbackQuery,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkService.handle_toggle_telegram_autoselect",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                is_checked = checkbox.is_checked()
                await checkbox.set_checked(not is_checked)

                dialog_manager.dialog_data["working_state"]["autoselect"] = is_checked
                await dialog_manager.show()

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_save_telegram_changes(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkService.handle_save_telegram_changes",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Get autoselect checkbox state
                autoselect_checkbox: ManagedCheckbox = dialog_manager.find("autoselect_checkbox")
                autoselect = autoselect_checkbox.is_checked() if autoselect_checkbox else False
                new_telegram_channel_username = dialog_manager.dialog_data.get("new_telegram_channel_username", None)

                # Get current user state
                state = await self._get_state(dialog_manager)

                # Update telegram settings (only autoselect for now)
                await self.kontur_content_client.update_telegram(
                    organization_id=state.organization_id,
                    autoselect=autoselect,
                    telegram_channel_username=new_telegram_channel_username,
                )

                await callback.answer("✅ Настройки сохранены!", show_alert=True)
                self.logger.info(f"telegram settings updated: autoselect={autoselect}")

                await dialog_manager.switch_to(model.AddSocialNetworkStates.telegram_main)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка при сохранении", show_alert=True)
                raise

    async def handle_new_telegram_channel_username_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            new_telegram_channel_username: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkService.handle_new_telegram_channel_username_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                error_flags = [
                    "has_void_new_telegram_channel_username",
                    "has_invalid_new_telegram_channel_username",
                ]
                for flag in error_flags:
                    dialog_manager.dialog_data.pop(flag, None)

                # Validation
                new_telegram_channel_username = new_telegram_channel_username.strip()
                if not new_telegram_channel_username:
                    dialog_manager.dialog_data["has_void_new_telegram_channel_username"] = True
                    return

                # Remove @ if present
                if new_telegram_channel_username.startswith("@"):
                    new_telegram_channel_username = new_telegram_channel_username[1:]

                # Validate username format
                if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$", new_telegram_channel_username):
                    dialog_manager.dialog_data["has_invalid_new_telegram_channel_username"] = True
                    return

                dialog_manager.dialog_data["working_state"]["telegram_channel_username"] = new_telegram_channel_username
                dialog_manager.dialog_data["has_new_telegram_channel_username"] = new_telegram_channel_username
                await dialog_manager.switch_to(model.AddSocialNetworkStates.telegram_edit)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                raise

    async def handle_go_to_organization_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddSocialNetworkService.handle_go_to_organization_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                if await self._check_alerts(dialog_manager):
                    return

                await dialog_manager.start(
                    model.OrganizationMenuStates.organization_menu,
                    mode=StartMode.RESET_STACK
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка при переходе в меню", show_alert=True)
                raise

    async def _check_alerts(self, dialog_manager: DialogManager) -> bool:
        state = await self._get_state(dialog_manager)
        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=True
        )

        vizard_alerts = await self.state_repo.get_vizard_video_cut_alert_by_state_id(
            state_id=state.id
        )
        if vizard_alerts:
            await dialog_manager.start(
                model.GenerateVideoCutStates.video_generated_alert,
                mode=StartMode.RESET_STACK
            )
            return True

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

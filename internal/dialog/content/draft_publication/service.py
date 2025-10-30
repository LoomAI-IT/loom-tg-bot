from typing import Any

from aiogram_dialog.widgets.input import MessageInput

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method

from internal.dialog.helpers import StateManager, AlertsManager, MessageExtractor, BalanceManager

from internal.dialog.content.draft_publication.helpers import (
    ValidationService, TextProcessor, ImageManager, PublicationManager, StateRestorer,
    NavigationManager, DialogDataHelper
)


class DraftPublicationService(interface.IDraftPublicationService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            loom_content_client: interface.ILoomContentClient,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_domain: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.loom_content_client = loom_content_client
        self.loom_organization_client = loom_organization_client
        self.loom_domain = loom_domain

        # Инициализация приватных сервисов
        self.state_manager = StateManager(
            state_repo=self.state_repo
        )
        self.validation = ValidationService(
            logger=self.logger
        )
        self.text_processor = TextProcessor(
            logger=self.logger
        )
        self.message_extractor = MessageExtractor(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client
        )
        self.alerts_manager = AlertsManager(
            self.state_repo
        )
        self.balance_manager = BalanceManager(
            loom_organization_client=self.loom_organization_client
        )
        self.image_manager = ImageManager(
            logger=self.logger,
            bot=self.bot,
            loom_domain=self.loom_domain,
            loom_content_client=self.loom_content_client,
        )
        self.state_restorer = StateRestorer(
            logger=self.logger,
            image_manager=self.image_manager
        )
        self.publication_manager = PublicationManager(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client,
            state_restorer=self.state_restorer,
            image_manager=self.image_manager,

        )
        self.navigation_manager = NavigationManager(
            logger=self.logger
        )
        self.dialog_data_helper = DialogDataHelper()

    @auto_log()
    @traced_method()
    async def handle_navigate_publication(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        direction = "prev" if button.widget_id == "prev_publication" else "next"

        _, at_edge = self.navigation_manager.navigate_publications(dialog_manager, direction)

        if at_edge:
            await callback.answer("Это крайняя публикация в списке")
            return

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_regenerate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)

        state = await self.state_manager.get_state(dialog_manager)

        if await self.balance_manager.check_balance_for_operation(state.organization_id, "generate_text"):
            await callback.answer("💰 Недостаточно средств. Пополните баланс организации", show_alert=True)
            return

        await callback.answer()
        self.dialog_data_helper.set_regenerating_text_flag(dialog_manager, True)
        await dialog_manager.show()

        async with tg_action(self.bot, callback.message.chat.id):
            regenerated_data = await self.publication_manager.generate_text(
                dialog_manager=dialog_manager
            )
            self.dialog_data_helper.update_working_text(dialog_manager, regenerated_data["text"])

        if await self.text_processor.check_text_length_with_image(dialog_manager):
            return

        self.dialog_data_helper.set_regenerating_text_flag(dialog_manager, False)

        await dialog_manager.switch_to(state=model.DraftPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_regenerate_text_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)
        self.dialog_data_helper.clear_regenerate_text_prompt_error_flags(dialog_manager=dialog_manager)
        await message.delete()

        state = await self.state_manager.get_state(dialog_manager)

        if await self.balance_manager.check_balance_for_operation(state.organization_id, "generate_text"):
            self.dialog_data_helper.set_has_insufficient_balance(dialog_manager, True)
            return

        if not self.validation.validate_content_type(
                message,
                dialog_manager
        ):
            return

        regenerate_text_prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id,
            return_html=True
        )

        if not self.validation.validate_regenerate_prompt(prompt=regenerate_text_prompt, dialog_manager=dialog_manager):
            return

        self.dialog_data_helper.set_regenerate_text_prompt(dialog_manager, regenerate_text_prompt)
        self.dialog_data_helper.set_regenerating_text_flag(dialog_manager, True)
        await dialog_manager.show()

        async with tg_action(self.bot, message.chat.id):
            regenerated_data = await self.publication_manager.regenerate_text(
                dialog_manager=dialog_manager,
                prompt=regenerate_text_prompt
            )
            self.dialog_data_helper.update_working_text(dialog_manager, regenerated_data["text"])

        self.dialog_data_helper.set_regenerating_text_flag(dialog_manager, False)
        self.dialog_data_helper.clear_regenerate_text_prompt(dialog_manager)

        if await self.text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.DraftPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_edit_publication_text(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)
        self.dialog_data_helper.clear_publication_text_edit_error_flags(dialog_manager=dialog_manager)
        await message.delete()

        new_text = self.text_processor.format_html_text(message.html_text)

        if not self.validation.validate_publication_text(text=new_text, dialog_manager=dialog_manager):
            return

        self.state_restorer.save_state_before_modification(dialog_manager, include_image=False)
        self.dialog_data_helper.update_working_text(dialog_manager, new_text)

        if await self.text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.DraftPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_generate_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)
        await callback.answer()

        self.dialog_data_helper.set_is_generating_image(dialog_manager, True)
        await dialog_manager.show()

        async with tg_action(self.bot, callback.message.chat.id, "upload_photo"):
            images_url = await self.publication_manager.generate_image(
                dialog_manager=dialog_manager
            )
            self.dialog_data_helper.set_generated_images_url(dialog_manager, images_url)

        self.dialog_data_helper.set_is_generating_image(dialog_manager, False)
        await dialog_manager.switch_to(state=model.DraftPublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_edit_image_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)
        self.dialog_data_helper.clear_edit_image_prompt_error_flags(dialog_manager=dialog_manager)
        await message.delete()

        state = await self.state_manager.get_state(dialog_manager)

        if await self.balance_manager.check_balance_for_operation(state.organization_id, "edit_image"):
            self.dialog_data_helper.set_has_insufficient_balance(dialog_manager, True)
            return

        if not self.validation.validate_content_type(message, dialog_manager):
            return

        edit_image_prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id,
        )

        if not self.validation.validate_edit_image_prompt(prompt=edit_image_prompt, dialog_manager=dialog_manager):
            return

        self.dialog_data_helper.set_edit_image_prompt(dialog_manager, edit_image_prompt)
        self.dialog_data_helper.set_is_generating_image(dialog_manager, True)
        await dialog_manager.show()

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            images_url = await self.publication_manager.edit_image(
                dialog_manager=dialog_manager,
                organization_id=state.organization_id,
                edit_image_prompt=edit_image_prompt
            )
            self.dialog_data_helper.set_generated_images_url(dialog_manager, images_url)

        self.dialog_data_helper.set_is_generating_image(dialog_manager, False)
        await dialog_manager.switch_to(state=model.DraftPublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)
        await message.delete()

        self.dialog_data_helper.clear_image_upload_error_flags(dialog_manager=dialog_manager)

        if not self.validation.validate_content_type(
                message,
                dialog_manager,
                [ContentType.PHOTO],
        ):
            self.dialog_data_helper.set_validation_flag(dialog_manager, "has_invalid_image_type")
            return

        photo = message.photo[-1]

        if not self.validation.validate_image_size(photo, dialog_manager):
            return

        self.state_restorer.save_state_before_modification(dialog_manager, include_image=True)
        self.image_manager.update_custom_image(dialog_manager, photo.file_id)

        if await self.text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.DraftPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_remove_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)
        self.image_manager.clear_image_data(dialog_manager=dialog_manager)

        await callback.answer("Изображение удалено", show_alert=True)
        await dialog_manager.switch_to(state=model.DraftPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_save_edits(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        if not self.publication_manager.has_changes(dialog_manager):
            self.logger.info("Нет изменений для сохранения")
            await callback.answer("Нет изменений для сохранения")
            return

        await self.publication_manager.save_publication_changes(dialog_manager)
        self.dialog_data_helper.update_original_from_working(dialog_manager)
        self.dialog_data_helper.clear_working_publication(dialog_manager)

        await callback.answer("Изменения сохранены", show_alert=True)
        await dialog_manager.switch_to(state=model.DraftPublicationStates.draft_list)

    @auto_log()
    @traced_method()
    async def handle_back_to_draft_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.clear_working_publication(dialog_manager)
        await dialog_manager.switch_to(state=model.DraftPublicationStates.draft_list)

    @auto_log()
    @traced_method()
    async def handle_back_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager)

        if await self.alerts_manager.check_alerts(dialog_manager=dialog_manager, state=state):
            self.logger.info("Обнаружены алерты")
            return

        await dialog_manager.start(
            state=model.ContentMenuStates.content_menu,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_toggle_social_network(
            self,
            callback: CallbackQuery,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        network_id = checkbox.widget_id
        is_checked = checkbox.is_checked()

        self.dialog_data_helper.toggle_social_network_selection(dialog_manager, network_id, is_checked)

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_prev_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        self.image_manager.navigate_images(
            dialog_manager=dialog_manager,
            direction="prev"
        )
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_next_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        self.image_manager.navigate_images(
            dialog_manager=dialog_manager,
            direction="next"
        )
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_send_to_moderation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await self.publication_manager.send_to_moderation(
            dialog_manager=dialog_manager,
        )

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)
        if await self.alerts_manager.check_alerts(dialog_manager=dialog_manager, state=state):
            return

        await callback.answer("Публикация отправлена на модерацию", show_alert=True)

        await dialog_manager.start(
            state=model.ContentMenuStates.content_menu,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_remove_photo_from_long_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        self.image_manager.clear_image_data(dialog_manager=dialog_manager)

        await callback.answer("Изображение удалено", show_alert=True)
        await dialog_manager.switch_to(state=model.DraftPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_compress_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager)

        if await self.balance_manager.check_balance_for_operation(state.organization_id, "generate_text"):
            await callback.answer("💰 Недостаточно средств. Пополните баланс организации", show_alert=True)
            return

        await callback.answer()
        await callback.message.edit_text(
            "Сжимаю текст, это может занять время... Не совершайте никаких действий",
            reply_markup=None
        )

        async with tg_action(self.bot, callback.message.chat.id):
            compressed_data = await self.publication_manager.compress_text(
                dialog_manager=dialog_manager
            )

        self.dialog_data_helper.update_working_text(dialog_manager, compressed_data["text"])

        await dialog_manager.switch_to(state=model.DraftPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_restore_previous_state(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        self.state_restorer.restore_previous_state(dialog_manager)

        await callback.answer("Изменения отменены", show_alert=True)
        await dialog_manager.switch_to(state=model.DraftPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_combine_images_start(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)

        await callback.answer()

        if self.dialog_data_helper.get_working_image_has_image(dialog_manager):
            await dialog_manager.switch_to(state=model.DraftPublicationStates.combine_images_choice)
        else:
            self.image_manager.init_combine_from_scratch(dialog_manager=dialog_manager)
            await dialog_manager.switch_to(state=model.DraftPublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_with_current_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()

        combine_images_list = await self.image_manager.prepare_current_image_for_combine(
            dialog_manager=dialog_manager,
            chat_id=callback.message.chat.id
        )

        self.dialog_data_helper.set_combine_images_list(dialog_manager, combine_images_list, 0)

        await dialog_manager.switch_to(state=model.DraftPublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_image_from_scratch(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()

        self.image_manager.init_combine_from_scratch(dialog_manager=dialog_manager)

        await dialog_manager.switch_to(state=model.DraftPublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.clear_combine_image_upload_error_flags(dialog_manager=dialog_manager)
        await message.delete()

        if not self.validation.validate_content_type(
                message,
                dialog_manager,
                [ContentType.PHOTO],
        ):
            return

        combine_images_list = self.dialog_data_helper.get_combine_images_list(dialog_manager)

        if len(combine_images_list) >= 3:
            self.dialog_data_helper.set_validation_flag(dialog_manager, "combine_images_limit_reached")
            return

        photo = message.photo[-1]

        if not self.validation.validate_image_size(photo, dialog_manager):
            return

        self.image_manager.upload_combine_image(photo=photo, dialog_manager=dialog_manager)

    @auto_log()
    @traced_method()
    async def handle_prev_combine_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.image_manager.navigate_combine_images(
            dialog_manager=dialog_manager,
            direction="prev"
        )
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_next_combine_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.image_manager.navigate_combine_images(
            dialog_manager=dialog_manager,
            direction="next"
        )
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_back_from_combine_image_upload(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()

        if self.image_manager.should_return_to_new_image_confirm(dialog_manager=dialog_manager):
            self.image_manager.cleanup_combine_data(dialog_manager=dialog_manager)
            await dialog_manager.switch_to(state=model.DraftPublicationStates.new_image_confirm)
        else:
            await dialog_manager.switch_to(state=model.DraftPublicationStates.edit_image_menu)

    @auto_log()
    @traced_method()
    async def handle_delete_combine_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.image_manager.delete_combine_image(dialog_manager=dialog_manager)
        await callback.answer("Изображение удалено")

    @auto_log()
    @traced_method()
    async def handle_combine_image_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)
        self.dialog_data_helper.clear_combine_image_prompt_error_flags(dialog_manager=dialog_manager)
        await message.delete()

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if await self.balance_manager.check_balance_for_operation(state.organization_id, "generate_image"):
            self.dialog_data_helper.set_has_insufficient_balance(dialog_manager, True)
            return

        if not self.validation.validate_content_type(message, dialog_manager):
            return

        combine_image_prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self.validation.validate_combine_image_prompt(combine_image_prompt, dialog_manager):
            return

        self.dialog_data_helper.set_combine_image_prompt(dialog_manager, combine_image_prompt)
        self.dialog_data_helper.set_is_combining_images(dialog_manager, True)
        await dialog_manager.show()

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            combined_image_result_url = await self.publication_manager.combine_images(
                dialog_manager=dialog_manager,
                prompt=combine_image_prompt or "Объедини эти фотографии в одну композицию",
                organization_id=state.organization_id,
            )

        self.dialog_data_helper.set_is_combining_images(dialog_manager, False)
        self.dialog_data_helper.set_combined_image_result_url(dialog_manager, combined_image_result_url)

        await dialog_manager.switch_to(state=model.DraftPublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_skip_combine_image_prompt(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if await self.balance_manager.check_balance_for_operation(state.organization_id, "generate_image"):
            await callback.answer("💰 Недостаточно средств. Пополните баланс организации", show_alert=True)
            return

        await callback.answer()
        await callback.message.edit_text(
            "Объединяю изображения, это может занять время... Не совершайте никаких действий",
            reply_markup=None
        )

        async with tg_action(self.bot, callback.message.chat.id, "upload_photo"):
            combined_image_result_url = await self.publication_manager.combine_images(
                dialog_manager=dialog_manager,
                prompt="Объедини эти фотографии в одну композицию",
                organization_id=state.organization_id,
            )

        self.dialog_data_helper.set_combined_image_result_url(dialog_manager, combined_image_result_url)

        await dialog_manager.switch_to(state=model.DraftPublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_combine_image_from_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        combine_images_list = await self.image_manager.prepare_combine_image_from_new_image(
            dialog_manager=dialog_manager,
            chat_id=callback.message.chat.id
        )

        if not combine_images_list:
            await callback.answer("Ошибка при подготовке изображения", show_alert=True)
            return

        self.dialog_data_helper.set_combine_images_list(dialog_manager, combine_images_list, 0)
        await callback.answer()

        await dialog_manager.switch_to(state=model.DraftPublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_edit_image_prompt_input_from_confirm_new_image(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.clear_new_image_confirm_error_flags(dialog_manager=dialog_manager)
        await message.delete()

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)
        if await self.balance_manager.check_balance_for_operation(state.organization_id, "edit_image"):
            self.dialog_data_helper.set_has_insufficient_balance(dialog_manager, True)
            return

        if not self.validation.validate_content_type(message, dialog_manager):
            return

        edit_image_prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self.validation.validate_edit_image_prompt(edit_image_prompt, dialog_manager):
            return

        self.dialog_data_helper.set_edit_image_prompt(dialog_manager, edit_image_prompt)
        self.dialog_data_helper.set_is_applying_edits(dialog_manager, True)
        await dialog_manager.show()

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            images_url = await self.publication_manager.edit_new_image_with_prompt(
                dialog_manager=dialog_manager,
                organization_id=state.organization_id,
                prompt=edit_image_prompt,
            )

        self.image_manager.update_image_after_edit_from_confirm_new_image(
            dialog_manager=dialog_manager,
            images_url=images_url
        )
        self.dialog_data_helper.set_is_applying_edits(dialog_manager, False)
        self.dialog_data_helper.set_edit_image_prompt(dialog_manager, "")

    @auto_log()
    @traced_method()
    async def handle_confirm_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await callback.answer("Изображение применено")

        self.image_manager.confirm_new_image(dialog_manager=dialog_manager)

        if await self.text_processor.check_text_length_with_image(dialog_manager=dialog_manager):
            return

        await dialog_manager.switch_to(state=model.DraftPublicationStates.edit_image_menu)

    @auto_log()
    @traced_method()
    async def handle_show_old_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.image_manager.toggle_showing_old_image(dialog_manager=dialog_manager, show_old=True)
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_show_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.image_manager.toggle_showing_old_image(dialog_manager=dialog_manager, show_old=False)
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_reject_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await callback.answer("Изображение отклонено")

        self.image_manager.reject_new_image(dialog_manager=dialog_manager)

        await dialog_manager.switch_to(state=model.DraftPublicationStates.edit_image_menu)

    # ============= ОБРАБОТЧИКИ ДЛЯ ГЕНЕРАЦИИ С РЕФЕРЕНСАМИ =============

    @auto_log()
    @traced_method()
    async def handle_auto_generate_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager)

        if await self.balance_manager.check_balance_for_operation(state.organization_id, "generate_image"):
            await callback.answer("💰 Недостаточно средств. Пополните баланс организации", show_alert=True)
            return

        await callback.answer()
        await callback.message.edit_text(
            "Генерирую изображение, это может занять время... Не совершайте никаких действий",
            reply_markup=None
        )

        async with tg_action(self.bot, callback.message.chat.id, "upload_photo"):
            images_url = await self.publication_manager.generate_image(
                dialog_manager=dialog_manager
            )

        self.dialog_data_helper.set_generated_images_url(dialog_manager, images_url)

        await dialog_manager.switch_to(state=model.DraftPublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_reference_generation_image_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await message.delete()

        self.dialog_data_helper.clear_reference_generation_image_prompt_errors(dialog_manager)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if await self.balance_manager.check_balance_for_operation(state.organization_id, "generate_image"):
            self.dialog_data_helper.set_has_insufficient_balance(dialog_manager, True)
            return

        if not self.validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            return

        reference_generation_image_prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self.validation.validate_edit_image_prompt(
                prompt=reference_generation_image_prompt,
                dialog_manager=dialog_manager
        ):
            return

        self.dialog_data_helper.set_reference_generation_image_prompt(
            dialog_manager,
            reference_generation_image_prompt
        )
        self.dialog_data_helper.set_is_generating_image(dialog_manager, True)
        await dialog_manager.show()

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            images_url = await self.image_manager.generate_image_with_reference(
                dialog_manager=dialog_manager,
                prompt=reference_generation_image_prompt,
                organization_id=state.organization_id
            )

        self.dialog_data_helper.set_is_generating_image(dialog_manager, False)
        self.dialog_data_helper.set_generated_images_url(dialog_manager, images_url)
        self.dialog_data_helper.clear_reference_generation_image_data(dialog_manager)

        await dialog_manager.switch_to(state=model.DraftPublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_reference_generation_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await message.delete()

        self.dialog_data_helper.clear_reference_generation_image_errors(dialog_manager)

        if not self.validation.validate_content_type(
                message=message,
                dialog_manager=dialog_manager,
                allowed_types=[ContentType.PHOTO]
        ):
            self.dialog_data_helper.set_validation_flag(
                dialog_manager,
                "has_invalid_reference_generation_image_type"
            )
            return

        photo = message.photo[-1]
        if not self.validation.validate_image_size(photo, dialog_manager):
            self.dialog_data_helper.set_validation_flag(
                dialog_manager,
                "has_big_reference_generation_image_size"
            )
            return

        self.dialog_data_helper.set_reference_generation_image_file_id(dialog_manager, photo.file_id)

        await dialog_manager.switch_to(state=model.DraftPublicationStates.reference_image_generation)

    @auto_log()
    @traced_method()
    async def handle_use_current_image_as_reference(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        file_id = await self.image_manager.use_current_image_as_reference(
            dialog_manager=dialog_manager,
            chat_id=callback.message.chat.id
        )

        if file_id:
            self.dialog_data_helper.set_reference_generation_image_file_id(dialog_manager, file_id)
            await callback.answer("Текущее изображение установлено как референс")
            await dialog_manager.switch_to(state=model.DraftPublicationStates.reference_image_generation)
        else:
            await callback.answer("Ошибка при загрузке изображения", show_alert=True)

    @auto_log()
    @traced_method()
    async def handle_remove_reference_generation_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.remove_reference_generation_image(dialog_manager)
        await callback.answer("Изображение удалено")

    @auto_log()
    @traced_method()
    async def handle_back_from_custom_generation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        self.dialog_data_helper.clear_reference_generation_image_data(dialog_manager)

        await callback.answer()
        await dialog_manager.switch_to(state=model.DraftPublicationStates.image_generation_mode_select)

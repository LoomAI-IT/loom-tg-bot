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

from internal.dialog.helpers import StateManager, AlertsManager, MessageExtractor

from internal.dialog.content.moderation_publication.helpers import (
    ValidationService, TextProcessor, ImageManager, PublicationManager, StateRestorer,
    NavigationManager, DialogDataHelper
)


class ModerationPublicationService(interface.IModerationPublicationService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            loom_content_client: interface.ILoomContentClient,
            loom_domain: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.loom_content_client = loom_content_client
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
        self.image_manager = ImageManager(
            logger=self.logger,
            bot=self.bot,
            loom_domain=self.loom_domain
        )
        self.publication_manager = PublicationManager(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client
        )
        self.state_restorer = StateRestorer(
            logger=self.logger,
            image_manager=self.image_manager
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

        # Определяем направление навигации
        direction = "prev" if button.widget_id == "prev_publication" else "next"

        # Делегируем навигацию в NavigationManager
        _, at_edge = self.navigation_manager.navigate_publications(dialog_manager, direction)

        if at_edge:
            await callback.answer("Это крайняя публикация в списке")
            return

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_reject_comment_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            comment: str
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await message.delete()

        self.dialog_data_helper.clear_reject_commentdialog_data_helper(dialog_manager=dialog_manager)

        # Очищаем и валидируем комментарий
        comment = self.text_processor.strip_text(comment)

        if not self.validation.validate_reject_comment(comment=comment, dialog_manager=dialog_manager):
            return

        self.dialog_data_helper.set_reject_comment(dialog_manager, comment)

    @auto_log()
    @traced_method()
    async def handle_send_rejection(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager)
        _, publication_id, reject_comment = self.dialog_data_helper.get_reject_comment_data(dialog_manager)

        # API вызов отклонения публикации
        await self.publication_manager.reject_publication(
            publication_id=publication_id,
            moderator_id=state.account_id,
            comment=reject_comment
        )
        # TODO сделать вебхук для отклонения публикации

        self.publication_manager.remove_current_publication_from_list(dialog_manager)

        await callback.answer("Публикация отклонена", show_alert=True)
        await dialog_manager.switch_to(state=model.ModerationPublicationStates.moderation_list)

    @auto_log()
    @traced_method()
    async def handle_regenerate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()
        self.dialog_data_helper.set_regenerating_text_flag(dialog_manager, True)
        await dialog_manager.show()

        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)

        # Сохраняем предыдущее состояние
        self.state_restorer.save_state_before_modification(dialog_manager, include_image=False)

        # API вызов регенерации текста
        async with tg_action(self.bot, callback.message.chat.id):
            regenerated_data = await self.publication_manager.regenerate_text(
                category_id=working_pub["category_id"],
                text=working_pub["text"],
                prompt=None
            )

        # Обновляем текст
        self.dialog_data_helper.update_working_text(dialog_manager, regenerated_data["text"])
        self.dialog_data_helper.set_regenerating_text_flag(dialog_manager, False)

        # Проверяем длину текста с изображением
        if await self.text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_regenerate_text_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await message.delete()

        self.dialog_data_helper.clear_regenerate_promptdialog_data_helper(dialog_manager=dialog_manager)

        # Валидация типа контента
        if not self.validation.validate_message_content_type(
                message,
                [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT],
                dialog_manager
        ):
            return

        # Обработка текста или голоса
        state = await self.state_manager.get_state(dialog_manager)
        prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id,
            return_html=True
        )

        if not self.validation.validate_regenerate_prompt(prompt=prompt, dialog_manager=dialog_manager):
            return

        self.dialog_data_helper.set_regenerate_prompt(dialog_manager, prompt)
        self.dialog_data_helper.set_regenerating_text_flag(dialog_manager, True)
        await dialog_manager.show()

        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)

        # Сохраняем предыдущее состояние
        self.state_restorer.save_state_before_modification(dialog_manager, include_image=False)

        # API вызов регенерации текста с промптом
        async with tg_action(self.bot, message.chat.id):
            regenerated_data = await self.publication_manager.regenerate_text(
                category_id=working_pub["category_id"],
                text=working_pub["text"],
                prompt=prompt
            )

        self.dialog_data_helper.update_working_text(dialog_manager, regenerated_data["text"])
        self.dialog_data_helper.set_regenerating_text_flag(dialog_manager, False)
        self.dialog_data_helper.clear_regenerate_prompt(dialog_manager)

        # Проверяем длину текста с изображением
        if await self.text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_edit_text(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await message.delete()

        self.dialog_data_helper.clear_text_editdialog_data_helper(dialog_manager=dialog_manager)

        # Форматируем HTML текст
        new_text = self.text_processor.format_html_text(message.html_text)

        if not self.validation.validate_publication_text(text=new_text, dialog_manager=dialog_manager):
            return

        # Сохраняем предыдущее состояние
        self.state_restorer.save_state_before_modification(dialog_manager, include_image=False)

        # Обновляем текст
        self.dialog_data_helper.update_working_text(dialog_manager, new_text)

        # Проверяем длину текста с изображением
        if await self.text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_generate_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()
        self.dialog_data_helper.set_generating_image_flag(dialog_manager, True)
        await dialog_manager.show()

        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)

        # Подготавливаем текущее изображение для генерации
        current_image_content, current_image_filename = await self.image_manager.prepare_current_image_for_generation(
            dialog_manager
        )

        # Сохраняем предыдущее состояние
        self.state_restorer.save_state_before_modification(dialog_manager, include_image=True)

        # API вызов генерации изображения
        async with tg_action(self.bot, callback.message.chat.id, "upload_photo"):
            images_url = await self.publication_manager.generate_image(
                category_id=working_pub["category_id"],
                publication_text=working_pub["text"],
                image_content=current_image_content,
                image_filename=current_image_filename
            )

        # Обновляем рабочую версию с сгенерированными изображениями
        self.image_manager.update_generated_images(dialog_manager, images_url)
        self.dialog_data_helper.set_generating_image_flag(dialog_manager, False)

        # Проверяем длину текста с изображением
        if await self.text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_generate_image_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await message.delete()

        self.dialog_data_helper.clear_image_promptdialog_data_helper(dialog_manager=dialog_manager)

        # Валидация типа контента
        if not self.validation.validate_message_content_type(
                message,
                [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT],
                dialog_manager
        ):
            return

        # Обработка текста или голоса
        state = await self.state_manager.get_state(dialog_manager)
        prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id,
            return_html=True
        )

        if not self.validation.validate_image_prompt(prompt=prompt, dialog_manager=dialog_manager):
            return

        self.dialog_data_helper.set_image_prompt(dialog_manager, prompt)
        self.dialog_data_helper.set_generating_image_flag(dialog_manager, True)
        await dialog_manager.show()

        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)

        # Подготавливаем текущее изображение для генерации
        current_image_content, current_image_filename = await self.image_manager.prepare_current_image_for_generation(
            dialog_manager
        )

        # Сохраняем предыдущее состояние
        self.state_restorer.save_state_before_modification(dialog_manager, include_image=True)

        # API вызов генерации изображения с промптом
        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            images_url = await self.publication_manager.generate_image(
                category_id=working_pub["category_id"],
                publication_text=working_pub["text"],
                image_content=current_image_content,
                image_filename=current_image_filename,
                prompt=prompt
            )

        # Обновляем рабочую версию с сгенерированными изображениями
        self.image_manager.update_generated_images(dialog_manager, images_url)
        self.dialog_data_helper.set_generating_image_flag(dialog_manager, False)

        # Проверяем длину текста с изображением
        if await self.text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await message.delete()

        self.dialog_data_helper.clear_image_uploaddialog_data_helper(dialog_manager=dialog_manager)

        # Валидация типа контента
        if not self.validation.validate_message_content_type(
                message,
                [ContentType.PHOTO],
                dialog_manager
        ):
            dialog_manager.dialog_data["has_invalid_image_type"] = True
            return

        if message.photo:
            photo = message.photo[-1]

            # Валидация размера изображения
            if not self.validation.validate_image_size(photo, dialog_manager):
                return

            # Сохраняем предыдущее состояние
            self.state_restorer.save_state_before_modification(dialog_manager, include_image=True)

            # Обновляем рабочую версию с загруженным изображением
            self.image_manager.update_custom_image(dialog_manager, photo.file_id)
            self.logger.info("Изображение загружено")

            # Проверяем длину текста с изображением
            if await self.text_processor.check_text_length_with_image(dialog_manager):
                return

            await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)
        else:
            self.logger.info("Ошибка обработки изображения")
            dialog_manager.dialog_data["has_image_processing_error"] = True

    @auto_log()
    @traced_method()
    async def handle_remove_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        self.image_manager.clear_image_data(dialog_manager=dialog_manager)

        await callback.answer("Изображение удалено", show_alert=True)

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

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

        # Сохраняем изменения через API
        await self.publication_manager.save_publication_changes(dialog_manager)

        # Обновляем оригинальную версию из working
        self.dialog_data_helper.update_original_from_working(dialog_manager)

        # Очищаем working_publication
        self.dialog_data_helper.clear_working_publication(dialog_manager)

        await callback.answer("Изменения сохранены", show_alert=True)
        await dialog_manager.switch_to(state=model.ModerationPublicationStates.moderation_list)

    @auto_log()
    @traced_method()
    async def handle_back_to_moderation_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await dialog_manager.switch_to(state=model.ModerationPublicationStates.moderation_list)

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
        if "selected_social_networks" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["selected_social_networks"] = {}

        network_id = checkbox.widget_id
        is_checked = checkbox.is_checked()

        # Сохраняем состояние чекбокса
        dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_prev_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
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
        self.image_manager.navigate_images(
            dialog_manager=dialog_manager,
            direction="next"
        )
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_publish_now(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        if not self.validation.validate_selected_networks(dialog_manager):
            await callback.answer(
                "Выберите хотя бы одну социальную сеть",
                show_alert=True
            )
            return

        state = await self.state_manager.get_state(dialog_manager)
        post_links = await self.publication_manager.approve_and_publish(dialog_manager, state)

        dialog_manager.dialog_data["post_links"] = post_links

        self.publication_manager.remove_current_publication_from_list(dialog_manager)
        await callback.answer("Опубликовано!", show_alert=True)

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.publication_success)

    @auto_log()
    @traced_method()
    async def handle_remove_photo_from_long_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        # Удаляем изображение из рабочей версии
        self.image_manager.clear_image_data(dialog_manager=dialog_manager)

        self.logger.info("Изображение удалено из-за длинного текста")
        await callback.answer("Изображение удалено", show_alert=True)
        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_compress_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()
        await callback.message.edit_text(
            "Сжимаю текст, это может занять время... Не совершайте никаких действий",
            reply_markup=None
        )

        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)
        expected_length = self.dialog_data_helper.get_expected_length(dialog_manager)

        # API вызов сжатия текста
        async with tg_action(self.bot, callback.message.chat.id):
            compressed_data = await self.publication_manager.compress_text(
                category_id=working_pub["category_id"],
                text=working_pub["text"],
                expected_length=expected_length
            )

        # Обновляем текст
        self.dialog_data_helper.update_working_text(dialog_manager, compressed_data["text"])

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_restore_previous_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        self.state_restorer.restore_previous_state(dialog_manager)

        await callback.answer("Изменения отменены", show_alert=True)
        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

from typing import Any

from aiogram_dialog.widgets.input import MessageInput

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox, Button

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method

from internal.dialog.helpers import StateManager, AlertsManager, MessageExtractor

from internal.dialog.content.generate_publication.helpers import (
    ImageManager, TextProcessor, ValidationService,
    PublicationManager, CategoryManager, DialogDataHelper, SocialNetworkManager
)


class GeneratePublicationService(interface.IGeneratePublicationService):
    DEFAULT_combine_image_prompt = "Объедини эти фотографии в одну композицию, чтобы это смотрелось органично"

    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            llm_chat_repo: interface.ILLMChatRepo,
            loom_content_client: interface.ILoomContentClient,
            loom_employee_client: interface.ILoomEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.llm_chat_repo = llm_chat_repo
        self.loom_content_client = loom_content_client
        self.loom_employee_client = loom_employee_client

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
            loom_content_client=self.loom_content_client
        )
        self.dialog_data_helper = DialogDataHelper(
            logger=self.logger
        )
        self.publication_manager = PublicationManager(
            logger=self.logger,
            loom_content_client=self.loom_content_client,
            image_manager=self.image_manager,
        )
        self.social_network_manager = SocialNetworkManager(
            logger=self.logger,
            loom_content_client=self.loom_content_client,
        )
        self.category_manager = CategoryManager(
            logger=self.logger,
            loom_content_client=self.loom_content_client,
            loom_employee_client=self.loom_employee_client,
            llm_chat_repo=self.llm_chat_repo
        )

    # ============= PUBLIC HANDLERS: INPUT & CATEGORY =============

    @auto_log()
    @traced_method()
    async def handle_generate_text_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.clear_generate_text_prompt_input(dialog_manager=dialog_manager)
        await message.delete()

        if not self.validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            self.logger.info("Неверный тип контента")
            return

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)
        generate_text_prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self.validation.validate_generate_text_prompt(text=generate_text_prompt, dialog_manager=dialog_manager):
            self.logger.info("Неверный размер промпта для генерации текста")
            return

        self.dialog_data_helper.set_generate_text_prompt(dialog_manager, generate_text_prompt, True)

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.generation)

    @auto_log()
    @traced_method()
    async def handle_select_category(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            category_id: str
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await self.category_manager.select_category(
            dialog_manager=dialog_manager,
            category_id=int(category_id)
        )

        if self.category_manager.has_start_generate_text_prompt(dialog_manager):
            self.logger.info("Есть стартовый текст")

            self.category_manager.set_start_generate_text_prompt(dialog_manager)
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.generation)
        else:
            self.logger.info("Нет стартового текста")
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.generate_text_prompt_input)

    @auto_log()
    @traced_method()
    async def go_to_create_category(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if not await self.category_manager.navigate_to_create_category(
                dialog_manager=dialog_manager,
                state=state
        ):
            await callback.answer("У вас нет прав создавать рубрики", show_alert=True)
            return

        await callback.answer()

    # ============= PUBLIC HANDLERS: TEXT GENERATION =============

    @auto_log()
    @traced_method()
    async def handle_generate_publication_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, delete_and_send=True)

        await callback.answer()
        await callback.message.edit_text(
            "Генерирую текст, это может занять время... Не совершайте никаких действий",
            reply_markup=None
        )

        async with tg_action(self.bot, callback.message.chat.id):
            publication_text = await self.publication_manager.generate_publication_text(
                dialog_manager=dialog_manager,
            )

        self.dialog_data_helper.set_publication_text(dialog_manager, publication_text)

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_generate_publication_text_with_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, delete_and_send=True)

        await callback.answer()
        await callback.message.edit_text(
            "Генерирую текст с картинкой, это может занять минуты 3. Не совершайте никаких действий...",
            reply_markup=None
        )

        async with tg_action(self.bot, callback.message.chat.id):
            publication_text = await self.publication_manager.generate_publication_text(dialog_manager)
            self.dialog_data_helper.set_publication_text(dialog_manager, publication_text)

        async with tg_action(self.bot, callback.message.chat.id, "upload_photo"):
            images_url = await self.image_manager.generate_new_image(dialog_manager)
            self.dialog_data_helper.set_new_publication_image(dialog_manager, images_url, 0)

        if await self.text_processor.check_text_length_with_image(dialog_manager=dialog_manager):
            return

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

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
            images_key="publication_images_url",
            index_key="current_image_index",
            direction="next"
        )
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
            images_key="publication_images_url",
            index_key="current_image_index",
            direction="prev"
        )
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
        await callback.answer()

        self.dialog_data_helper.set_is_regenerating_text(dialog_manager, True)
        await dialog_manager.show()
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        async with tg_action(self.bot, callback.message.chat.id):
            publication_text = await self.publication_manager.generate_publication_text(dialog_manager)
            self.dialog_data_helper.set_publication_text(dialog_manager, publication_text)

        self.dialog_data_helper.set_is_regenerating_text(dialog_manager, False)

        if await self.text_processor.check_text_length_with_image(dialog_manager=dialog_manager):
            return

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_regenerate_text_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)
        self.dialog_data_helper.clear_regenerate_text_prompt(dialog_manager=dialog_manager)
        await message.delete()

        if not self.validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            return

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)
        regenerate_text_prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self.validation.validate_regenerate_text_prompt(
                text=regenerate_text_prompt,
                dialog_manager=dialog_manager,
        ):
            return

        self.dialog_data_helper.set_regenerate_text_prompt(dialog_manager, regenerate_text_prompt, True)
        self.dialog_data_helper.set_is_regenerating_text(dialog_manager, True)
        await dialog_manager.show()

        async with tg_action(self.bot, message.chat.id):
            new_publication_text = await self.publication_manager.regenerate_publication_text(
                dialog_manager=dialog_manager,
                regenerate_text_prompt=regenerate_text_prompt
            )

        self.dialog_data_helper.set_publication_text(dialog_manager, new_publication_text)
        self.dialog_data_helper.set_is_regenerating_text(dialog_manager, False)
        self.dialog_data_helper.set_regenerate_text_prompt(dialog_manager, "", False)

        if await self.text_processor.check_text_length_with_image(dialog_manager=dialog_manager):
            return

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_edit_publication_text(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.clear_text_edit(dialog_manager=dialog_manager)
        await message.delete()

        new_text = message.html_text.replace('\n', '<br/>')

        if not self.validation.validate_edited_text(text=new_text, dialog_manager=dialog_manager):
            return

        self.dialog_data_helper.set_publication_text(dialog_manager, new_text)
        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_edit_image_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)
        self.dialog_data_helper.clear_edit_image_prompt(dialog_manager=dialog_manager)
        await message.delete()

        if not self.validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            return

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)
        edit_image_prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self.validation.validate_edit_image_prompt(
                text=edit_image_prompt,
                dialog_manager=dialog_manager,
        ):
            return

        self.dialog_data_helper.set_edit_image_prompt(dialog_manager, edit_image_prompt)
        self.dialog_data_helper.set_is_generating_image(dialog_manager, True)
        await dialog_manager.show()

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            images_url = await self.image_manager.edit_image_with_prompt(
                dialog_manager=dialog_manager,
                organization_id=state.organization_id,
                prompt=edit_image_prompt,
            )

        self.dialog_data_helper.set_is_generating_image(dialog_manager, False)
        self.dialog_data_helper.set_generated_images_url(dialog_manager, images_url)

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.clear_image_upload(dialog_manager=dialog_manager)
        await message.delete()

        if not self.validation.validate_image_content_type(message=message, dialog_manager=dialog_manager):
            return

        photo = message.photo[-1]

        if not self.validation.validate_image_size(photo=photo, dialog_manager=dialog_manager):
            return

        self.dialog_data_helper.set_new_custom_image(dialog_manager=dialog_manager, file_id=photo.file_id)

        if await self.text_processor.check_text_length_with_image(dialog_manager=dialog_manager):
            return

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_remove_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        self.dialog_data_helper.clear_all_image_data(dialog_manager)

        await callback.answer("Изображение удалено", show_alert=True)
        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_add_to_drafts(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        await callback.answer("Черновики публикации в разработке", show_alert=True)
        return

    @auto_log()
    @traced_method()
    async def handle_send_to_moderation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        await self.publication_manager.send_to_moderation(
            dialog_manager=dialog_manager,
            state=state
        )

        await callback.answer("Публикация отправлена на модерацию", show_alert=True)

        if await self.alerts_manager.check_alerts(dialog_manager=dialog_manager, state=state):
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
        self.social_network_manager.toggle_social_network(checkbox=checkbox, dialog_manager=dialog_manager)
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_publish_now(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        selected_networks = self.dialog_data_helper.get_selected_social_networks(dialog_manager)

        if not self.validation.validate_selected_networks(selected_networks):
            self.logger.info("Не выбрана ни одна соцсеть")
            await callback.answer("Выберите хотя бы одну социальную сеть", show_alert=True)
            return

        await self.publication_manager.publish_now(
            dialog_manager=dialog_manager,
            state=state,
        )

        await callback.answer("Публикация успешно опубликована", show_alert=True)

        if await self.alerts_manager.check_alerts(dialog_manager=dialog_manager, state=state):
            self.logger.info("Переход к алертам")
            return

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.publication_success)

    @auto_log()
    @traced_method()
    async def handle_remove_photo_from_long_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.clear_all_image_data(dialog_manager=dialog_manager)
        await callback.answer("Изображение удалено", show_alert=True)
        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

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

        async with tg_action(self.bot, callback.message.chat.id):
            compressed_publication_text = await self.publication_manager.compress_publication_text(
                dialog_manager=dialog_manager
            )

        self.dialog_data_helper.set_publication_text(dialog_manager, compressed_publication_text)

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_go_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if await self.alerts_manager.check_alerts(dialog_manager=dialog_manager, state=state):
            self.logger.info("Обнаружены алерты")
            return

        await dialog_manager.start(
            state=model.ContentMenuStates.content_menu,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_combine_images_start(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await callback.answer()

        if self.dialog_data_helper.get_has_image(dialog_manager):
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_choice)
        else:
            self.dialog_data_helper.set_combine_images_list(dialog_manager, [], 0)
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_upload)

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

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_image_from_scratch(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.set_combine_images_list(dialog_manager, [], 0)
        await callback.answer()

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.clear_combine_image_upload(dialog_manager=dialog_manager)
        await message.delete()

        if not self.validation.validate_image_content_type(
                message=message,
                dialog_manager=dialog_manager,
                error_flag="has_invalid_combine_image_type"
        ):
            return

        combine_images_list = self.dialog_data_helper.get_combine_images_list(dialog_manager)

        if not self.validation.validate_combine_images_count(
                combine_images_list=combine_images_list,
                dialog_manager=dialog_manager,
                check_min=False,
                check_max=True
        ):
            return

        if message.photo:
            photo = message.photo[-1]

            if not self.validation.validate_image_size(
                    photo=photo,
                    dialog_manager=dialog_manager,
                    error_flag="has_big_combine_image_size"
            ):
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
        self.image_manager.navigate_images(
            dialog_manager=dialog_manager,
            images_key="combine_images_list",
            index_key="combine_current_index",
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
        self.image_manager.navigate_images(
            dialog_manager=dialog_manager,
            images_key="combine_images_list",
            index_key="combine_current_index",
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
        """
        Обработка нажатия кнопки "Назад" в окне загрузки изображений для объединения.
        Возвращает в new_image_confirm, если пришли оттуда, иначе в image_menu.
        """
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()

        if self.image_manager.should_return_to_new_image_confirm(dialog_manager=dialog_manager):
            self.dialog_data_helper.clear_combine_image_data(dialog_manager)
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.new_image_confirm)
        else:
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.image_menu)

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
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.clear_combine_image_prompt_error_flags(dialog_manager=dialog_manager)
        await message.delete()

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if not self.validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            return

        combine_image_prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self.validation.validate_combine_image_prompt(prompt=combine_image_prompt,
                                                             dialog_manager=dialog_manager):
            return

        combine_images_list = self.dialog_data_helper.get_combine_images_list(dialog_manager)

        if not self.validation.validate_combine_images_count(
                combine_images_list=combine_images_list,
                dialog_manager=dialog_manager,
                check_min=True,
                check_max=False
        ):
            return

        self.dialog_data_helper.set_combine_image_prompt(dialog_manager, combine_image_prompt)
        self.dialog_data_helper.set_is_combining_images(dialog_manager, True)
        await dialog_manager.show()

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            combined_result_url = await self.image_manager.process_combine_with_prompt(
                dialog_manager=dialog_manager,
                state=state,
                combine_images_list=combine_images_list,
                prompt=combine_image_prompt or self.DEFAULT_combine_image_prompt,
                chat_id=message.chat.id
            )

        self.dialog_data_helper.set_is_combining_images(dialog_manager, False)
        self.dialog_data_helper.set_combine_image_url(dialog_manager, combined_result_url)

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_skip_combine_image_prompt(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        combine_images_list = self.dialog_data_helper.get_combine_images_list(dialog_manager)

        if not self.validation.validate_combine_images_count(
                combine_images_list=combine_images_list,
                dialog_manager=dialog_manager,
                check_min=True,
                check_max=False
        ):
            await callback.answer("Нужно минимум 2 изображения", show_alert=True)
            return

        await callback.answer()
        self.dialog_data_helper.set_is_combining_images(dialog_manager, True)
        await dialog_manager.show()

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        async with tg_action(self.bot, callback.message.chat.id, "upload_photo"):
            combined_result_url = await self.image_manager.process_combine_with_prompt(
                dialog_manager=dialog_manager,
                state=state,
                combine_images_list=combine_images_list,
                prompt=self.DEFAULT_combine_image_prompt,
                chat_id=callback.message.chat.id
            )

        self.dialog_data_helper.set_is_combining_images(dialog_manager, False)
        self.dialog_data_helper.set_combine_image_url(dialog_manager, combined_result_url)

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_combine_image_from_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        combine_images_list = await self.image_manager.prepare_new_image_for_combine(
            dialog_manager=dialog_manager,
            chat_id=callback.message.chat.id
        )

        if not combine_images_list:
            await callback.answer("Ошибка при подготовке изображения", show_alert=True)
            return

        self.dialog_data_helper.set_combine_images_list(dialog_manager, combine_images_list, 0)
        await callback.answer()

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_edit_image_prompt_input_from_confirm_new_image(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.clear_edit_image_prompt_error_flags(dialog_manager=dialog_manager)
        await message.delete()

        if not self.validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            return

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)
        edit_image_prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self.validation.validate_edit_image_prompt(text=edit_image_prompt, dialog_manager=dialog_manager):
            return

        self.dialog_data_helper.set_edit_image_prompt(dialog_manager, edit_image_prompt)
        self.dialog_data_helper.set_is_applying_edits(dialog_manager, True)

        await dialog_manager.show()

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            images_url = await self.image_manager.edit_new_image_with_prompt(
                dialog_manager=dialog_manager,
                organization_id=state.organization_id,
                prompt=edit_image_prompt,
                chat_id=message.chat.id
            )

        self.dialog_data_helper.set_is_applying_edits(dialog_manager, False)

        self.image_manager.update_image_after_edit_from_confirm_new_image(
            dialog_manager=dialog_manager,
            images_url=images_url
        )

        self.dialog_data_helper.set_edit_image_prompt(dialog_manager, "")

        await dialog_manager.show()

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

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.image_menu)

    @auto_log()
    @traced_method()
    async def handle_show_old_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.dialog_data_helper.set_showing_old_image(dialog_manager, True)
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
        self.dialog_data_helper.set_showing_old_image(dialog_manager, False)
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

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.image_menu)

    @auto_log()
    @traced_method()
    async def handle_auto_generate_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)

        await callback.answer()
        await callback.message.edit_text(
            "Генерирую изображение, это может занять время... Не совершайте никаких действий",
            reply_markup=None
        )

        async with tg_action(self.bot, callback.message.chat.id, "upload_photo"):
            images_url = await self.image_manager.generate_new_image(
                dialog_manager=dialog_manager,
            )

        self.dialog_data_helper.set_is_generating_image(dialog_manager, False)
        self.dialog_data_helper.set_generated_images_url(dialog_manager, images_url)

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.new_image_confirm)

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
    async def handle_reference_generation_image_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)
        await message.delete()

        self.dialog_data_helper.clear_reference_generation_image_prompt_errors(dialog_manager)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if not self.validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            return

        reference_generation_image_prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self.validation.validate_prompt(
                text=reference_generation_image_prompt,
                dialog_manager=dialog_manager,
                void_flag="has_void_reference_generation_image_prompt",
                small_flag="has_small_reference_generation_image_prompt",
                big_flag="has_big_reference_generation_image_prompt"
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
                prompt=reference_generation_image_prompt
            )

        self.dialog_data_helper. set_is_generating_image(dialog_manager, False)
        self.dialog_data_helper.set_generated_images_url(dialog_manager, images_url)
        self.dialog_data_helper.clear_reference_generation_image_data(dialog_manager)

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.new_image_confirm)

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

        if not self.validation.validate_image_content_type(
                message=message,
                dialog_manager=dialog_manager,
                error_flag="has_invalid_reference_generation_image_type"
        ):
            return

        photo = message.photo[-1]
        if not self.validation.validate_image_size(
                photo=photo,
                dialog_manager=dialog_manager,
                error_flag="has_big_reference_generation_image_size"
        ):
            return

        self.dialog_data_helper.set_reference_generation_image_file_id(dialog_manager, photo.file_id)

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.reference_image_generation)

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
        await dialog_manager.switch_to(state=model.GeneratePublicationStates.image_generation_mode_select)

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
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.reference_image_generation)
        else:
            await callback.answer("Ошибка при загрузке изображения", show_alert=True)

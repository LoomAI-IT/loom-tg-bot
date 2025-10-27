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
    ErrorFlagsManager, ImageManager, TextProcessor, ValidationService,
    PublicationManager, CategoryManager
)


class GeneratePublicationService(interface.IGeneratePublicationService):
    DEFAULT_COMBINE_PROMPT = "Объедини эти фотографии в одну композицию, чтобы это смотрелось органично"

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
        self._validation = ValidationService(
            logger=self.logger
        )
        self._text_processor = TextProcessor(
            logger=self.logger
        )
        self.message_extractor = MessageExtractor(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client
        )
        self._alerts_manager = AlertsManager(
            self.state_repo
        )
        self._image_manager = ImageManager(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client
        )
        self.dialog_data_helper = ErrorFlagsManager()
        self._publication_manager = PublicationManager(
            logger=self.logger,
            loom_content_client=self.loom_content_client
        )
        self._category_manager = CategoryManager(
            logger=self.logger,
            loom_content_client=self.loom_content_client,
            loom_employee_client=self.loom_employee_client,
            llm_chat_repo=self.llm_chat_repo
        )

    # ============= PUBLIC HANDLERS: INPUT & CATEGORY =============

    @auto_log()
    @traced_method()
    async def handle_generate_publication_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await message.delete()

        self.dialog_data_helper.clear_inputdialog_data_helper(dialog_manager=dialog_manager)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if not self._validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            return

        text = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self._validation.validate_input_text(text=text, dialog_manager=dialog_manager):
            return

        dialog_manager.dialog_data["input_text"] = text
        dialog_manager.dialog_data["has_input_text"] = True

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

        await self._category_manager.select_category(
            dialog_manager=dialog_manager,
            category_id=int(category_id)
        )

        if self._category_manager.has_start_text(dialog_manager):
            self._category_manager.set_start_text(dialog_manager)
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.generation)
        else:
            self.logger.info("Нет стартового текста")
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.input_text)

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

        if not await self._category_manager.navigate_to_create_category(
                dialog_manager=dialog_manager,
                state=state
        ):
            await callback.answer("У вас нет прав создавать рубрики", show_alert=True)
            return

        await callback.answer()

    # ============= PUBLIC HANDLERS: TEXT GENERATION =============

    @auto_log()
    @traced_method()
    async def handle_generate_text(
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

        category_id = dialog_manager.dialog_data["category_id"]
        input_text = dialog_manager.dialog_data["input_text"]

        async with tg_action(self.bot, callback.message.chat.id):
            publication_data = await self.loom_content_client.generate_publication_text(
                category_id=category_id,
                text_reference=input_text,
            )

        dialog_manager.dialog_data["publication_text"] = publication_data["text"]

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_generate_text_with_image(
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

        category_id = dialog_manager.dialog_data["category_id"]
        input_text = dialog_manager.dialog_data["input_text"]

        async with tg_action(self.bot, callback.message.chat.id):
            publication_data = await self.loom_content_client.generate_publication_text(
                category_id=category_id,
                text_reference=input_text,
            )

        dialog_manager.dialog_data["publication_text"] = publication_data["text"]

        async with tg_action(self.bot, callback.message.chat.id, "upload_photo"):
            images_url = await self.loom_content_client.generate_publication_image(
                category_id=category_id,
                publication_text=publication_data["text"],
                text_reference=input_text,
            )

        dialog_manager.dialog_data["publication_images_url"] = images_url
        dialog_manager.dialog_data["has_image"] = True
        dialog_manager.dialog_data["is_custom_image"] = False
        dialog_manager.dialog_data["current_image_index"] = 0

        # Проверяем длину текста с изображением
        if await self._text_processor.check_text_length_with_image(dialog_manager=dialog_manager):
            return

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

    # ============= PUBLIC HANDLERS: IMAGE NAVIGATION =============

    @auto_log()
    @traced_method()
    async def handle_next_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self._image_manager.navigate_images(
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
        self._image_manager.navigate_images(
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
        dialog_manager.dialog_data["is_regenerating_text"] = True
        await dialog_manager.show()

        category_id = dialog_manager.dialog_data["category_id"]
        input_text = dialog_manager.dialog_data["input_text"]

        async with tg_action(self.bot, callback.message.chat.id):
            regenerated_data = await self.loom_content_client.generate_publication_text(
                category_id=category_id,
                text_reference=input_text,
            )

        dialog_manager.dialog_data["is_regenerating_text"] = False

        dialog_manager.dialog_data["publication_text"] = regenerated_data["text"]

        # Проверяем длину текста с изображением
        if await self._text_processor.check_text_length_with_image(dialog_manager=dialog_manager):
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
        await message.delete()

        self.dialog_data_helper.clear_regenerate_promptdialog_data_helper(dialog_manager=dialog_manager)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if not self._validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            return

        prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self._validation.validate_prompt(
                text=prompt,
                dialog_manager=dialog_manager,
                void_flag="has_void_regenerate_prompt",
                small_flag="has_small_regenerate_prompt",
                big_flag="has_big_regenerate_prompt"
        ):
            return

        dialog_manager.dialog_data["regenerate_prompt"] = prompt
        dialog_manager.dialog_data["has_regenerate_prompt"] = True
        dialog_manager.dialog_data["is_regenerating_text"] = True

        await dialog_manager.show()

        category_id = dialog_manager.dialog_data["category_id"]
        current_text = dialog_manager.dialog_data["publication_text"]

        async with tg_action(self.bot, message.chat.id):
            regenerated_data = await self.loom_content_client.regenerate_publication_text(
                category_id=category_id,
                publication_text=current_text,
                prompt=prompt
            )

        dialog_manager.dialog_data["publication_text"] = regenerated_data["text"]

        dialog_manager.dialog_data["is_regenerating_text"] = False
        dialog_manager.dialog_data["has_regenerate_prompt"] = False

        if await self._text_processor.check_text_length_with_image(dialog_manager=dialog_manager):
            return

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

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

        new_text = message.html_text.replace('\n', '<br/>')

        if not self._validation.validate_edited_text(text=new_text, dialog_manager=dialog_manager):
            return

        dialog_manager.dialog_data["publication_text"] = new_text
        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

    # ============= PUBLIC HANDLERS: IMAGE GENERATION & EDITING =============

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
        dialog_manager.dialog_data["is_generating_image"] = True
        await dialog_manager.show()

        category_id = dialog_manager.dialog_data["category_id"]
        publication_text = dialog_manager.dialog_data["publication_text"]
        text_reference = dialog_manager.dialog_data["input_text"]

        images_url = await self._image_manager.generate_new_image(
            dialog_manager=dialog_manager,
            category_id=category_id,
            publication_text=publication_text,
            text_reference=text_reference,
            chat_id=callback.message.chat.id
        )

        dialog_manager.dialog_data["is_generating_image"] = False
        dialog_manager.dialog_data["generated_images_url"] = images_url

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_edit_image_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, send=True)
        await message.delete()

        self.dialog_data_helper.clear_image_promptdialog_data_helper(dialog_manager=dialog_manager)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if not self._validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            return

        prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self._validation.validate_prompt(
                text=prompt,
                dialog_manager=dialog_manager,
                void_flag="has_void_image_prompt",
                small_flag="has_small_image_prompt",
                big_flag="has_big_image_prompt"
        ):
            return

        dialog_manager.dialog_data["image_prompt"] = prompt
        dialog_manager.dialog_data["is_generating_image"] = True

        await dialog_manager.show()

        images_url = await self._image_manager.edit_image_with_prompt(
            dialog_manager=dialog_manager,
            organization_id=state.organization_id,
            prompt=prompt,
            chat_id=message.chat.id
        )

        dialog_manager.dialog_data["is_generating_image"] = False
        dialog_manager.dialog_data["generated_images_url"] = images_url

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

        await message.delete()

        self.dialog_data_helper.clear_image_uploaddialog_data_helper(dialog_manager=dialog_manager)

        if not self._validation.validate_image_content_type(message=message, dialog_manager=dialog_manager):
            return

        if message.photo:
            photo = message.photo[-1]

            if not self._validation.validate_image_size(photo=photo, dialog_manager=dialog_manager):
                return

            await self._image_manager.upload_custom_image(photo=photo, dialog_manager=dialog_manager)

            if await self._text_processor.check_text_length_with_image(dialog_manager=dialog_manager):
                return

            await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

            self.logger.info("Конец загрузки изображения")
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

        self._image_manager.clear_image_data(dialog_manager=dialog_manager)

        await callback.answer("Изображение удалено", show_alert=True)
        await dialog_manager.switch_to(state=model.GeneratePublicationStates.preview)

    # ============= PUBLIC HANDLERS: PUBLICATION & MODERATION =============

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
        # dialog_manager.show_mode = ShowMode.EDIT
        #
        # state = await self._get_state(dialog_manager=dialog_manager)
        #
        # category_id = dialog_manager.dialog_data["category_id"]
        # text_reference = dialog_manager.dialog_data["input_text"]
        # text = dialog_manager.dialog_data["publication_text"]
        #
        # image_url, image_content, image_filename = await self._get_selected_image_data(dialog_manager=dialog_manager)
        #
        # publication_data = await self.loom_content_client.create_publication(
        #     state.organization_id,
        #     category_id,
        #     state.account_id,
        #     text_reference,
        #     text,
        #     "draft",
        #     image_url=image_url,
        #     image_content=image_content,
        #     image_filename=image_filename,
        # )
        #
        # selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
        # if selected_networks:
        #     tg_source = selected_networks.get("telegram_checkbox", False)
        #     vk_source = selected_networks.get("vkontakte_checkbox", False)
        #
        #     await self.loom_content_client.change_publication(
        #         publication_id=publication_data["publication_id"],
        #         tg_source=tg_source,
        #         vk_source=vk_source,
        #     )
        #
        # self.logger.info("Публикация сохранена в черновики")
        #
        # await callback.answer("💾 Сохранено в черновики!", show_alert=True)
        #
        # if await self._check_alerts(dialog_manager=dialog_manager):
        #     return
        #
        # await dialog_manager.start(
        #     model.ContentMenuStates.content_menu,
        #     mode=StartMode.RESET_STACK
        # )
        # span.set_status(Status(StatusCode.OK))

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

        category_id = dialog_manager.dialog_data["category_id"]
        text_reference = dialog_manager.dialog_data["input_text"]
        text = dialog_manager.dialog_data["publication_text"]
        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

        image_url, image_content, image_filename = await self._image_manager.get_selected_image_data(
            dialog_manager=dialog_manager
        )

        await self._publication_manager.send_to_moderation(
            state=state,
            category_id=category_id,
            text_reference=text_reference,
            text=text,
            image_url=image_url,
            image_content=image_content,
            image_filename=image_filename,
            selected_networks=selected_networks
        )

        await callback.answer("Публикация отправлена на модерацию", show_alert=True)

        if await self._alerts_manager.check_alerts(dialog_manager=dialog_manager, state=state):
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
        self._publication_manager.toggle_social_network(checkbox=checkbox, dialog_manager=dialog_manager)
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

        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

        if not self._validation.validate_selected_networks(selected_networks):
            self.logger.info("Не выбрана ни одна соцсеть")
            await callback.answer(
                "Выберите хотя бы одну социальную сеть",
                show_alert=True
            )
            return

        category_id = dialog_manager.dialog_data["category_id"]
        text_reference = dialog_manager.dialog_data["input_text"]
        text = dialog_manager.dialog_data["publication_text"]

        image_url, image_content, image_filename = await self._image_manager.get_selected_image_data(
            dialog_manager=dialog_manager
        )

        await self._publication_manager.publish_now(
            dialog_manager=dialog_manager,
            state=state,
            category_id=category_id,
            text_reference=text_reference,
            text=text,
            image_url=image_url,
            image_content=image_content,
            image_filename=image_filename,
            selected_networks=selected_networks
        )

        await callback.answer("Публикация успешно опубликована", show_alert=True)

        if await self._alerts_manager.check_alerts(dialog_manager=dialog_manager, state=state):
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
        self._publication_manager.remove_photo_from_long_text(dialog_manager=dialog_manager)
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

        category_id = dialog_manager.dialog_data["category_id"]
        current_text = dialog_manager.dialog_data["publication_text"]
        expected_length = dialog_manager.dialog_data["expected_length"]

        compress_prompt = f"Сожми текст до {expected_length} символов, сохраняя основной смысл и ключевые идеи"

        async with tg_action(self.bot, callback.message.chat.id):
            compressed_data = await self.loom_content_client.regenerate_publication_text(
                category_id=category_id,
                publication_text=current_text,
                prompt=compress_prompt
            )

        dialog_manager.dialog_data["publication_text"] = compressed_data["text"]

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

        if await self._alerts_manager.check_alerts(dialog_manager=dialog_manager, state=state):
            self.logger.info("Обнаружены алерты")
            return

        await dialog_manager.start(
            state=model.ContentMenuStates.content_menu,
            mode=StartMode.RESET_STACK
        )

    # ============= PUBLIC HANDLERS: IMAGE COMBINING =============

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

        if self._image_manager.start_combine_images(dialog_manager=dialog_manager):
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_choice)
        else:
            self._image_manager.init_combine_from_scratch(dialog_manager=dialog_manager)
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_with_current(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()

        combine_images_list = await self._image_manager.prepare_current_image_for_combine(
            dialog_manager=dialog_manager,
            chat_id=callback.message.chat.id
        )

        dialog_manager.dialog_data["combine_images_list"] = combine_images_list
        dialog_manager.dialog_data["combine_current_index"] = 0

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_from_scratch(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()

        self._image_manager.init_combine_from_scratch(dialog_manager=dialog_manager)

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

        await message.delete()

        self.dialog_data_helper.clear_combine_uploaddialog_data_helper(dialog_manager=dialog_manager)

        if not self._validation.validate_image_content_type(
                message=message,
                dialog_manager=dialog_manager,
                error_flag="has_invalid_combine_image_type"
        ):
            return

        combine_images_list = dialog_manager.dialog_data.get("combine_images_list", [])

        if not self._validation.validate_combine_images_count(
                combine_images_list=combine_images_list,
                dialog_manager=dialog_manager,
                check_min=False,
                check_max=True
        ):
            return

        if message.photo:
            photo = message.photo[-1]

            if not self._validation.validate_image_size(
                    photo=photo,
                    dialog_manager=dialog_manager,
                    error_flag="has_big_combine_image_size"
            ):
                return

            self._image_manager.upload_combine_image(photo=photo, dialog_manager=dialog_manager)

    @auto_log()
    @traced_method()
    async def handle_prev_combine_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self._image_manager.navigate_images(
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
        self._image_manager.navigate_images(
            dialog_manager=dialog_manager,
            images_key="combine_images_list",
            index_key="combine_current_index",
            direction="next"
        )
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_back_from_combine_upload(
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

        if self._image_manager.should_return_to_new_image_confirm(dialog_manager=dialog_manager):
            self._image_manager.cleanup_combine_data(dialog_manager=dialog_manager)
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
        self._image_manager.delete_combine_image(dialog_manager=dialog_manager)
        await callback.answer("Изображение удалено")

    @auto_log()
    @traced_method()
    async def handle_combine_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await message.delete()

        self.dialog_data_helper.clear_combine_promptdialog_data_helper(dialog_manager=dialog_manager)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if not self._validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            return

        prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self._validation.validate_combine_prompt(prompt=prompt, dialog_manager=dialog_manager):
            return

        combine_images_list = dialog_manager.dialog_data.get("combine_images_list", [])

        if not self._validation.validate_combine_images_count(
                combine_images_list=combine_images_list,
                dialog_manager=dialog_manager,
                check_min=True,
                check_max=False
        ):
            return

        dialog_manager.dialog_data["combine_prompt"] = prompt
        dialog_manager.dialog_data["is_combining_images"] = True
        await dialog_manager.show()

        combined_result_url = await self._image_manager.process_combine_with_prompt(
            dialog_manager=dialog_manager,
            state=state,
            combine_images_list=combine_images_list,
            prompt=prompt or self.DEFAULT_COMBINE_PROMPT,
            chat_id=message.chat.id
        )

        dialog_manager.dialog_data["is_combining_images"] = False
        dialog_manager.dialog_data["combine_result_url"] = combined_result_url

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_skip_combine_prompt(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        combine_images_list = dialog_manager.dialog_data.get("combine_images_list", [])

        if not self._validation.validate_combine_images_count(
                combine_images_list=combine_images_list,
                dialog_manager=dialog_manager,
                check_min=True,
                check_max=False
        ):
            await callback.answer("Нужно минимум 2 изображения", show_alert=True)
            return

        await callback.answer()
        dialog_manager.dialog_data["is_combining_images"] = True
        await dialog_manager.show()

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        combined_result_url = await self._image_manager.process_combine_with_prompt(
            dialog_manager=dialog_manager,
            state=state,
            combine_images_list=combine_images_list,
            prompt=self.DEFAULT_COMBINE_PROMPT,
            chat_id=callback.message.chat.id
        )

        dialog_manager.dialog_data["is_combining_images"] = False
        dialog_manager.dialog_data["combine_result_url"] = combined_result_url

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_combine_from_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        combine_images_list = await self._image_manager.combine_from_new_image(
            dialog_manager=dialog_manager,
            chat_id=callback.message.chat.id
        )

        if not combine_images_list:
            await callback.answer("Ошибка при подготовке изображения", show_alert=True)
            return

        dialog_manager.dialog_data["combine_images_list"] = combine_images_list
        dialog_manager.dialog_data["combine_current_index"] = 0
        await callback.answer()

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_new_image_confirm_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await message.delete()

        self.dialog_data_helper.cleardialog_data_helper(
            dialog_manager,
            "has_small_edit_prompt",
            "has_big_edit_prompt",
            "has_invalid_content_type"
        )

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)

        if not self._validation.validate_content_type(message=message, dialog_manager=dialog_manager):
            return

        prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not self._validation.validate_edit_image_prompt(prompt=prompt, dialog_manager=dialog_manager):
            return

        dialog_manager.dialog_data["image_edit_prompt"] = prompt
        dialog_manager.dialog_data["is_applying_edits"] = True

        await dialog_manager.show()

        images_url = await self._image_manager.edit_new_image_with_prompt(
            dialog_manager=dialog_manager,
            organization_id=state.organization_id,
            prompt=prompt,
            chat_id=message.chat.id
        )

        dialog_manager.dialog_data["is_applying_edits"] = False

        self._image_manager.update_image_after_edit(
            dialog_manager=dialog_manager,
            images_url=images_url
        )

        dialog_manager.dialog_data.pop("image_edit_prompt", None)

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

        self._image_manager.confirm_new_image(dialog_manager=dialog_manager)

        if await self._text_processor.check_text_length_with_image(dialog_manager=dialog_manager):
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
        self._image_manager.toggle_showing_old_image(dialog_manager=dialog_manager, show_old=True)
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
        self._image_manager.toggle_showing_old_image(dialog_manager=dialog_manager, show_old=False)
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

        self._image_manager.reject_new_image(dialog_manager=dialog_manager)

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.image_menu)

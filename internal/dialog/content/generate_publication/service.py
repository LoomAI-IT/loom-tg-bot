from typing import Any

from aiogram_dialog.widgets.input import MessageInput

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox, Button

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method

from internal.dialog._state_helper import _StateHelper
from internal.dialog._alerts import _AlertsChecker
from internal.dialog._message_extractor import _MessageExtractor

from ._error_flags import _ErrorFlagsManager
from ._image_manager import _ImageManager
from ._text_processor import _TextProcessor
from ._validation import _ValidationService


class GeneratePublicationService(interface.IGeneratePublicationService):
    MIN_IMAGE_PROMPT_LENGTH = 10
    MAX_IMAGE_PROMPT_LENGTH = 2000

    MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
    MAX_COMBINE_IMAGES = 3

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
        self._state_helper = _StateHelper(
            state_repo=self.state_repo
        )
        self._validation = _ValidationService(
            logger=self.logger
        )
        self._text_processor = _TextProcessor(
            logger=self.logger
        )
        self._message_extractor = _MessageExtractor(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client
        )
        self._alerts_checker = _AlertsChecker(
            self.state_repo
        )
        self._image_manager = _ImageManager(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client
        )
        self._error_flags = _ErrorFlagsManager()

    # ============= PUBLIC HANDLERS: INPUT & CATEGORY =============

    @auto_log()
    @traced_method()
    async def handle_generate_publication_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
        await message.delete()

        self._error_flags.clear_input_error_flags(dialog_manager=dialog_manager)

        state = await self._state_helper.get_state(dialog_manager=dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        text = await self._message_extractor.process_voice_or_text_input(
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
        category = await self.loom_content_client.get_category_by_id(
            category_id=int(category_id)
        )

        dialog_manager.dialog_data["category_id"] = category.id
        dialog_manager.dialog_data["category_name"] = category.name
        dialog_manager.dialog_data["category_hint"] = category.hint

        if dialog_manager.start_data:
            if dialog_manager.start_data.get("has_input_text"):
                self.logger.info("Есть стартовый текст")
                dialog_manager.dialog_data["has_input_text"] = True
                dialog_manager.dialog_data["input_text"] = dialog_manager.start_data["input_text"]
                await dialog_manager.switch_to(state=model.GeneratePublicationStates.generation)
            else:
                self.logger.info("Нет стартового текста")
                await dialog_manager.switch_to(state=model.GeneratePublicationStates.input_text)
        else:
            self.logger.info("Нет стартовых данных")
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.input_text)

    @auto_log()
    @traced_method()
    async def go_to_create_category(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        state = await self._state_helper.get_state(dialog_manager=dialog_manager)

        employee = await self.loom_employee_client.get_employee_by_account_id(
            account_id=state.account_id
        )

        if not employee.setting_category_permission:
            self.logger.info("Отказано в доступе")
            await callback.answer("У вас нет прав создавать рубрики", show_alert=True)
            return

        await callback.answer()
        chat = await self.llm_chat_repo.get_chat_by_state_id(state_id=state.id)
        if chat:
            await self.llm_chat_repo.delete_chat(chat_id=chat[0].id)

        await dialog_manager.start(
            state=model.CreateCategoryStates.create_category,
            mode=StartMode.RESET_STACK
        )

    # ============= PUBLIC HANDLERS: TEXT GENERATION =============

    @auto_log()
    @traced_method()
    async def handle_generate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
        await message.delete()

        self._error_flags.clear_regenerate_prompt_error_flags(dialog_manager=dialog_manager)

        state = await self._state_helper.get_state(dialog_manager=dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для регенерации")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        prompt = await self._message_extractor.process_voice_or_text_input(
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        await message.delete()

        self._error_flags.clear_text_edit_error_flags(dialog_manager=dialog_manager)

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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        await callback.answer()
        dialog_manager.dialog_data["is_generating_image"] = True
        await dialog_manager.show()

        self._image_manager.backup_current_image(dialog_manager=dialog_manager)

        category_id = dialog_manager.dialog_data["category_id"]
        publication_text = dialog_manager.dialog_data["publication_text"]
        text_reference = dialog_manager.dialog_data["input_text"]

        current_image_content = None
        current_image_filename = None

        if await self._image_manager.get_current_image_data(dialog_manager=dialog_manager):
            current_image_content, current_image_filename = await self._image_manager.get_current_image_data(
                dialog_manager=dialog_manager
            )

        async with tg_action(self.bot, callback.message.chat.id, "upload_photo"):
            images_url = await self.loom_content_client.generate_publication_image(
                category_id=category_id,
                publication_text=publication_text,
                text_reference=text_reference,
                image_content=current_image_content,
                image_filename=current_image_filename,
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
        await message.delete()

        self._error_flags.clear_image_prompt_error_flags(dialog_manager=dialog_manager)

        state = await self._state_helper.get_state(dialog_manager=dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для генерации изображения")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        prompt = await self._message_extractor.process_voice_or_text_input(
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

        self._image_manager.backup_current_image(dialog_manager=dialog_manager)

        current_image_content = None
        current_image_filename = None

        if await self._image_manager.get_current_image_data(dialog_manager=dialog_manager):
            current_image_content, current_image_filename = await self._image_manager.get_current_image_data(dialog_manager=dialog_manager)

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            images_url = await self.loom_content_client.edit_image(
                organization_id=state.organization_id,
                prompt=prompt,
                image_content=current_image_content,
                image_filename=current_image_filename,
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        await message.delete()

        self._error_flags.clear_image_upload_error_flags(dialog_manager=dialog_manager)

        if message.content_type != ContentType.PHOTO:
            self.logger.info("Неверный тип контента для изображения")
            dialog_manager.dialog_data["has_invalid_image_type"] = True
            return

        if message.photo:
            photo = message.photo[-1]

            if hasattr(photo, 'file_size') and photo.file_size:
                if photo.file_size > self.MAX_IMAGE_SIZE_BYTES:
                    self.logger.info("Размер изображения превышает лимит")
                    dialog_manager.dialog_data["has_big_image_size"] = True
                    return

            dialog_manager.dialog_data["custom_image_file_id"] = photo.file_id
            dialog_manager.dialog_data["has_image"] = True
            dialog_manager.dialog_data["is_custom_image"] = True

            dialog_manager.dialog_data.pop("publication_images_url", None)
            dialog_manager.dialog_data.pop("current_image_index", None)

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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        state = await self._state_helper.get_state(dialog_manager=dialog_manager)

        category_id = dialog_manager.dialog_data["category_id"]
        text_reference = dialog_manager.dialog_data["input_text"]
        text = dialog_manager.dialog_data["publication_text"]

        image_url, image_content, image_filename = await self._image_manager.get_selected_image_data(dialog_manager=dialog_manager)

        publication_data = await self.loom_content_client.create_publication(
            organization_id=state.organization_id,
            category_id=category_id,
            creator_id=state.account_id,
            text_reference=text_reference,
            text=text,
            moderation_status="moderation",
            image_url=image_url,
            image_content=image_content,
            image_filename=image_filename,
        )

        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
        if selected_networks:
            self.logger.info("Установка выбранных соцсетей")
            tg_source = selected_networks.get("telegram_checkbox", False)
            vk_source = selected_networks.get("vkontakte_checkbox", False)

            await self.loom_content_client.change_publication(
                publication_id=publication_data["publication_id"],
                tg_source=tg_source,
                vk_source=vk_source,
            )

        await callback.answer("Публикация отправлена на модерацию", show_alert=True)

        if await self._alerts_checker.check_alerts(dialog_manager=dialog_manager, state=state):
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        if "selected_social_networks" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["selected_social_networks"] = {}

        network_id = checkbox.widget_id
        is_checked = checkbox.is_checked()

        dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_publish_now(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        state = await self._state_helper.get_state(dialog_manager=dialog_manager)

        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
        has_selected_networks = any(selected_networks.values())

        if not has_selected_networks:
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

        publication_data = await self.loom_content_client.create_publication(
            organization_id=state.organization_id,
            category_id=category_id,
            creator_id=state.account_id,
            text_reference=text_reference,
            text=text,
            moderation_status="draft",
            image_url=image_url,
            image_content=image_content,
            image_filename=image_filename,
        )

        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
        tg_source = selected_networks.get("telegram_checkbox", False)
        vk_source = selected_networks.get("vkontakte_checkbox", False)

        await self.loom_content_client.change_publication(
            publication_id=publication_data["publication_id"],
            tg_source=tg_source,
            vk_source=vk_source,
        )

        post_links = await self.loom_content_client.moderate_publication(
            publication_id=publication_data["publication_id"],
            moderator_id=state.account_id,
            moderation_status="approved"
        )

        dialog_manager.dialog_data["post_links"] = post_links

        await callback.answer("Публикация успешно опубликована", show_alert=True)

        if await self._alerts_checker.check_alerts(dialog_manager=dialog_manager, state=state):
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        dialog_manager.dialog_data["has_image"] = False
        dialog_manager.dialog_data.pop("publication_images_url", None)
        dialog_manager.dialog_data.pop("custom_image_file_id", None)
        dialog_manager.dialog_data.pop("is_custom_image", None)
        dialog_manager.dialog_data.pop("current_image_index", None)

        self.logger.info("Изображение удалено из-за длинного текста")
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        state = await self._state_helper.get_state(dialog_manager=dialog_manager)

        if await self._alerts_checker.check_alerts(dialog_manager=dialog_manager, state=state):
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        await callback.answer()

        has_image = dialog_manager.dialog_data.get("has_image", False)

        if has_image:
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_choice)
        else:
            dialog_manager.dialog_data["combine_images_list"] = []
            dialog_manager.dialog_data["combine_current_index"] = 0
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_with_current(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        await callback.answer()

        dialog_manager.dialog_data["combine_images_list"] = []
        dialog_manager.dialog_data["combine_current_index"] = 0

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        await message.delete()

        self._error_flags.clear_combine_upload_error_flags(dialog_manager=dialog_manager)

        if message.content_type != ContentType.PHOTO:
            self.logger.info("Неверный тип контента для объединения изображения")
            dialog_manager.dialog_data["has_invalid_combine_image_type"] = True
            return

        combine_images_list = dialog_manager.dialog_data.get("combine_images_list", [])

        if len(combine_images_list) >= self.MAX_COMBINE_IMAGES:
            self.logger.info("Достигнут лимит изображений для объединения")
            dialog_manager.dialog_data["combine_images_limit_reached"] = True
            return

        if message.photo:
            photo = message.photo[-1]

            if hasattr(photo, 'file_size') and photo.file_size:
                if photo.file_size > self.MAX_IMAGE_SIZE_BYTES:
                    self.logger.info("Размер изображения превышает лимит")
                    dialog_manager.dialog_data["has_big_combine_image_size"] = True
                    return

            combine_images_list.append(photo.file_id)
            dialog_manager.dialog_data["combine_images_list"] = combine_images_list
            dialog_manager.dialog_data["combine_current_index"] = len(combine_images_list) - 1

            self.logger.info(f"Изображение добавлено. Всего: {len(combine_images_list)}")

    @auto_log()
    @traced_method()
    async def handle_prev_combine_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        await callback.answer()

        # Проверяем, есть ли данные от new_image_confirm (generated_images_url или combine_result_url)
        has_generated_images = dialog_manager.dialog_data.get("generated_images_url") is not None
        has_combine_result = dialog_manager.dialog_data.get("combine_result_url") is not None

        # Если есть временные данные от генерации/объединения, значит пришли из new_image_confirm
        if has_generated_images or has_combine_result:
            dialog_manager.dialog_data.pop("combine_images_list", None)
            dialog_manager.dialog_data.pop("combine_current_index", None)

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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        combine_images_list = dialog_manager.dialog_data.get("combine_images_list", [])
        current_index = dialog_manager.dialog_data.get("combine_current_index", 0)

        if current_index < len(combine_images_list):
            combine_images_list.pop(current_index)
            dialog_manager.dialog_data["combine_images_list"] = combine_images_list

            # Корректируем индекс
            if current_index >= len(combine_images_list) > 0:
                dialog_manager.dialog_data["combine_current_index"] = len(combine_images_list) - 1
            elif len(combine_images_list) == 0:
                dialog_manager.dialog_data["combine_current_index"] = 0

        await callback.answer("Изображение удалено")

    @auto_log()
    @traced_method()
    async def handle_combine_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
        await message.delete()

        self._error_flags.clear_combine_prompt_error_flags(dialog_manager=dialog_manager)

        state = await self._state_helper.get_state(dialog_manager=dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для промпта объединения")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        prompt = await self._message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        # Валидация промпта через ValidationService
        if not self._validation.validate_combine_prompt(prompt=prompt, dialog_manager=dialog_manager):
            return

        dialog_manager.dialog_data["combine_prompt"] = prompt

        combine_images_list = dialog_manager.dialog_data.get("combine_images_list", [])

        if len(combine_images_list) < 2:
            dialog_manager.dialog_data["not_enough_combine_images"] = True
            return

        dialog_manager.dialog_data["is_combining_images"] = True
        await dialog_manager.show()

        # Сохраняем backup (если старый backup не был создан ранее)
        if not dialog_manager.dialog_data.get("old_image_backup"):
            dialog_manager.dialog_data["old_image_backup"] = self._image_manager.create_image_backup_dict(
                dialog_manager=dialog_manager
            )

        combined_images_url = await self._image_manager.combine_images_with_prompt(
            dialog_manager=dialog_manager,
            state=state,
            combine_images_list=combine_images_list,
            prompt=prompt or self.DEFAULT_COMBINE_PROMPT,
            chat_id=message.chat.id
        )

        dialog_manager.dialog_data["is_combining_images"] = False
        dialog_manager.dialog_data["combine_result_url"] = combined_images_url[0] if combined_images_url else None

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_skip_combine_prompt(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        combine_images_list = dialog_manager.dialog_data.get("combine_images_list", [])

        if len(combine_images_list) < 2:
            dialog_manager.dialog_data["not_enough_combine_images"] = True
            await callback.answer("Нужно минимум 2 изображения", show_alert=True)
            return

        await callback.answer()
        dialog_manager.dialog_data["is_combining_images"] = True
        await dialog_manager.show()

        state = await self._state_helper.get_state(dialog_manager=dialog_manager)

        # Сохраняем backup (если старый backup не был создан ранее)
        if not dialog_manager.dialog_data.get("old_image_backup"):
            dialog_manager.dialog_data["old_image_backup"] = self._image_manager.create_image_backup_dict(
                dialog_manager=dialog_manager
            )

        combined_images_url = await self._image_manager.combine_images_with_prompt(
            dialog_manager=dialog_manager,
            state=state,
            combine_images_list=combine_images_list,
            prompt=self.DEFAULT_COMBINE_PROMPT,
            chat_id=callback.message.chat.id
        )

        dialog_manager.dialog_data["is_combining_images"] = False
        dialog_manager.dialog_data["combine_result_url"] = combined_images_url[0] if combined_images_url else None

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.new_image_confirm)

    # ============= NEW IMAGE CONFIRM HANDLERS =============

    @auto_log()
    @traced_method()
    async def handle_combine_from_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """
        Переход к объединению изображений с новой сгенерированной картинкой как первой
        """
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        await callback.answer()

        # Получаем новую сгенерированную картинку или результат комбинирования
        generated_images_url = dialog_manager.dialog_data.get("generated_images_url")
        combine_result_url = dialog_manager.dialog_data.get("combine_result_url")

        # Определяем URL изображения для подготовки
        image_url = None
        if generated_images_url and len(generated_images_url) > 0:
            image_url = generated_images_url[0]
        elif combine_result_url:
            image_url = combine_result_url

        # Подготавливаем изображение для комбинирования
        combine_images_list = []
        if image_url:
            file_id = await self._image_manager.download_and_get_file_id(
                image_url=image_url,
                chat_id=callback.message.chat.id
            )
            if file_id:
                combine_images_list.append(file_id)
                self.logger.info(f"Новая картинка добавлена в список для объединения: {file_id}")
            else:
                await callback.answer("Ошибка при подготовке изображения", show_alert=True)
                return

        # Сохраняем backup для возможности отмены
        if not dialog_manager.dialog_data.get("old_generated_image_backup") and \
                not dialog_manager.dialog_data.get("old_image_backup"):
            if generated_images_url:
                dialog_manager.dialog_data["old_generated_image_backup"] = {
                    "type": "url",
                    "value": generated_images_url,
                    "index": 0
                }
            elif combine_result_url:
                dialog_manager.dialog_data["old_image_backup"] = {
                    "type": "url",
                    "value": combine_result_url
                }

        # Устанавливаем данные для combine_images_upload
        dialog_manager.dialog_data["combine_images_list"] = combine_images_list
        dialog_manager.dialog_data["combine_current_index"] = 0

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_new_image_confirm_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
        await message.delete()

        self._error_flags.clear_error_flags(
            dialog_manager,
            "has_small_edit_prompt",
            "has_big_edit_prompt",
            "has_invalid_content_type"
        )

        state = await self._state_helper.get_state(dialog_manager=dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для правок изображения")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        prompt = await self._message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        if not prompt or len(prompt) < 10:
            self.logger.info("Слишком короткий промпт для правок")
            dialog_manager.dialog_data["has_small_edit_prompt"] = True
            return

        if len(prompt) > 1000:
            self.logger.info("Слишком длинный промпт для правок")
            dialog_manager.dialog_data["has_big_edit_prompt"] = True
            return

        dialog_manager.dialog_data["image_edit_prompt"] = prompt
        dialog_manager.dialog_data["is_applying_edits"] = True

        await dialog_manager.show()

        # Определяем URL текущего изображения
        image_url = None
        if dialog_manager.dialog_data.get("generated_images_url"):
            images_url = dialog_manager.dialog_data["generated_images_url"]
            if images_url and len(images_url) > 0:
                image_url = images_url[0]
        elif dialog_manager.dialog_data.get("combine_result_url"):
            image_url = dialog_manager.dialog_data["combine_result_url"]

        # Скачиваем и редактируем изображение
        current_image_content = None
        current_image_filename = None
        if image_url:
            current_image_content, _ = await self._image_manager.download_image(image_url)
            current_image_filename = "current_image.jpg"

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            images_url = await self.loom_content_client.edit_image(
                organization_id=state.organization_id,
                prompt=prompt,
                image_content=current_image_content,
                image_filename=current_image_filename,
            )

        dialog_manager.dialog_data["is_applying_edits"] = False

        # Обновляем изображения
        if dialog_manager.dialog_data.get("generated_images_url"):
            dialog_manager.dialog_data["generated_images_url"] = images_url
        elif dialog_manager.dialog_data.get("combine_result_url"):
            dialog_manager.dialog_data["combine_result_url"] = images_url[0] if images_url else None

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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        await callback.answer("Изображение применено")

        # Применяем сгенерированное изображение или результат комбинирования
        generated_images_url = dialog_manager.dialog_data.get("generated_images_url")
        combine_result_url = dialog_manager.dialog_data.get("combine_result_url")

        if generated_images_url:
            self._image_manager.set_generated_images(
                dialog_manager=dialog_manager,
                images_url=generated_images_url
            )
        elif combine_result_url:
            self._image_manager.set_generated_images(
                dialog_manager=dialog_manager,
                images_url=[combine_result_url]
            )

        self._image_manager.clear_temporary_image_data(dialog_manager=dialog_manager)

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
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
        dialog_manager.dialog_data["showing_old_image"] = True
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_show_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)
        dialog_manager.dialog_data["showing_old_image"] = False
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_reject_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager=dialog_manager)

        await callback.answer("Изображение отклонено")

        old_image_backup = dialog_manager.dialog_data.get("old_generated_image_backup") or \
                           dialog_manager.dialog_data.get("old_image_backup")

        self._image_manager.restore_image_from_backup(
            dialog_manager=dialog_manager,
            backup_dict=old_image_backup
        )
        self._image_manager.clear_temporary_image_data(dialog_manager=dialog_manager)

        await dialog_manager.switch_to(state=model.GeneratePublicationStates.image_menu)

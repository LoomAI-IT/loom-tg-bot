import re
from typing import Any

import aiohttp
from aiogram_dialog.widgets.input import MessageInput

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType, BufferedInputFile
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox, Button

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method


class GeneratePublicationService(interface.IGeneratePublicationService):
    MIN_TEXT_PROMPT_LENGTH = 10
    MAX_TEXT_PROMPT_LENGTH = 2000

    MIN_IMAGE_PROMPT_LENGTH = 10
    MAX_IMAGE_PROMPT_LENGTH = 2000

    MIN_EDITED_TEXT_LENGTH = 50
    MAX_EDITED_TEXT_LENGTH = 4000

    MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
    MAX_COMBINE_IMAGES = 3

    MAX_TEXT_WITH_IMAGE = 1024
    RECOMMENDED_TEXT_WITH_IMAGE = 800
    MAX_TEXT_WITHOUT_IMAGE = 4096
    RECOMMENDED_TEXT_WITHOUT_IMAGE = 3600

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

    # ============= PUBLIC HANDLERS: INPUT & CATEGORY =============

    @auto_log()
    @traced_method()
    async def handle_generate_publication_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)
        await message.delete()

        self._clear_input_error_flags(dialog_manager)

        state = await self._get_state(dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        text = await self._process_voice_or_text_input(message, dialog_manager, state.organization_id)

        if not self._validate_input_text(text, dialog_manager):
            return

        dialog_manager.dialog_data["input_text"] = text
        dialog_manager.dialog_data["has_input_text"] = True

        await dialog_manager.switch_to(model.GeneratePublicationStates.generation)

    @auto_log()
    @traced_method()
    async def handle_select_category(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            category_id: str
    ) -> None:
        self._set_edit_mode(dialog_manager)
        category = await self.loom_content_client.get_category_by_id(
            int(category_id)
        )

        dialog_manager.dialog_data["category_id"] = category.id
        dialog_manager.dialog_data["category_name"] = category.name
        dialog_manager.dialog_data["category_hint"] = category.hint

        if dialog_manager.start_data:
            if dialog_manager.start_data.get("has_input_text"):
                self.logger.info("Есть стартовый текст")
                dialog_manager.dialog_data["has_input_text"] = True
                dialog_manager.dialog_data["input_text"] = dialog_manager.start_data["input_text"]
                await dialog_manager.switch_to(model.GeneratePublicationStates.generation)
            else:
                self.logger.info("Нет стартового текста")
                await dialog_manager.switch_to(model.GeneratePublicationStates.input_text)
        else:
            self.logger.info("Нет стартовых данных")
            await dialog_manager.switch_to(model.GeneratePublicationStates.input_text)

    @auto_log()
    @traced_method()
    async def go_to_create_category(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)

        state = await self._get_state(dialog_manager)

        employee = await self.loom_employee_client.get_employee_by_account_id(
            state.account_id
        )

        if not employee.setting_category_permission:
            self.logger.info("Отказано в доступе")
            await callback.answer("У вас нет прав создавать рубрики", show_alert=True)
            return

        await callback.answer()
        chat = await self.llm_chat_repo.get_chat_by_state_id(state.id)
        if chat:
            await self.llm_chat_repo.delete_chat(chat[0].id)

        await dialog_manager.start(
            model.CreateCategoryStates.create_category,
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
        self._set_edit_mode(dialog_manager)

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

        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_generate_text_with_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)
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
                category_id,
                publication_data["text"],
                input_text,
            )

        dialog_manager.dialog_data["publication_images_url"] = images_url
        dialog_manager.dialog_data["has_image"] = True
        dialog_manager.dialog_data["is_custom_image"] = False
        dialog_manager.dialog_data["current_image_index"] = 0

        # Проверяем длину текста с изображением
        if await self._check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    # ============= PUBLIC HANDLERS: IMAGE NAVIGATION =============

    @auto_log()
    @traced_method()
    async def handle_next_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)
        self._navigate_images(dialog_manager, "publication_images_url", "current_image_index", "next")
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_prev_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)
        self._navigate_images(dialog_manager, "publication_images_url", "current_image_index", "prev")
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_regenerate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)

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
        if await self._check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_regenerate_text_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)
        await message.delete()

        self._clear_regenerate_prompt_error_flags(dialog_manager)

        state = await self._get_state(dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для регенерации")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        prompt = await self._process_voice_or_text_input(message, dialog_manager, state.organization_id)

        if not self._validate_prompt(
                prompt,
                dialog_manager,
                "has_void_regenerate_prompt",
                "has_small_regenerate_prompt",
                "has_big_regenerate_prompt"
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

        if await self._check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_edit_text(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        self._set_edit_mode(dialog_manager)

        await message.delete()

        self._clear_text_edit_error_flags(dialog_manager)

        new_text = message.html_text.replace('\n', '<br/>')

        if not self._validate_edited_text(new_text, dialog_manager):
            return

        dialog_manager.dialog_data["publication_text"] = new_text
        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    # ============= PUBLIC HANDLERS: IMAGE GENERATION & EDITING =============

    @auto_log()
    @traced_method()
    async def handle_generate_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)

        await callback.answer()
        dialog_manager.dialog_data["is_generating_image"] = True
        await dialog_manager.show()

        self._backup_current_image(dialog_manager)

        category_id = dialog_manager.dialog_data["category_id"]
        publication_text = dialog_manager.dialog_data["publication_text"]
        text_reference = dialog_manager.dialog_data["input_text"]

        current_image_content = None
        current_image_filename = None

        if await self._get_current_image_data(dialog_manager):
            current_image_content, current_image_filename = await self._get_current_image_data(dialog_manager)

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

        await dialog_manager.switch_to(model.GeneratePublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_edit_image_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)
        await message.delete()

        self._clear_image_prompt_error_flags(dialog_manager)

        state = await self._get_state(dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для генерации изображения")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        prompt = await self._process_voice_or_text_input(message, dialog_manager, state.organization_id)

        if not self._validate_prompt(
                prompt,
                dialog_manager,
                "has_void_image_prompt",
                "has_small_image_prompt",
                "has_big_image_prompt"
        ):
            return

        dialog_manager.dialog_data["image_prompt"] = prompt
        dialog_manager.dialog_data["is_generating_image"] = True

        await dialog_manager.show()

        self._backup_current_image(dialog_manager)

        current_image_content = None
        current_image_filename = None

        if await self._get_current_image_data(dialog_manager):
            current_image_content, current_image_filename = await self._get_current_image_data(dialog_manager)

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            images_url = await self.loom_content_client.edit_image(
                organization_id=state.organization_id,
                prompt=prompt,
                image_content=current_image_content,
                image_filename=current_image_filename,
            )

        dialog_manager.dialog_data["is_generating_image"] = False
        dialog_manager.dialog_data["generated_images_url"] = images_url

        await dialog_manager.switch_to(model.GeneratePublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)

        await message.delete()

        self._clear_image_upload_error_flags(dialog_manager)

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

            if await self._check_text_length_with_image(dialog_manager):
                return

            await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

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
        self._set_edit_mode(dialog_manager)

        self._clear_image_data(dialog_manager)

        await callback.answer("Изображение удалено", show_alert=True)
        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

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
        # state = await self._get_state(dialog_manager)
        #
        # category_id = dialog_manager.dialog_data["category_id"]
        # text_reference = dialog_manager.dialog_data["input_text"]
        # text = dialog_manager.dialog_data["publication_text"]
        #
        # image_url, image_content, image_filename = await self._get_selected_image_data(dialog_manager)
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
        # if await self._check_alerts(dialog_manager):
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
        self._set_edit_mode(dialog_manager)

        state = await self._get_state(dialog_manager)

        category_id = dialog_manager.dialog_data["category_id"]
        text_reference = dialog_manager.dialog_data["input_text"]
        text = dialog_manager.dialog_data["publication_text"]

        image_url, image_content, image_filename = await self._get_selected_image_data(dialog_manager)

        publication_data = await self.loom_content_client.create_publication(
            state.organization_id,
            category_id,
            state.account_id,
            text_reference,
            text,
            "moderation",
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

        if await self._check_alerts(dialog_manager):
            return

        await dialog_manager.start(
            model.ContentMenuStates.content_menu,
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
        self._set_edit_mode(dialog_manager)

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
        self._set_edit_mode(dialog_manager)

        state = await self._get_state(dialog_manager)

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

        image_url, image_content, image_filename = await self._get_selected_image_data(dialog_manager)

        publication_data = await self.loom_content_client.create_publication(
            state.organization_id,
            category_id,
            state.account_id,
            text_reference,
            text,
            "draft",
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
            publication_data["publication_id"],
            state.account_id,
            "approved"
        )

        dialog_manager.dialog_data["post_links"] = post_links

        await callback.answer("Публикация успешно опубликована", show_alert=True)

        if await self._check_alerts(dialog_manager):
            self.logger.info("Переход к алертам")
            return

        await dialog_manager.switch_to(model.GeneratePublicationStates.publication_success)

    @auto_log()
    @traced_method()
    async def handle_remove_photo_from_long_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)

        # Удаляем изображение
        dialog_manager.dialog_data["has_image"] = False
        dialog_manager.dialog_data.pop("publication_images_url", None)
        dialog_manager.dialog_data.pop("custom_image_file_id", None)
        dialog_manager.dialog_data.pop("is_custom_image", None)
        dialog_manager.dialog_data.pop("current_image_index", None)

        self.logger.info("Изображение удалено из-за длинного текста")
        await callback.answer("Изображение удалено", show_alert=True)
        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_compress_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)

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

        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_go_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)

        if await self._check_alerts(dialog_manager):
            self.logger.info("Обнаружены алерты")
            return

        await dialog_manager.start(
            model.ContentMenuStates.content_menu,
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
        self._set_edit_mode(dialog_manager)

        await callback.answer()

        # Проверяем, есть ли текущее изображение
        has_image = dialog_manager.dialog_data.get("has_image", False)

        if has_image:
            # Переходим к выбору: с текущим или с новых
            await dialog_manager.switch_to(model.GeneratePublicationStates.combine_images_choice)
        else:
            # Сразу переходим к загрузке
            dialog_manager.dialog_data["combine_images_list"] = []
            dialog_manager.dialog_data["combine_current_index"] = 0
            await dialog_manager.switch_to(model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_with_current(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)

        await callback.answer()

        # Добавляем текущее изображение как первое в списке
        combine_images_list = []

        if dialog_manager.dialog_data.get("custom_image_file_id"):
            file_id = dialog_manager.dialog_data["custom_image_file_id"]
            combine_images_list.append(file_id)
        elif dialog_manager.dialog_data.get("publication_images_url"):
            images_url = dialog_manager.dialog_data["publication_images_url"]
            current_index = dialog_manager.dialog_data.get("current_image_index", 0)
            if current_index < len(images_url):
                # Скачиваем текущее изображение и загружаем в бот, чтобы получить file_id
                current_url = images_url[current_index]
                image_content, _ = await self._download_image(current_url)

                # Отправляем изображение себе, чтобы получить file_id
                message = await self.bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=BufferedInputFile(image_content, filename="tmp_image.png"),
                )
                await message.delete()
                combine_images_list.append(message.photo[-1].file_id)

        dialog_manager.dialog_data["combine_images_list"] = combine_images_list
        dialog_manager.dialog_data["combine_current_index"] = 0

        await dialog_manager.switch_to(model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_from_scratch(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)

        await callback.answer()

        # Начинаем с пустого списка
        dialog_manager.dialog_data["combine_images_list"] = []
        dialog_manager.dialog_data["combine_current_index"] = 0

        await dialog_manager.switch_to(model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_combine_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)

        await message.delete()

        self._clear_combine_upload_error_flags(dialog_manager)

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
        self._set_edit_mode(dialog_manager)
        self._navigate_images(dialog_manager, "combine_images_list", "combine_current_index", "prev")
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_next_combine_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)
        self._navigate_images(dialog_manager, "combine_images_list", "combine_current_index", "next")
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
        self._set_edit_mode(dialog_manager)

        await callback.answer()

        # Проверяем, есть ли данные от new_image_confirm (generated_images_url или combine_result_url)
        has_generated_images = dialog_manager.dialog_data.get("generated_images_url") is not None
        has_combine_result = dialog_manager.dialog_data.get("combine_result_url") is not None

        # Если есть временные данные от генерации/объединения, значит пришли из new_image_confirm
        if has_generated_images or has_combine_result:
            # Очищаем временные данные объединения
            dialog_manager.dialog_data.pop("combine_images_list", None)
            dialog_manager.dialog_data.pop("combine_current_index", None)
            # Возвращаемся в new_image_confirm
            await dialog_manager.switch_to(model.GeneratePublicationStates.new_image_confirm)
        else:
            # Иначе возвращаемся в image_menu
            await dialog_manager.switch_to(model.GeneratePublicationStates.image_menu)

    @auto_log()
    @traced_method()
    async def handle_delete_combine_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)

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
        self._set_edit_mode(dialog_manager)
        await message.delete()

        self._clear_combine_prompt_error_flags(dialog_manager)

        state = await self._get_state(dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для промпта объединения")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        prompt = message.text if message.content_type == ContentType.TEXT else \
            await self._speech_to_text(message, dialog_manager, state.organization_id)

        # Валидация промпта с допущением пустого значения
        if prompt and len(prompt) < self.MIN_IMAGE_PROMPT_LENGTH:
            self.logger.info("Слишком короткий промпт для объединения")
            dialog_manager.dialog_data["has_small_combine_prompt"] = True
            return

        if prompt and len(prompt) > self.MAX_IMAGE_PROMPT_LENGTH:
            self.logger.info("Слишком длинный промпт для объединения")
            dialog_manager.dialog_data["has_big_combine_prompt"] = True
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
            dialog_manager.dialog_data["old_image_backup"] = self._create_image_backup_dict(dialog_manager)

        combined_images_url = await self._combine_images_with_prompt(
            dialog_manager, state, combine_images_list, prompt, message.chat.id
        )

        dialog_manager.dialog_data["is_combining_images"] = False
        dialog_manager.dialog_data["combine_result_url"] = combined_images_url[0] if combined_images_url else None

        await dialog_manager.switch_to(model.GeneratePublicationStates.new_image_confirm)

    @auto_log()
    @traced_method()
    async def handle_skip_combine_prompt(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработчик для кнопки 'Пропустить' - объединяет изображения с дефолтным промптом"""
        self._set_edit_mode(dialog_manager)

        combine_images_list = dialog_manager.dialog_data.get("combine_images_list", [])

        if len(combine_images_list) < 2:
            dialog_manager.dialog_data["not_enough_combine_images"] = True
            await callback.answer("Нужно минимум 2 изображения", show_alert=True)
            return

        await callback.answer()
        dialog_manager.dialog_data["is_combining_images"] = True
        await dialog_manager.show()

        state = await self._get_state(dialog_manager)

        # Сохраняем backup (если старый backup не был создан ранее)
        if not dialog_manager.dialog_data.get("old_image_backup"):
            dialog_manager.dialog_data["old_image_backup"] = self._create_image_backup_dict(dialog_manager)

        combined_images_url = await self._combine_images_with_prompt(
            dialog_manager, state, combine_images_list, self.DEFAULT_COMBINE_PROMPT, callback.message.chat.id
        )

        dialog_manager.dialog_data["is_combining_images"] = False
        dialog_manager.dialog_data["combine_result_url"] = combined_images_url[0] if combined_images_url else None

        await dialog_manager.switch_to(model.GeneratePublicationStates.new_image_confirm)

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
        self._set_edit_mode(dialog_manager)

        await callback.answer()

        # Инициализируем список для объединения
        combine_images_list = []

        # Получаем новую сгенерированную картинку или результат комбинирования
        generated_images_url = dialog_manager.dialog_data.get("generated_images_url")
        combine_result_url = dialog_manager.dialog_data.get("combine_result_url")

        # Определяем, какое изображение использовать
        image_url_to_download = None
        if generated_images_url and len(generated_images_url) > 0:
            image_url_to_download = generated_images_url[0]
        elif combine_result_url:
            image_url_to_download = combine_result_url

        # Скачиваем изображение и загружаем в бот, чтобы получить file_id
        if image_url_to_download:
            try:
                image_content, _ = await self._download_image(image_url_to_download)

                # Отправляем изображение себе, чтобы получить file_id
                message = await self.bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=BufferedInputFile(image_content, filename="new_generated_image.jpg"),
                )
                await message.delete()
                combine_images_list.append(message.photo[-1].file_id)

                self.logger.info(f"Новая картинка добавлена в список для объединения: {message.photo[-1].file_id}")
            except Exception as e:
                self.logger.error(f"Ошибка при загрузке изображения: {e}")
                await callback.answer("Ошибка при подготовке изображения", show_alert=True)
                return

        # Сохраняем backup для возможности отмены (используем существующий backup)
        # Backup уже должен быть сохранен при генерации изображения
        # Но на всякий случай проверим и сохраним, если его нет
        if not dialog_manager.dialog_data.get("old_generated_image_backup") and \
                not dialog_manager.dialog_data.get("old_image_backup"):
            # Сохраняем текущее состояние новой картинки как backup
            # На случай если пользователь захочет вернуться
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

        # Переходим к окну загрузки дополнительных изображений
        await dialog_manager.switch_to(model.GeneratePublicationStates.combine_images_upload)

    @auto_log()
    @traced_method()
    async def handle_new_image_confirm_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._set_edit_mode(dialog_manager)
        await message.delete()

        self._clear_error_flags(
            dialog_manager,
            "has_small_edit_prompt",
            "has_big_edit_prompt",
            "has_invalid_content_type"
        )

        state = await self._get_state(dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для правок изображения")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        prompt = message.text if message.content_type == ContentType.TEXT else \
            await self._speech_to_text(message, dialog_manager, state.organization_id)

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

        # Определяем, какое изображение редактируем
        current_image_content = None
        current_image_filename = None

        # Проверяем, есть ли сгенерированное изображение или результат комбинирования
        if dialog_manager.dialog_data.get("generated_images_url"):
            # Это было сгенерированное изображение
            images_url = dialog_manager.dialog_data["generated_images_url"]
            if images_url and len(images_url) > 0:
                image_content, _ = await self._download_image(images_url[0])
                current_image_content = image_content
                current_image_filename = "generated_image.jpg"
        elif dialog_manager.dialog_data.get("combine_result_url"):
            # Это был результат комбинирования
            combine_url = dialog_manager.dialog_data["combine_result_url"]
            image_content, _ = await self._download_image(combine_url)
            current_image_content = image_content
            current_image_filename = "combined_image.jpg"

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
            images_url = await self.loom_content_client.edit_image(
                organization_id=state.organization_id,
                prompt=prompt,
                image_content=current_image_content,
                image_filename=current_image_filename,
            )

        dialog_manager.dialog_data["is_applying_edits"] = False

        # Обновляем изображения - теперь это новое отредактированное изображение
        if dialog_manager.dialog_data.get("generated_images_url"):
            dialog_manager.dialog_data["generated_images_url"] = images_url
        elif dialog_manager.dialog_data.get("combine_result_url"):
            dialog_manager.dialog_data["combine_result_url"] = images_url[0] if images_url else None

        # Очищаем промпт после применения
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
        self._set_edit_mode(dialog_manager)

        await callback.answer("Изображение применено")

        # Применяем сгенерированное изображение или результат комбинирования
        generated_images_url = dialog_manager.dialog_data.get("generated_images_url")
        combine_result_url = dialog_manager.dialog_data.get("combine_result_url")

        if generated_images_url:
            self._set_generated_images(dialog_manager, generated_images_url)
        elif combine_result_url:
            self._set_generated_images(dialog_manager, [combine_result_url])

        self._clear_temporary_image_data(dialog_manager)

        if await self._check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(model.GeneratePublicationStates.image_menu)

    @auto_log()
    @traced_method()
    async def handle_show_old_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Переключение на показ старой картинки"""
        self._set_edit_mode(dialog_manager)
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
        """Переключение на показ новой картинки"""
        self._set_edit_mode(dialog_manager)
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
        self._set_edit_mode(dialog_manager)

        await callback.answer("Изображение отклонено")

        # Восстанавливаем старое изображение, если оно было
        old_image_backup = dialog_manager.dialog_data.get("old_generated_image_backup") or \
                           dialog_manager.dialog_data.get("old_image_backup")

        if old_image_backup:
            if old_image_backup["type"] == "file_id":
                dialog_manager.dialog_data["custom_image_file_id"] = old_image_backup["value"]
                dialog_manager.dialog_data["has_image"] = True
                dialog_manager.dialog_data["is_custom_image"] = True
                dialog_manager.dialog_data.pop("publication_images_url", None)
                dialog_manager.dialog_data.pop("current_image_index", None)
            elif old_image_backup["type"] == "url":
                value = old_image_backup["value"]
                if isinstance(value, list):
                    dialog_manager.dialog_data["publication_images_url"] = value
                    dialog_manager.dialog_data["current_image_index"] = old_image_backup.get("index", 0)
                else:
                    dialog_manager.dialog_data["publication_images_url"] = [value]
                    dialog_manager.dialog_data["current_image_index"] = 0
                dialog_manager.dialog_data["has_image"] = True
                dialog_manager.dialog_data["is_custom_image"] = False
                dialog_manager.dialog_data.pop("custom_image_file_id", None)
        else:
            self._clear_image_data(dialog_manager)

        self._clear_temporary_image_data(dialog_manager)

        await dialog_manager.switch_to(model.GeneratePublicationStates.image_menu)

    # ============= HELPER METHODS: GENERAL =============

    def _set_edit_mode(self, dialog_manager: DialogManager) -> None:
        """Устанавливает режим редактирования для диалога"""
        dialog_manager.show_mode = ShowMode.EDIT

    def _clear_error_flags(self, dialog_manager: DialogManager, *flag_names: str) -> None:
        """Универсальная очистка флагов ошибок"""
        for flag_name in flag_names:
            dialog_manager.dialog_data.pop(flag_name, None)

    async def _process_voice_or_text_input(
            self,
            message: Message,
            dialog_manager: DialogManager,
            organization_id: int
    ) -> str:
        """Обрабатывает текстовые, голосовые и аудио сообщения"""
        if message.content_type == ContentType.TEXT:
            return message.text if hasattr(message, 'text') else message.html_text.replace('\n', '<br/>')
        else:
            return await self._speech_to_text(message, dialog_manager, organization_id)

    def _clear_input_error_flags(self, dialog_manager: DialogManager) -> None:
        self._clear_error_flags(
            dialog_manager,
            "has_void_input_text",
            "has_small_input_text",
            "has_big_input_text",
            "has_invalid_content_type"
        )

    def _clear_regenerate_prompt_error_flags(self, dialog_manager: DialogManager) -> None:
        self._clear_error_flags(
            dialog_manager,
            "has_void_regenerate_prompt",
            "has_small_regenerate_prompt",
            "has_big_regenerate_prompt",
            "has_invalid_content_type"
        )

    def _clear_image_prompt_error_flags(self, dialog_manager: DialogManager) -> None:
        self._clear_error_flags(
            dialog_manager,
            "has_void_image_prompt",
            "has_small_image_prompt",
            "has_big_image_prompt",
            "has_invalid_content_type",
            "has_empty_voice_text"
        )

    def _clear_text_edit_error_flags(self, dialog_manager: DialogManager) -> None:
        self._clear_error_flags(
            dialog_manager,
            "has_void_text",
            "has_big_text",
            "has_small_text"
        )

    def _clear_image_upload_error_flags(self, dialog_manager: DialogManager) -> None:
        self._clear_error_flags(
            dialog_manager,
            "has_invalid_image_type",
            "has_big_image_size"
        )

    def _clear_combine_prompt_error_flags(self, dialog_manager: DialogManager) -> None:
        self._clear_error_flags(
            dialog_manager,
            "has_small_combine_prompt",
            "has_big_combine_prompt",
            "has_invalid_content_type"
        )

    def _clear_combine_upload_error_flags(self, dialog_manager: DialogManager) -> None:
        self._clear_error_flags(
            dialog_manager,
            "has_invalid_combine_image_type",
            "has_big_combine_image_size",
            "combine_images_limit_reached"
        )

    def _clear_new_image_confirm_error_flags(self, dialog_manager: DialogManager) -> None:
        self._clear_error_flags(
            dialog_manager,
            "has_small_edit_prompt",
            "has_big_edit_prompt",
            "has_invalid_content_type"
        )

    # ============= HELPER METHODS: VALIDATION =============

    def _validate_text_with_limits(
            self,
            text: str,
            min_length: int,
            max_length: int,
            dialog_manager: DialogManager,
            void_flag: str,
            small_flag: str,
            big_flag: str
    ) -> bool:
        """Универсальная валидация текста с указанными лимитами"""
        if not text:
            self.logger.info(f"Пустой текст: {void_flag}")
            dialog_manager.dialog_data[void_flag] = True
            return False

        if len(text) < min_length:
            self.logger.info(f"Слишком короткий текст: {small_flag}")
            dialog_manager.dialog_data[small_flag] = True
            return False

        if len(text) > max_length:
            self.logger.info(f"Слишком длинный текст: {big_flag}")
            dialog_manager.dialog_data[big_flag] = True
            return False

        return True

    def _validate_prompt(
            self,
            text: str,
            dialog_manager: DialogManager,
            void_flag: str,
            small_flag: str,
            big_flag: str
    ) -> bool:
        return self._validate_text_with_limits(
            text,
            self.MIN_TEXT_PROMPT_LENGTH,
            self.MAX_TEXT_PROMPT_LENGTH,
            dialog_manager,
            void_flag,
            small_flag,
            big_flag
        )

    def _validate_input_text(self, text: str, dialog_manager: DialogManager) -> bool:
        return self._validate_text_with_limits(
            text,
            self.MIN_TEXT_PROMPT_LENGTH,
            self.MAX_TEXT_PROMPT_LENGTH,
            dialog_manager,
            "has_void_input_text",
            "has_small_input_text",
            "has_big_input_text"
        )

    def _validate_edited_text(self, text: str, dialog_manager: DialogManager) -> bool:
        return self._validate_text_with_limits(
            text,
            self.MIN_EDITED_TEXT_LENGTH,
            self.MAX_EDITED_TEXT_LENGTH,
            dialog_manager,
            "has_void_text",
            "has_small_text",
            "has_big_text"
        )

    # ============= HELPER METHODS: IMAGE MANAGEMENT =============

    def _navigate_images(
            self,
            dialog_manager: DialogManager,
            images_key: str,
            index_key: str,
            direction: str
    ) -> None:
        """Универсальная навигация по списку изображений"""
        images_list = dialog_manager.dialog_data.get(images_key, [])
        current_index = dialog_manager.dialog_data.get(index_key, 0)

        if direction == "next":
            new_index = current_index + 1 if current_index < len(images_list) - 1 else 0
        else:  # prev
            new_index = current_index - 1 if current_index > 0 else len(images_list) - 1

        dialog_manager.dialog_data[index_key] = new_index

    def _create_image_backup_dict(self, dialog_manager: DialogManager) -> dict | None:
        """Создает словарь с backup текущего изображения"""
        if dialog_manager.dialog_data.get("custom_image_file_id"):
            return {
                "type": "file_id",
                "value": dialog_manager.dialog_data["custom_image_file_id"]
            }
        elif dialog_manager.dialog_data.get("publication_images_url"):
            images_url = dialog_manager.dialog_data["publication_images_url"]
            current_index = dialog_manager.dialog_data.get("current_image_index", 0)
            return {
                "type": "url",
                "value": images_url,
                "index": current_index
            }
        return None

    def _backup_current_image(self, dialog_manager: DialogManager) -> None:
        """Создает backup текущего изображения для возможности отката"""
        old_image_backup = self._create_image_backup_dict(dialog_manager)
        dialog_manager.dialog_data["old_generated_image_backup"] = old_image_backup

    def _clear_image_data(self, dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data["has_image"] = False
        dialog_manager.dialog_data.pop("publication_images_url", None)
        dialog_manager.dialog_data.pop("custom_image_file_id", None)
        dialog_manager.dialog_data.pop("is_custom_image", None)
        dialog_manager.dialog_data.pop("current_image_index", None)

    def _clear_temporary_image_data(self, dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("generated_images_url", None)
        dialog_manager.dialog_data.pop("combine_result_url", None)
        dialog_manager.dialog_data.pop("old_generated_image_backup", None)
        dialog_manager.dialog_data.pop("old_image_backup", None)
        dialog_manager.dialog_data.pop("image_edit_prompt", None)
        dialog_manager.dialog_data.pop("combine_images_list", None)
        dialog_manager.dialog_data.pop("combine_current_index", None)
        dialog_manager.dialog_data.pop("combine_prompt", None)
        dialog_manager.dialog_data.pop("showing_old_image", None)

    def _set_generated_images(self, dialog_manager: DialogManager, images_url: list[str]) -> None:
        dialog_manager.dialog_data["publication_images_url"] = images_url
        dialog_manager.dialog_data["has_image"] = True
        dialog_manager.dialog_data["is_custom_image"] = False
        dialog_manager.dialog_data["current_image_index"] = 0
        dialog_manager.dialog_data.pop("custom_image_file_id", None)

    async def _download_and_get_file_id(self, image_url: str, chat_id: int) -> str | None:
        try:
            image_content, _ = await self._download_image(image_url)

            message = await self.bot.send_photo(
                chat_id=chat_id,
                photo=BufferedInputFile(image_content, filename="tmp_image.png"),
            )
            await message.delete()
            return message.photo[-1].file_id
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке изображения: {e}")
            return None

    async def _combine_images_with_prompt(
            self,
            dialog_manager: DialogManager,
            state: model.UserState,
            combine_images_list: list[str],
            prompt: str,
            chat_id: int
    ) -> list[str] | None:
        images_content = []
        images_filenames = []

        for i, file_id in enumerate(combine_images_list):
            image_io = await self.bot.download(file_id)
            content = image_io.read()
            images_content.append(content)
            images_filenames.append(f"image_{i}.jpg")

        async with tg_action(self.bot, chat_id, "upload_photo"):
            combined_images_url = await self.loom_content_client.combine_images(
                organization_id=state.organization_id,
                category_id=dialog_manager.dialog_data["category_id"],
                images_content=images_content,
                images_filenames=images_filenames,
                prompt=prompt,
            )

        return combined_images_url

    # ============= HELPER METHODS: TEXT & IMAGE PROCESSING =============

    async def _check_text_length_with_image(self, dialog_manager: DialogManager) -> bool:
        publication_text = dialog_manager.dialog_data.get("publication_text", "")

        text_without_tags = re.sub(r'<[^>]+>', '', publication_text)
        text_length = len(text_without_tags)
        has_image = dialog_manager.dialog_data.get("has_image", False)

        if has_image and text_length > self.MAX_TEXT_WITH_IMAGE:
            self.logger.info(f"Текст слишком длинный для публикации с изображением: {text_length} символов")
            dialog_manager.dialog_data["expected_length"] = self.RECOMMENDED_TEXT_WITH_IMAGE
            await dialog_manager.switch_to(model.GeneratePublicationStates.text_too_long_alert)
            return True

        if not has_image and text_length > self.MAX_TEXT_WITHOUT_IMAGE:
            self.logger.info(f"Текст слишком длинный: {text_length} символов")
            dialog_manager.dialog_data["expected_length"] = self.RECOMMENDED_TEXT_WITHOUT_IMAGE
            await dialog_manager.switch_to(model.GeneratePublicationStates.text_too_long_alert)
            return True

        return False

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

    async def _speech_to_text(self, message: Message, dialog_manager: DialogManager, organization_id: int) -> str:
        if message.voice:
            file_id = message.voice.file_id
        else:
            file_id = message.audio.file_id

        dialog_manager.dialog_data["voice_transcribe"] = True
        await dialog_manager.show()

        file = await self.bot.get_file(file_id)
        file_data = await self.bot.download_file(file.file_path)

        text = await self.loom_content_client.transcribe_audio(
            organization_id,
            audio_content=file_data.read(),
            audio_filename="audio.mp3",
        )
        dialog_manager.dialog_data["voice_transcribe"] = False
        return text

    async def _get_current_image_data(self, dialog_manager: DialogManager) -> tuple[bytes, str] | None:
        try:
            if dialog_manager.dialog_data.get("custom_image_file_id"):
                file_id = dialog_manager.dialog_data["custom_image_file_id"]
                image_content = await self.bot.download(file_id)
                return image_content.read(), f"{file_id}.jpg"

            elif dialog_manager.dialog_data.get("publication_images_url"):
                images_url = dialog_manager.dialog_data["publication_images_url"]
                current_index = dialog_manager.dialog_data.get("current_image_index", 0)

                if current_index < len(images_url):
                    current_url = images_url[current_index]
                    image_content, content_type = await self._download_image(current_url)
                    filename = f"generated_image_{current_index}.jpg"
                    return image_content, filename

            return None
        except Exception as err:
            return None

    async def _get_selected_image_data(self, dialog_manager: DialogManager) -> tuple[
        str | None, bytes | None, str | None]:
        if dialog_manager.dialog_data.get("custom_image_file_id"):
            file_id = dialog_manager.dialog_data["custom_image_file_id"]
            image_content = await self.bot.download(file_id)
            return None, image_content.read(), f"{file_id}.jpg"

        elif dialog_manager.dialog_data.get("publication_images_url"):
            images_url = dialog_manager.dialog_data["publication_images_url"]
            current_index = dialog_manager.dialog_data.get("current_image_index", 0)

            if current_index < len(images_url):
                selected_url = images_url[current_index]
                return selected_url, None, None

        return None, None, None

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

    async def _download_image(self, image_url: str) -> tuple[bytes, str]:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                response.raise_for_status()
                content = await response.read()
                content_type = response.headers.get('content-type', 'image/png')
                return content, content_type

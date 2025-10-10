from typing import Any

import aiohttp
from aiogram_dialog.widgets.input import MessageInput

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class GeneratePublicationService(interface.IGeneratePublicationService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.loom_content_client = loom_content_client

    @auto_log()
    @traced_method()
    async def handle_generate_publication_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await message.delete()

        dialog_manager.dialog_data.pop("has_void_input_text", None)
        dialog_manager.dialog_data.pop("has_small_input_text", None)
        dialog_manager.dialog_data.pop("has_big_input_text", None)
        dialog_manager.dialog_data.pop("has_invalid_content_type", None)
        dialog_manager.dialog_data.pop("has_small_input_text", None)
        dialog_manager.dialog_data.pop("has_big_input_text", None)

        state = await self._get_state(dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return
        if message.content_type == ContentType.TEXT:
            text = message.text
        else:
            text = await self._speech_to_text(message, dialog_manager, state.organization_id)

        if not text:
            self.logger.info("Пустой текст")
            dialog_manager.dialog_data["has_void_input_text"] = True
            return

        if len(text) < 10:
            self.logger.info("Слишком короткий текст")
            dialog_manager.dialog_data["has_small_input_text"] = True
            return

        if len(text) > 2000:
            self.logger.info("Слишком длинный текст")
            dialog_manager.dialog_data["has_big_input_text"] = True
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
        dialog_manager.show_mode = ShowMode.EDIT
        category = await self.loom_content_client.get_category_by_id(
            int(category_id)
        )

        dialog_manager.dialog_data["category_id"] = category.id
        dialog_manager.dialog_data["category_name"] = category.name

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
    async def handle_generate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await callback.answer()
        await callback.message.edit_text(
            "Генерирую текст, это может занять время... Не совершайте никаких действий",
            reply_markup=None
        )

        category_id = dialog_manager.dialog_data["category_id"]
        input_text = dialog_manager.dialog_data["input_text"]

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
        dialog_manager.show_mode = ShowMode.EDIT
        await callback.answer()
        await callback.message.edit_text(
            "Генерирую текст с картинкой, это может занять минуты 3. Не совершайте никаких действий...",
            reply_markup=None
        )

        category_id = dialog_manager.dialog_data["category_id"]
        input_text = dialog_manager.dialog_data["input_text"]

        publication_data = await self.loom_content_client.generate_publication_text(
            category_id=category_id,
            text_reference=input_text,
        )

        dialog_manager.dialog_data["publication_text"] = publication_data["text"]

        images_url = await self.loom_content_client.generate_publication_image(
            category_id,
            publication_data["text"],
            input_text,
        )

        dialog_manager.dialog_data["publication_images_url"] = images_url
        dialog_manager.dialog_data["has_image"] = True
        dialog_manager.dialog_data["is_custom_image"] = False
        dialog_manager.dialog_data["current_image_index"] = 0

        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_next_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        images_url = dialog_manager.dialog_data.get("publication_images_url", [])
        current_index = dialog_manager.dialog_data.get("current_image_index", 0)

        if current_index < len(images_url) - 1:
            self.logger.info("Переход к следующему изображению")
            dialog_manager.dialog_data["current_image_index"] = current_index + 1
        else:
            self.logger.info("Переход к первому изображению")
            dialog_manager.dialog_data["current_image_index"] = 0

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_prev_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        images_url = dialog_manager.dialog_data.get("publication_images_url", [])
        current_index = dialog_manager.dialog_data.get("current_image_index", 0)

        if current_index > 0:
            self.logger.info("Переход к предыдущему изображению")
            dialog_manager.dialog_data["current_image_index"] = current_index - 1
        else:
            self.logger.info("Переход к последнему изображению")
            dialog_manager.dialog_data["current_image_index"] = len(images_url) - 1

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_regenerate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await callback.answer()
        dialog_manager.dialog_data["is_regenerating_text"] = True
        await dialog_manager.show()

        category_id = dialog_manager.dialog_data["category_id"]
        current_text = dialog_manager.dialog_data["publication_text"]

        regenerated_data = await self.loom_content_client.regenerate_publication_text(
            category_id=category_id,
            publication_text=current_text,
            prompt=None
        )

        dialog_manager.dialog_data["is_regenerating_text"] = False

        dialog_manager.dialog_data["publication_text"] = regenerated_data["text"]

        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_regenerate_text_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await message.delete()

        # Очистка флагов ошибок
        dialog_manager.dialog_data.pop("has_void_regenerate_prompt", None)
        dialog_manager.dialog_data.pop("has_small_regenerate_prompt", None)
        dialog_manager.dialog_data.pop("has_big_regenerate_prompt", None)
        dialog_manager.dialog_data.pop("has_invalid_content_type", None)

        state = await self._get_state(dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для регенерации")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        if message.content_type == ContentType.TEXT:
            prompt = message.html_text.replace('\n', '<br/>')
        else:
            prompt = await self._speech_to_text(message, dialog_manager, state.organization_id)

        if not prompt:
            self.logger.info("Пустой промпт для регенерации")
            dialog_manager.dialog_data["has_void_regenerate_prompt"] = True
            return

        if len(prompt) < 10:
            self.logger.info("Слишком короткий промпт для регенерации")
            dialog_manager.dialog_data["has_small_regenerate_prompt"] = True
            return

        if len(prompt) > 1000:
            self.logger.info("Слишком длинный промпт для регенерации")
            dialog_manager.dialog_data["has_big_regenerate_prompt"] = True
            return

        dialog_manager.dialog_data["regenerate_prompt"] = prompt
        dialog_manager.dialog_data["has_regenerate_prompt"] = True
        dialog_manager.dialog_data["is_regenerating_text"] = True

        await dialog_manager.show()

        category_id = dialog_manager.dialog_data["category_id"]
        current_text = dialog_manager.dialog_data["publication_text"]

        regenerated_data = await self.loom_content_client.regenerate_publication_text(
            category_id=category_id,
            publication_text=current_text,
            prompt=prompt
        )

        dialog_manager.dialog_data["publication_text"] = regenerated_data["text"]

        dialog_manager.dialog_data["is_regenerating_text"] = False
        dialog_manager.dialog_data["has_regenerate_prompt"] = False

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
        dialog_manager.show_mode = ShowMode.EDIT

        await message.delete()

        dialog_manager.dialog_data.pop("has_void_text", None)
        dialog_manager.dialog_data.pop("has_big_text", None)
        dialog_manager.dialog_data.pop("has_small_text", None)

        new_text = message.html_text.replace('\n', '<br/>')
        self.logger.info("HTML текст", {"html_text": new_text})
        if not new_text:
            self.logger.info("Пустой текст")
            dialog_manager.dialog_data["has_void_text"] = True
            return

        if len(new_text) > 4000:
            self.logger.info("Слишком длинный текст")
            dialog_manager.dialog_data["has_big_text"] = True
            return

        if len(new_text) < 50:
            self.logger.info("Слишком короткий текст")
            dialog_manager.dialog_data["has_small_text"] = True
            return

        dialog_manager.dialog_data["publication_text"] = new_text
        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_generate_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await callback.answer()
        dialog_manager.dialog_data["is_generating_image"] = True
        await dialog_manager.show()

        category_id = dialog_manager.dialog_data["category_id"]
        publication_text = dialog_manager.dialog_data["publication_text"]
        text_reference = dialog_manager.dialog_data["input_text"]

        current_image_content = None
        current_image_filename = None

        if await self._get_current_image_data(dialog_manager):
            current_image_content, current_image_filename = await self._get_current_image_data(dialog_manager)

        images_url = await self.loom_content_client.generate_publication_image(
            category_id=category_id,
            publication_text=publication_text,
            text_reference=text_reference,
            image_content=current_image_content,
            image_filename=current_image_filename,
        )

        dialog_manager.dialog_data["is_generating_image"] = False
        dialog_manager.dialog_data["publication_images_url"] = images_url
        dialog_manager.dialog_data["has_image"] = True
        dialog_manager.dialog_data["is_custom_image"] = False
        dialog_manager.dialog_data["current_image_index"] = 0
        dialog_manager.dialog_data.pop("custom_image_file_id", None)

        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_generate_image_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await message.delete()

        # Очистка флагов ошибок
        dialog_manager.dialog_data.pop("has_void_image_prompt", None)
        dialog_manager.dialog_data.pop("has_small_image_prompt", None)
        dialog_manager.dialog_data.pop("has_big_image_prompt", None)
        dialog_manager.dialog_data.pop("has_invalid_content_type", None)
        dialog_manager.dialog_data.pop("has_empty_voice_text", None)

        state = await self._get_state(dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для генерации изображения")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        if message.content_type == ContentType.TEXT:
            prompt = message.html_text.replace('\n', '<br/>')
        else:
            prompt = await self._speech_to_text(message, dialog_manager, state.organization_id)

        if not prompt:
            self.logger.info("Пустой промпт для изображения")
            dialog_manager.dialog_data["has_void_image_prompt"] = True
            return

        if len(prompt) < 10:
            self.logger.info("Слишком короткий промпт для изображения")
            dialog_manager.dialog_data["has_small_image_prompt"] = True
            return

        if len(prompt) > 1000:
            self.logger.info("Слишком длинный промпт для изображения")
            dialog_manager.dialog_data["has_big_image_prompt"] = True
            return

        dialog_manager.dialog_data["image_prompt"] = prompt
        dialog_manager.dialog_data["is_generating_image"] = True

        await dialog_manager.show()

        category_id = dialog_manager.dialog_data["category_id"]
        publication_text = dialog_manager.dialog_data["publication_text"]
        text_reference = dialog_manager.dialog_data["input_text"]

        current_image_content = None
        current_image_filename = None

        if await self._get_current_image_data(dialog_manager):
            current_image_content, current_image_filename = await self._get_current_image_data(
                dialog_manager
            )

        images_url = await self.loom_content_client.generate_publication_image(
            category_id=category_id,
            publication_text=publication_text,
            text_reference=text_reference,
            prompt=prompt,
            image_content=current_image_content,
            image_filename=current_image_filename,
        )

        dialog_manager.dialog_data["publication_images_url"] = images_url
        dialog_manager.dialog_data["has_image"] = True
        dialog_manager.dialog_data["is_custom_image"] = False
        dialog_manager.dialog_data["current_image_index"] = 0
        dialog_manager.dialog_data.pop("custom_image_file_id", None)
        dialog_manager.dialog_data["is_generating_image"] = False

        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

    @auto_log()
    @traced_method()
    async def handle_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await message.delete()

        dialog_manager.dialog_data.pop("has_invalid_image_type", None)
        dialog_manager.dialog_data.pop("has_big_image_size", None)

        if message.content_type != ContentType.PHOTO:
            self.logger.info("Неверный тип контента для изображения")
            dialog_manager.dialog_data["has_invalid_image_type"] = True
            return

        if message.photo:
            photo = message.photo[-1]

            if hasattr(photo, 'file_size') and photo.file_size:
                if photo.file_size > 10 * 1024 * 1024:
                    self.logger.info("Размер изображения превышает лимит")
                    dialog_manager.dialog_data["has_big_image_size"] = True
                    return

            dialog_manager.dialog_data["custom_image_file_id"] = photo.file_id
            dialog_manager.dialog_data["has_image"] = True
            dialog_manager.dialog_data["is_custom_image"] = True

            dialog_manager.dialog_data.pop("publication_images_url", None)
            dialog_manager.dialog_data.pop("current_image_index", None)

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
        dialog_manager.show_mode = ShowMode.EDIT

        dialog_manager.dialog_data["has_image"] = False
        dialog_manager.dialog_data.pop("publication_images_url", None)
        dialog_manager.dialog_data.pop("custom_image_file_id", None)
        dialog_manager.dialog_data.pop("is_custom_image", None)
        dialog_manager.dialog_data.pop("current_image_index", None)

        await callback.answer("Изображение удалено", show_alert=True)
        await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

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
        dialog_manager.show_mode = ShowMode.EDIT

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
        dialog_manager.show_mode = ShowMode.EDIT

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
        dialog_manager.show_mode = ShowMode.EDIT

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
    async def handle_go_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        if await self._check_alerts(dialog_manager):
            self.logger.info("Обнаружены алерты")
            return

        await dialog_manager.start(
            model.ContentMenuStates.content_menu,
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

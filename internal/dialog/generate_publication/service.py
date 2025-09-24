from typing import Any

import aiohttp
from aiogram_dialog.widgets.input import MessageInput

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class GeneratePublicationService(interface.IGeneratePublicationService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            kontur_content_client: interface.IKonturContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.kontur_content_client = kontur_content_client

    async def handle_text_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_text_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                dialog_manager.dialog_data.pop("has_invalid_voice_type", None)
                dialog_manager.dialog_data.pop("has_long_voice_duration", None)
                dialog_manager.dialog_data.pop("has_empty_voice_text", None)
                dialog_manager.dialog_data.pop("has_small_input_text", None)
                dialog_manager.dialog_data.pop("has_big_input_text", None)

                await message.delete()

                text = text.strip()
                if not text:
                    dialog_manager.dialog_data["has_void_input_text"] = True
                    return
                dialog_manager.dialog_data.pop("has_void_input_text", None)

                if len(text) < 10:
                    dialog_manager.dialog_data["has_small_input_text"] = True
                    return
                dialog_manager.dialog_data.pop("has_small_input_text", None)

                if len(text) > 2000:
                    dialog_manager.dialog_data["has_big_input_text"] = True
                    return
                dialog_manager.dialog_data.pop("has_big_input_text", None)

                dialog_manager.dialog_data["input_text"] = text
                dialog_manager.dialog_data["has_input_text"] = True

                self.logger.info("Текст для генерации введен")
                await dialog_manager.switch_to(model.GeneratePublicationStates.generation)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_voice_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_voice_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                dialog_manager.dialog_data.pop("has_void_input_text", None)
                dialog_manager.dialog_data.pop("has_small_input_text", None)
                dialog_manager.dialog_data.pop("has_big_input_text", None)

                state = await self._get_state(dialog_manager)

                if message.content_type not in [ContentType.VOICE, ContentType.AUDIO]:
                    dialog_manager.dialog_data["has_invalid_voice_type"] = True
                    return
                dialog_manager.dialog_data.pop("has_invalid_voice_type", None)

                if message.voice:
                    file_id = message.voice.file_id
                    duration = message.voice.duration
                else:
                    file_id = message.audio.file_id
                    duration = message.audio.duration

                if duration > 300:  # 5 minutes max
                    dialog_manager.dialog_data["has_long_voice_duration"] = True
                    return
                dialog_manager.dialog_data.pop("has_long_voice_duration", None)

                file = await self.bot.get_file(file_id)
                file_data = await self.bot.download_file(file.file_path)

                await message.delete()

                text = await self.kontur_content_client.transcribe_audio(
                    state.organization_id,
                    audio_content=file_data.read(),
                    audio_filename="audio.mp3",
                )

                if not text or not text.strip():
                    dialog_manager.dialog_data["has_empty_voice_text"] = True
                    return
                dialog_manager.dialog_data.pop("has_empty_voice_text", None)

                text = text.strip()

                if len(text) < 10:
                    dialog_manager.dialog_data["has_small_input_text"] = True
                    return
                dialog_manager.dialog_data.pop("has_small_input_text", None)

                if len(text) > 2000:
                    dialog_manager.dialog_data["has_big_input_text"] = True
                    return
                dialog_manager.dialog_data.pop("has_big_input_text", None)


                dialog_manager.dialog_data["input_text"] = text
                dialog_manager.dialog_data["has_input_text"] = True

                self.logger.info("Голосовое сообщение обработано")
                await dialog_manager.switch_to(model.GeneratePublicationStates.generation)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_select_category(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            category_id: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_select_category",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT
                category = await self.kontur_content_client.get_category_by_id(
                    int(category_id)
                )

                dialog_manager.dialog_data["category_id"] = category.id
                dialog_manager.dialog_data["category_name"] = category.name

                self.logger.info("Категория выбрана")

                await dialog_manager.switch_to(model.GeneratePublicationStates.input_text)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_generate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_generate_text",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await callback.answer()
                await callback.message.edit_text(
                    "🔄 Генерирую текст, это может занять время... Не совершайте никаких действий",
                    reply_markup=None
                )

                category_id = dialog_manager.dialog_data["category_id"]
                input_text = dialog_manager.dialog_data["input_text"]

                publication_data = await self.kontur_content_client.generate_publication_text(
                    category_id=category_id,
                    text_reference=input_text,
                )

                dialog_manager.dialog_data["publication_text"] = publication_data["text"]

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_generate_text_with_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_generate_text_with_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT
                await callback.answer()
                await callback.message.edit_text(
                    "🔄 Генерирую текст с картинкой, это может занять минуты 3. Не совершайте никаких действий...",
                    reply_markup=None
                )

                category_id = dialog_manager.dialog_data["category_id"]
                input_text = dialog_manager.dialog_data["input_text"]

                publication_data = await self.kontur_content_client.generate_publication_text(
                    category_id=category_id,
                    text_reference=input_text,
                )

                dialog_manager.dialog_data["publication_text"] = publication_data["text"]

                images_url = await self.kontur_content_client.generate_publication_image(
                    category_id,
                    publication_data["text"],
                    input_text,
                )

                dialog_manager.dialog_data["publication_images_url"] = images_url
                dialog_manager.dialog_data["has_image"] = True
                dialog_manager.dialog_data["is_custom_image"] = False
                dialog_manager.dialog_data["current_image_index"] = 0

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_next_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_next_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                images_url = dialog_manager.dialog_data.get("publication_images_url", [])
                current_index = dialog_manager.dialog_data.get("current_image_index", 0)

                if current_index < len(images_url) - 1:
                    dialog_manager.dialog_data["current_image_index"] = current_index + 1
                else:
                    dialog_manager.dialog_data["current_image_index"] = 0

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_prev_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_prev_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                images_url = dialog_manager.dialog_data.get("publication_images_url", [])
                current_index = dialog_manager.dialog_data.get("current_image_index", 0)

                if current_index > 0:
                    dialog_manager.dialog_data["current_image_index"] = current_index - 1
                else:
                    dialog_manager.dialog_data["current_image_index"] = len(images_url) - 1

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_regenerate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_regenerate_text",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await callback.answer()
                await callback.message.edit_text(
                    "🔄 Генерирую текст, это может занять время... Не совершайте никаких действий",
                    reply_markup=None
                )

                category_id = dialog_manager.dialog_data["category_id"]
                current_text = dialog_manager.dialog_data["publication_text"]

                regenerated_data = await self.kontur_content_client.regenerate_publication_text(
                    category_id=category_id,
                    publication_text=current_text,
                    prompt=None
                )

                dialog_manager.dialog_data["publication_text"] = regenerated_data["text"]

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_regenerate_text_with_prompt(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            prompt: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_regenerate_text_with_prompt",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()
                prompt = prompt.strip()

                # Очищаем предыдущие ошибки
                dialog_manager.dialog_data.pop("has_void_regenerate_prompt", None)
                dialog_manager.dialog_data.pop("has_small_regenerate_prompt", None)
                dialog_manager.dialog_data.pop("has_big_regenerate_prompt", None)
                dialog_manager.dialog_data.pop("has_regenerate_api_error", None)

                # Валидация
                if not prompt:
                    dialog_manager.dialog_data["has_void_regenerate_prompt"] = True
                    return

                if len(prompt) < 5:
                    dialog_manager.dialog_data["has_small_regenerate_prompt"] = True
                    return

                if len(prompt) > 500:
                    dialog_manager.dialog_data["has_big_regenerate_prompt"] = True
                    return

                # Сохраняем промпт и устанавливаем состояние загрузки
                dialog_manager.dialog_data["regenerate_prompt"] = prompt
                dialog_manager.dialog_data["is_regenerating_text"] = True

                # Обновляем UI для показа индикатора загрузки
                await dialog_manager.show()

                category_id = dialog_manager.dialog_data["category_id"]
                current_text = dialog_manager.dialog_data["publication_text"]

                regenerated_data = await self.kontur_content_client.regenerate_publication_text(
                    category_id=category_id,
                    publication_text=current_text,
                    prompt=prompt
                )

                # Обновляем данные публикации
                dialog_manager.dialog_data["publication_text"] = regenerated_data["text"]

                # Отключаем индикатор загрузки
                dialog_manager.dialog_data["is_regenerating_text"] = False

                # Переходим к превью
                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

                self.logger.info("Текст успешно перегенерирован с промптом")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_edit_text(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_edit_text",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()
                new_text = text.strip()

                if not new_text:
                    dialog_manager.dialog_data["has_void_content"] = True
                    return

                if len(new_text) > 4000:
                    dialog_manager.dialog_data["has_big_content"] = True
                    return

                if len(new_text) < 50:
                    dialog_manager.dialog_data["has_small_content"] = True
                    return

                dialog_manager.dialog_data.pop("has_void_content", None)
                dialog_manager.dialog_data.pop("has_big_content", None)
                dialog_manager.dialog_data.pop("has_small_content", None)

                dialog_manager.dialog_data["publication_text"] = new_text

                self.logger.info("Текст публикации изменен")

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_generate_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_generate_new_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await callback.answer()
                await callback.message.edit_text(
                    "🔄 Генерирую изображение, это может занять время...",
                    reply_markup=None
                )

                category_id = dialog_manager.dialog_data["category_id"]
                publication_text = dialog_manager.dialog_data["publication_text"]
                text_reference = dialog_manager.dialog_data["input_text"]

                current_image_content = None
                current_image_filename = None

                if await self._get_current_image_data(dialog_manager):
                    current_image_content, current_image_filename = await self._get_current_image_data(dialog_manager)

                images_url = await self.kontur_content_client.generate_publication_image(
                    category_id=category_id,
                    publication_text=publication_text,
                    text_reference=text_reference,
                    image_content=current_image_content,
                    image_filename=current_image_filename,
                )

                dialog_manager.dialog_data["publication_images_url"] = images_url
                dialog_manager.dialog_data["has_image"] = True
                dialog_manager.dialog_data["is_custom_image"] = False
                dialog_manager.dialog_data["current_image_index"] = 0
                dialog_manager.dialog_data.pop("custom_image_file_id", None)

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_generate_image_with_prompt(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            prompt: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_generate_image_with_prompt",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()
                prompt = prompt.strip()

                if not prompt:
                    dialog_manager.dialog_data["has_void_image_prompt"] = True
                    return

                if len(prompt) < 5:
                    dialog_manager.dialog_data["has_small_image_prompt"] = True
                    return

                if len(prompt) > 500:
                    dialog_manager.dialog_data["has_big_image_prompt"] = True
                    return

                # Clear error flags
                dialog_manager.dialog_data.pop("has_void_image_prompt", None)
                dialog_manager.dialog_data.pop("has_small_image_prompt", None)
                dialog_manager.dialog_data.pop("has_big_image_prompt", None)
                dialog_manager.dialog_data.pop("has_image_generation_error", None)

                dialog_manager.dialog_data["image_prompt"] = prompt
                dialog_manager.dialog_data["is_generating_image"] = True

                await dialog_manager.show(ShowMode.EDIT)

                category_id = dialog_manager.dialog_data["category_id"]
                publication_text = dialog_manager.dialog_data["publication_text"]
                text_reference = dialog_manager.dialog_data["input_text"]

                current_image_content = None
                current_image_filename = None

                if await self._get_current_image_data(dialog_manager):
                    current_image_content, current_image_filename = await self._get_current_image_data(
                        dialog_manager
                    )

                images_url = await self.kontur_content_client.generate_publication_image(
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
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_image_upload",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                if message.content_type != ContentType.PHOTO:
                    dialog_manager.dialog_data["has_invalid_image_type"] = True
                    return

                if message.photo:
                    photo = message.photo[-1]

                    if hasattr(photo, 'file_size') and photo.file_size:
                        if photo.file_size > 10 * 1024 * 1024:  # 10 MB
                            dialog_manager.dialog_data["has_big_image_size"] = True
                            return

                    dialog_manager.dialog_data.pop("has_invalid_image_type", None)
                    dialog_manager.dialog_data.pop("has_big_image_size", None)

                    dialog_manager.dialog_data["custom_image_file_id"] = photo.file_id
                    dialog_manager.dialog_data["has_image"] = True
                    dialog_manager.dialog_data["is_custom_image"] = True

                    dialog_manager.dialog_data.pop("publication_images_url", None)
                    dialog_manager.dialog_data.pop("current_image_index", None)

                    self.logger.info("Пользовательское изображение загружено")

                    await dialog_manager.switch_to(model.GeneratePublicationStates.preview)
                    span.set_status(Status(StatusCode.OK))
                else:
                    dialog_manager.dialog_data["has_image_processing_error"] = True

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_remove_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_remove_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                dialog_manager.dialog_data["has_image"] = False
                dialog_manager.dialog_data.pop("publication_images_url", None)
                dialog_manager.dialog_data.pop("custom_image_file_id", None)
                dialog_manager.dialog_data.pop("is_custom_image", None)
                dialog_manager.dialog_data.pop("current_image_index", None)

                self.logger.info("Изображение удалено из публикации")

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка при удалении изображения", show_alert=True)
                raise

    async def handle_add_to_drafts(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_add_to_drafts",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)

                category_id = dialog_manager.dialog_data["category_id"]
                text_reference = dialog_manager.dialog_data["input_text"]
                text = dialog_manager.dialog_data["publication_text"]

                image_url, image_content, image_filename = await self._get_selected_image_data(dialog_manager)

                publication_data = await self.kontur_content_client.create_publication(
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
                if selected_networks:
                    tg_source = selected_networks.get("telegram_checkbox", False)
                    vk_source = selected_networks.get("vkontakte_checkbox", False)

                    await self.kontur_content_client.change_publication(
                        publication_id=publication_data["publication_id"],
                        tg_source=tg_source,
                        vk_source=vk_source,
                    )

                self.logger.info("Публикация сохранена в черновики")

                await callback.answer("💾 Сохранено в черновики!", show_alert=True)

                if await self._check_alerts(dialog_manager):
                    return

                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка сохранения", show_alert=True)
                raise

    async def handle_send_to_moderation(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_send_to_moderation",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)

                category_id = dialog_manager.dialog_data["category_id"]
                text_reference = dialog_manager.dialog_data["input_text"]
                text = dialog_manager.dialog_data["publication_text"]

                image_url, image_content, image_filename = await self._get_selected_image_data(dialog_manager)

                publication_data = await self.kontur_content_client.create_publication(
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
                    tg_source = selected_networks.get("telegram_checkbox", False)
                    vk_source = selected_networks.get("vkontakte_checkbox", False)

                    await self.kontur_content_client.change_publication(
                        publication_id=publication_data["publication_id"],
                        tg_source=tg_source,
                        vk_source=vk_source,
                    )

                self.logger.info("Отправлено на модерацию")

                await callback.answer("💾 Отправлено на модерацию!", show_alert=True)

                if await self._check_alerts(dialog_manager):
                    return

                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка отправки", show_alert=True)
                raise

    async def handle_toggle_social_network(
            self,
            callback: CallbackQuery,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_toggle_social_network",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                if "selected_social_networks" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["selected_social_networks"] = {}

                network_id = checkbox.widget_id
                is_checked = checkbox.is_checked()

                dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

                self.logger.info("Социальная сеть переключена")

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
                raise

    async def handle_publish_now(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_publish_now",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)

                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                if not has_selected_networks:
                    await callback.answer(
                        "⚠️ Выберите хотя бы одну социальную сеть для публикации",
                        show_alert=True
                    )
                    return

                category_id = dialog_manager.dialog_data["category_id"]
                text_reference = dialog_manager.dialog_data["input_text"]
                text = dialog_manager.dialog_data["publication_text"]

                image_url, image_content, image_filename = await self._get_selected_image_data(dialog_manager)

                publication_data = await self.kontur_content_client.create_publication(
                    state.organization_id,
                    category_id,
                    state.account_id,
                    text_reference,
                    text,
                    "published",
                    image_url=image_url,
                    image_content=image_content,
                    image_filename=image_filename,
                )

                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                tg_source = selected_networks.get("telegram_checkbox", False)
                vk_source = selected_networks.get("vkontakte_checkbox", False)

                await self.kontur_content_client.change_publication(
                    publication_id=publication_data["publication_id"],
                    tg_source=tg_source,
                    vk_source=vk_source,
                )

                await callback.answer("💾 Опубликовано!", show_alert=True)

                if await self._check_alerts(dialog_manager):
                    return

                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка при переходе к выбору соцсетей", show_alert=True)
                raise

    async def handle_go_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_go_to_content_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                if await self._check_alerts(dialog_manager):
                    return
                
                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("❌ Ошибка", show_alert=True)
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

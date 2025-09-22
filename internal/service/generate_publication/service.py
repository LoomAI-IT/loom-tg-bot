import io
import asyncio
from typing import Any

import aiohttp
from aiogram_dialog.widgets.input import MessageInput

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class GeneratePublicationDialogService(interface.IGeneratePublicationDialogService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_organization_client: interface.IKonturOrganizationClient,
            kontur_content_client: interface.IKonturContentClient,
            kontur_domain: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client
        self.kontur_organization_client = kontur_organization_client
        self.kontur_content_client = kontur_content_client
        self.kontur_domain = kontur_domain

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
                # Получаем информацию о категории
                category = await self.kontur_content_client.get_category_by_id(
                    int(category_id)
                )

                # Сохраняем в данные диалога
                dialog_manager.dialog_data["category_id"] = category.id
                dialog_manager.dialog_data["category_name"] = category.name
                dialog_manager.dialog_data["text_style"] = category.prompt_for_text_style
                dialog_manager.dialog_data["image_style"] = category.prompt_for_image_style

                self.logger.info(
                    "Категория выбрана",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "category_id": category_id,
                        "category_name": category.name,
                    }
                )

                # Переходим к вводу текста
                await dialog_manager.switch_to(model.GeneratePublicationStates.input_text)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при выборе категории", show_alert=True)
                raise

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
                await message.delete()
                text = text.strip()

                if not text:
                    dialog_manager.dialog_data["has_void_input_text"] = True
                    await dialog_manager.switch_to(model.GeneratePublicationStates.input_text, show_mode=ShowMode.EDIT)
                    return

                if len(text) < 10:
                    dialog_manager.dialog_data["has_small_input_text"] = True
                    await dialog_manager.switch_to(model.GeneratePublicationStates.input_text, show_mode=ShowMode.EDIT)
                    return

                if len(text) > 2000:
                    dialog_manager.dialog_data["has_big_input_text"] = True
                    await dialog_manager.switch_to(model.GeneratePublicationStates.input_text, show_mode=ShowMode.EDIT)
                    return

                # Clear error flags on successful input
                dialog_manager.dialog_data.pop("has_void_input_text", None)
                dialog_manager.dialog_data.pop("has_small_input_text", None)
                dialog_manager.dialog_data.pop("has_big_input_text", None)

                # Сохраняем текст
                dialog_manager.dialog_data["input_text"] = text
                dialog_manager.dialog_data["has_input_text"] = True

                self.logger.info(
                    "Текст для генерации введен",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "text_length": len(text),
                    }
                )
                await dialog_manager.switch_to(model.GeneratePublicationStates.input_text, show_mode=ShowMode.EDIT)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка обработки текста")
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
                state = await self._get_state(dialog_manager)

                if message.content_type not in [ContentType.VOICE, ContentType.AUDIO]:
                    dialog_manager.dialog_data["has_invalid_voice_type"] = True
                    await dialog_manager.switch_to(model.GeneratePublicationStates.input_text, show_mode=ShowMode.EDIT)
                    return

                # Определяем продолжительность и file_id
                if message.voice:
                    file_id = message.voice.file_id
                    duration = message.voice.duration
                else:
                    file_id = message.audio.file_id
                    duration = message.audio.duration

                if duration > 300:  # 5 минут макс
                    dialog_manager.dialog_data["has_long_voice_duration"] = True
                    await dialog_manager.switch_to(model.GeneratePublicationStates.input_text, show_mode=ShowMode.EDIT)
                    return

                # Clear error flags and show processing message
                dialog_manager.dialog_data.pop("has_invalid_voice_type", None)
                dialog_manager.dialog_data.pop("has_long_voice_duration", None)
                dialog_manager.dialog_data.pop("has_voice_recognition_error", None)
                dialog_manager.dialog_data.pop("has_empty_voice_text", None)

                file = await self.bot.get_file(file_id)
                file_data = await self.bot.download_file(file.file_path)
                file_data = io.BytesIO(file_data.read())

                await message.delete()

                text = await self._convert_voice_to_text(state.organization_id, file_data)

                if not text or not text.strip():
                    dialog_manager.dialog_data["has_empty_voice_text"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.input_text,
                        show_mode=ShowMode.EDIT
                    )
                    return

                text = text.strip()

                # Apply same text validation as text input
                if len(text) < 10:
                    dialog_manager.dialog_data["has_small_input_text"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.input_text,
                        show_mode=ShowMode.EDIT
                    )
                    return

                if len(text) > 2000:
                    dialog_manager.dialog_data["has_big_input_text"] = True

                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.input_text,
                        show_mode=ShowMode.EDIT
                    )
                    return

                # Successful processing
                dialog_manager.dialog_data["input_text"] = text
                dialog_manager.dialog_data["has_input_text"] = True

                self.logger.info(
                    "Голосовое сообщение обработано",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "voice_duration": duration,
                        "text_length": len(text),
                    }
                )

                # Update the window to show the recognized text
                await dialog_manager.switch_to(model.GeneratePublicationStates.input_text, show_mode=ShowMode.EDIT)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                dialog_manager.dialog_data["has_voice_recognition_error"] = True
                await dialog_manager.switch_to(model.GeneratePublicationStates.input_text, show_mode=ShowMode.EDIT)
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
                await callback.answer()

                await callback.message.edit_text(
                    "🔄 Генерирую текст, это может занять время... Не совершайте никаких дейтсви",
                    reply_markup=None  # Убираем клавиатуру
                )

                category_id = dialog_manager.dialog_data["category_id"]
                input_text = dialog_manager.dialog_data["input_text"]

                publication_data = await self.kontur_content_client.generate_publication_text(
                    category_id=category_id,
                    text_reference=input_text,
                )

                dialog_manager.dialog_data["publication_tags"] = publication_data["tags"]
                dialog_manager.dialog_data["publication_name"] = publication_data["name"]
                dialog_manager.dialog_data["publication_text"] = publication_data["text"]

                # Переходим к предпросмотру
                await dialog_manager.switch_to(model.GeneratePublicationStates.preview, show_mode=ShowMode.EDIT)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
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
                await callback.answer()
                await callback.message.edit_text(
                    "🔄 Генерирую текст с картинкой, это может занять минуты 3. Не совершайте никаких дейтсвий...",
                    reply_markup=None
                )

                category_id = dialog_manager.dialog_data["category_id"]
                input_text = dialog_manager.dialog_data["input_text"]

                # Генерируем текст
                publication_data = await self.kontur_content_client.generate_publication_text(
                    category_id=category_id,
                    text_reference=input_text,
                )

                dialog_manager.dialog_data["publication_tags"] = publication_data.get("tags", [])
                dialog_manager.dialog_data["publication_name"] = publication_data["name"]
                dialog_manager.dialog_data["publication_text"] = publication_data["text"]

                # Генерируем изображение
                images_url = await self.kontur_content_client.generate_publication_image(
                    category_id,
                    publication_data["text"],
                    input_text,
                )

                # Сохраняем множественные изображения
                dialog_manager.dialog_data["publication_images_url"] = images_url
                dialog_manager.dialog_data["has_image"] = True
                dialog_manager.dialog_data["is_custom_image"] = False
                dialog_manager.dialog_data["current_image_index"] = 0  # Индекс текущего изображения

                # Переходим к предпросмотру
                await dialog_manager.switch_to(model.GeneratePublicationStates.preview, show_mode=ShowMode.EDIT)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при генерации", show_alert=True)
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
                images_url = dialog_manager.dialog_data.get("publication_images_url", [])
                current_index = dialog_manager.dialog_data.get("current_image_index", 0)

                if current_index < len(images_url) - 1:
                    dialog_manager.dialog_data["current_image_index"] = current_index + 1
                else:
                    dialog_manager.dialog_data["current_image_index"] = 0  # Циклично к первому

                await callback.answer()
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
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
                images_url = dialog_manager.dialog_data.get("publication_images_url", [])
                current_index = dialog_manager.dialog_data.get("current_image_index", 0)

                if current_index > 0:
                    dialog_manager.dialog_data["current_image_index"] = current_index - 1
                else:
                    dialog_manager.dialog_data["current_image_index"] = len(images_url) - 1  # Циклично к последнему

                await callback.answer()
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_regenerate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_regenerate_all",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await callback.answer()
                await callback.message.edit_text(
                    "🔄 Генерирую текст, это может занять время... Не совершайте никаких дейтсви",
                    reply_markup=None  # Убираем клавиатуру
                )

                category_id = dialog_manager.dialog_data["category_id"]
                current_text = dialog_manager.dialog_data["publication_text"]

                # Перегенерация через API
                regenerated_data = await self.kontur_content_client.regenerate_publication_text(
                    category_id=category_id,
                    publication_text=current_text,
                    prompt=None
                )

                # Обновляем данные
                dialog_manager.dialog_data["publication_name"] = regenerated_data["name"]
                dialog_manager.dialog_data["publication_text"] = regenerated_data["text"]
                dialog_manager.dialog_data["publication_tags"] = regenerated_data["tags"]

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при перегенерации", show_alert=True)
                raise

    async def handle_regenerate_text_with_prompt(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            prompt: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_regenerate_with_prompt",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await message.delete()
                prompt = prompt.strip()

                if not prompt:
                    dialog_manager.dialog_data["has_void_regenerate_prompt"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.regenerate_text,
                        show_mode=ShowMode.EDIT
                    )
                    return

                if len(prompt) < 5:
                    dialog_manager.dialog_data["has_small_regenerate_prompt"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.regenerate_text,
                        show_mode=ShowMode.EDIT
                    )
                    return

                if len(prompt) > 500:
                    dialog_manager.dialog_data["has_big_regenerate_prompt"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.regenerate_text,
                        show_mode=ShowMode.EDIT
                    )
                    return

                # Clear error flags on successful input
                dialog_manager.dialog_data.pop("has_void_regenerate_prompt", None)
                dialog_manager.dialog_data.pop("has_small_regenerate_prompt", None)
                dialog_manager.dialog_data.pop("has_big_regenerate_prompt", None)

                # Сохраняем промпт для отображения в состоянии ожидания
                dialog_manager.dialog_data["regenerate_prompt"] = prompt

                # Переключаемся на состояние ожидания
                await dialog_manager.switch_to(
                    model.GeneratePublicationStates.regenerate_loading,
                    show_mode=ShowMode.EDIT
                )

                category_id = dialog_manager.dialog_data["category_id"]
                current_text = dialog_manager.dialog_data["publication_text"]

                regenerated_data = await self.kontur_content_client.regenerate_publication_text(
                    category_id=category_id,
                    publication_text=current_text,
                    prompt=prompt
                )

                dialog_manager.dialog_data["publication_name"] = regenerated_data["name"]
                dialog_manager.dialog_data["publication_text"] = regenerated_data["text"]
                dialog_manager.dialog_data["publication_tags"] = regenerated_data["tags"]

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_edit_title_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_edit_title_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await message.delete()
                new_title = text.strip()

                if not new_title:
                    dialog_manager.dialog_data["has_void_title"] = True
                    await dialog_manager.switch_to(model.GeneratePublicationStates.edit_title, show_mode=ShowMode.EDIT)
                    return

                if len(new_title) > 200:
                    dialog_manager.dialog_data["has_big_title"] = True
                    await dialog_manager.switch_to(model.GeneratePublicationStates.edit_title, show_mode=ShowMode.EDIT)
                    return

                # Clear error flags on successful input
                dialog_manager.dialog_data.pop("has_void_title", None)
                dialog_manager.dialog_data.pop("has_big_title", None)

                dialog_manager.dialog_data["publication_name"] = new_title

                self.logger.info(
                    "Название публикации изменено",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "new_title": new_title,
                    }
                )

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview, show_mode=ShowMode.EDIT)
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при сохранении названия")
                raise

    async def handle_edit_tags_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_edit_tags_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await message.delete()
                tags_raw = text.strip()

                if not tags_raw:
                    # Clear error flags
                    dialog_manager.dialog_data.pop("has_too_many_tags", None)
                    dialog_manager.dialog_data["publication_tags"] = []
                    await dialog_manager.switch_to(model.GeneratePublicationStates.preview)
                    return

                # Разделяем по запятым и очищаем
                tags = [tag.strip() for tag in tags_raw.split(",")]
                tags = [tag for tag in tags if tag]  # Убираем пустые

                if len(tags) > 10:
                    dialog_manager.dialog_data["has_too_many_tags"] = True
                    await dialog_manager.switch_to(model.GeneratePublicationStates.edit_tags, show_mode=ShowMode.EDIT)
                    return

                # Clear error flags on successful input
                dialog_manager.dialog_data.pop("has_too_many_tags", None)
                dialog_manager.dialog_data["publication_tags"] = tags

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview, show_mode=ShowMode.EDIT)
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при сохранении тегов")
                raise

    async def handle_edit_content_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_edit_content_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await message.delete()
                new_text = text.strip()

                if not new_text:
                    dialog_manager.dialog_data["has_void_content"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.edit_content,
                        show_mode=ShowMode.EDIT
                    )
                    return

                if len(new_text) > 4000:
                    dialog_manager.dialog_data["has_big_content"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.edit_content,
                        show_mode=ShowMode.EDIT
                    )
                    return

                if len(new_text) < 50:
                    dialog_manager.dialog_data["has_small_content"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.edit_content,
                        show_mode=ShowMode.EDIT
                    )
                    return

                # Clear error flags on successful input
                dialog_manager.dialog_data.pop("has_void_content", None)
                dialog_manager.dialog_data.pop("has_big_content", None)
                dialog_manager.dialog_data.pop("has_small_content", None)

                dialog_manager.dialog_data["publication_text"] = new_text

                self.logger.info(
                    "Текст публикации изменен",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "text_length": len(new_text),
                    }
                )

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview, show_mode=ShowMode.EDIT)
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при сохранении текста")
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
                await callback.answer()
                await callback.message.edit_text(
                    "🔄 Генерирую изображение, это может занять время...",
                    reply_markup=None  # Убираем клавиатуру
                )

                category_id = dialog_manager.dialog_data["category_id"]
                publication_text = dialog_manager.dialog_data["publication_text"]
                text_reference = dialog_manager.dialog_data["input_text"]

                # Передаем текущее изображение если есть
                current_image_content = None
                current_image_filename = None

                if await self._get_current_image_data(dialog_manager):
                    current_image_content, current_image_filename = await self._get_current_image_data(dialog_manager)

                # Генерация через API
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

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview, show_mode=ShowMode.EDIT)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при генерации изображения", show_alert=True)
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
                await message.delete()
                prompt = prompt.strip()

                if not prompt:
                    dialog_manager.dialog_data["has_void_image_prompt"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.generate_image,
                        show_mode=ShowMode.EDIT
                    )
                    return

                if len(prompt) < 5:
                    dialog_manager.dialog_data["has_small_image_prompt"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.generate_image,
                        show_mode=ShowMode.EDIT
                    )
                    return

                if len(prompt) > 500:
                    dialog_manager.dialog_data["has_big_image_prompt"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.generate_image,
                        show_mode=ShowMode.EDIT
                    )
                    return

                # Clear error flags on successful input
                dialog_manager.dialog_data.pop("has_void_image_prompt", None)
                dialog_manager.dialog_data.pop("has_small_image_prompt", None)
                dialog_manager.dialog_data.pop("has_big_image_prompt", None)
                dialog_manager.dialog_data.pop("has_image_generation_error", None)

                # Сохраняем промпт для отображения в состоянии ожидания
                dialog_manager.dialog_data["image_prompt"] = prompt

                # Переключаемся на состояние ожидания
                await dialog_manager.switch_to(model.GeneratePublicationStates.generate_image_loading,
                                               show_mode=ShowMode.EDIT)

                try:
                    category_id = dialog_manager.dialog_data["category_id"]
                    publication_text = dialog_manager.dialog_data["publication_text"]
                    text_reference = dialog_manager.dialog_data["input_text"]

                    # Передаем текущее изображение если есть
                    current_image_content = None
                    current_image_filename = None

                    if await self._get_current_image_data(dialog_manager):
                        current_image_content, current_image_filename = await self._get_current_image_data(
                            dialog_manager)

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

                    await dialog_manager.switch_to(model.GeneratePublicationStates.preview, show_mode=ShowMode.EDIT)

                except Exception as generation_err:
                    self.logger.error(f"Image generation error: {generation_err}")
                    dialog_manager.dialog_data["has_image_generation_error"] = True
                    await dialog_manager.switch_to(model.GeneratePublicationStates.generate_image,
                                                   show_mode=ShowMode.EDIT)
                    return

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                dialog_manager.dialog_data["has_image_generation_error"] = True
                await dialog_manager.switch_to(model.GeneratePublicationStates.generate_image, show_mode=ShowMode.EDIT)
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
                if message.content_type != ContentType.PHOTO:
                    dialog_manager.dialog_data["has_invalid_image_type"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.upload_image,
                        show_mode=ShowMode.EDIT
                    )
                    return

                # Проверяем размер файла (если доступно)
                if message.photo:
                    # Берем фото с наибольшим разрешением
                    photo = message.photo[-1]

                    # Проверяем размер (если доступно)
                    if hasattr(photo, 'file_size') and photo.file_size:
                        if photo.file_size > 10 * 1024 * 1024:  # 10 МБ
                            dialog_manager.dialog_data["has_big_image_size"] = True
                            await dialog_manager.switch_to(
                                model.GeneratePublicationStates.upload_image,
                                show_mode=ShowMode.EDIT
                            )
                            return

                    # Clear error flags on successful upload
                    dialog_manager.dialog_data.pop("has_invalid_image_type", None)
                    dialog_manager.dialog_data.pop("has_big_image_size", None)

                    # Сохраняем file_id для дальнейшего использования
                    dialog_manager.dialog_data["custom_image_file_id"] = photo.file_id
                    dialog_manager.dialog_data["has_image"] = True
                    dialog_manager.dialog_data["is_custom_image"] = True

                    # Удаляем сгенерированные изображения если были
                    dialog_manager.dialog_data.pop("publication_images_url", None)
                    dialog_manager.dialog_data.pop("current_image_index", None)

                    self.logger.info(
                        "Пользовательское изображение загружено",
                        {
                            common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                            "file_id": photo.file_id,
                            "file_size": getattr(photo, 'file_size', 'unknown'),
                        }
                    )

                    await dialog_manager.switch_to(model.GeneratePublicationStates.preview)
                    span.set_status(Status(StatusCode.OK))
                else:
                    dialog_manager.dialog_data["has_image_processing_error"] = True
                    await dialog_manager.switch_to(
                        model.GeneratePublicationStates.upload_image,
                        show_mode=ShowMode.EDIT
                    )

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                dialog_manager.dialog_data["has_image_processing_error"] = True
                await dialog_manager.switch_to(model.GeneratePublicationStates.upload_image, show_mode=ShowMode.EDIT)
                raise

    async def handle_remove_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Удаление изображения из публикации"""
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_remove_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Удаляем все данные об изображении
                dialog_manager.dialog_data["has_image"] = False
                dialog_manager.dialog_data.pop("publication_images_url", None)
                dialog_manager.dialog_data.pop("custom_image_file_id", None)
                dialog_manager.dialog_data.pop("is_custom_image", None)
                dialog_manager.dialog_data.pop("current_image_index", None)

                await callback.answer("✅ Изображение удалено", show_alert=True)
                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

                self.logger.info(
                    "Изображение удалено из публикации",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )

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
                state = await self._get_state(dialog_manager)

                category_id = dialog_manager.dialog_data["category_id"]
                text_reference = dialog_manager.dialog_data["input_text"]
                tags = dialog_manager.dialog_data["publication_tags"]
                name = dialog_manager.dialog_data["publication_name"]
                text = dialog_manager.dialog_data["publication_text"]

                # Получаем данные выбранного изображения
                image_url, image_content, image_filename = await self._get_selected_image_data(dialog_manager)

                # Создаем публикацию
                publication_data = await self.kontur_content_client.create_publication(
                    state.organization_id,
                    category_id,
                    state.account_id,
                    text_reference,
                    name,
                    text,
                    tags,
                    "draft",
                    image_url=image_url,
                    image_content=image_content,
                    image_filename=image_filename,
                )

                # Если выбраны социальные сети, обновляем публикацию
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                if selected_networks:
                    tg_source = selected_networks.get("telegram_checkbox", False)
                    vk_source = selected_networks.get("vkontakte_checkbox", False)

                    await self.kontur_content_client.change_publication(
                        publication_id=publication_data["publication_id"],
                        tg_source=tg_source,
                        vk_source=vk_source,
                    )

                self.logger.info(
                    "Публикация сохранена в черновики",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "publication_id": publication_data["publication_id"],
                        "selected_image_index": dialog_manager.dialog_data.get("current_image_index", 0),
                    }
                )

                await callback.answer("💾 Сохранено в черновики!", show_alert=True)

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
                state = await self._get_state(dialog_manager)

                category_id = dialog_manager.dialog_data["category_id"]
                text_reference = dialog_manager.dialog_data["input_text"]
                tags = dialog_manager.dialog_data["publication_tags"]
                name = dialog_manager.dialog_data["publication_name"]
                text = dialog_manager.dialog_data["publication_text"]

                # Получаем данные выбранного изображения
                image_url, image_content, image_filename = await self._get_selected_image_data(dialog_manager)

                # Создаем публикацию на модерации
                publication_data = await self.kontur_content_client.create_publication(
                    state.organization_id,
                    category_id,
                    state.account_id,
                    text_reference,
                    name,
                    text,
                    tags,
                    "moderation",
                    image_url=image_url,
                    image_content=image_content,
                    image_filename=image_filename,
                )

                # Если выбраны социальные сети, обновляем публикацию
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                if selected_networks:
                    tg_source = selected_networks.get("telegram_checkbox", False)
                    vk_source = selected_networks.get("vkontakte_checkbox", False)

                    await self.kontur_content_client.change_publication(
                        publication_id=publication_data["publication_id"],
                        tg_source=tg_source,
                        vk_source=vk_source,
                    )

                self.logger.info(
                    "Отправлено на модерацию",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "publication_id": publication_data["publication_id"],
                        "selected_image_index": dialog_manager.dialog_data.get("current_image_index", 0),
                    }
                )

                await callback.answer("💾 Отправлено на модерацию!", show_alert=True)

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
                # Инициализируем словарь выбранных соцсетей если его нет
                if "selected_social_networks" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["selected_social_networks"] = {}

                network_id = checkbox.widget_id
                is_checked = checkbox.is_checked()

                # Сохраняем состояние чекбокса
                dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

                self.logger.info(
                    "Социальная сеть переключена",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "network": network_id,
                        "selected": is_checked,
                        "all_selected": dialog_manager.dialog_data["selected_social_networks"]
                    }
                )

                await callback.answer()
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
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
                # Переходим к выбору социальных сетей
                await dialog_manager.switch_to(model.GeneratePublicationStates.social_network_select)
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при переходе к выбору соцсетей", show_alert=True)
                raise

    async def handle_publish_with_selected_networks(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_publish_with_selected_networks",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Проверяем, что выбрана хотя бы одна соцсеть
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                if not has_selected_networks:
                    await callback.answer(
                        "⚠️ Выберите хотя бы одну социальную сеть для публикации",
                        show_alert=True
                    )
                    return

                await self._publish_immediately(callback, dialog_manager)
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при публикации", show_alert=True)
                raise

    async def _publish_immediately(
            self,
            callback: CallbackQuery,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService._publish_immediately",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await callback.answer()
                loading_message = await callback.message.answer("🚀 Публикую пост...")

                state = await self._get_state(dialog_manager)

                category_id = dialog_manager.dialog_data["category_id"]
                text_reference = dialog_manager.dialog_data["input_text"]
                tags = dialog_manager.dialog_data["publication_tags"]
                name = dialog_manager.dialog_data["publication_name"]
                text = dialog_manager.dialog_data["publication_text"]

                # Получаем данные выбранного изображения
                image_url, image_content, image_filename = await self._get_selected_image_data(dialog_manager)

                # Создаем публикацию со статусом "published"
                publication_data = await self.kontur_content_client.create_publication(
                    state.organization_id,
                    category_id,
                    state.account_id,
                    text_reference,
                    name,
                    text,
                    tags,
                    "published",  # Статус published для немедленной публикации
                    image_url=image_url,
                    image_content=image_content,
                    image_filename=image_filename,
                )

                # Обновляем публикацию с выбранными социальными сетями
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                tg_source = selected_networks.get("telegram_checkbox", False)
                vk_source = selected_networks.get("vkontakte_checkbox", False)

                await self.kontur_content_client.change_publication(
                    publication_id=publication_data["publication_id"],
                    tg_source=tg_source,
                    vk_source=vk_source,
                )

                # Формируем сообщение о публикации
                published_networks = []
                if tg_source:
                    published_networks.append("📺 Telegram")
                if vk_source:
                    published_networks.append("🔗 VKontakte")

                networks_text = ", ".join(published_networks)

                self.logger.info(
                    "Публикация опубликована",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "publication_id": publication_data["publication_id"],
                        "selected_image_index": dialog_manager.dialog_data.get("current_image_index", 0),
                        "tg_source": tg_source,
                        "vk_source": vk_source,
                    }
                )

                await loading_message.edit_text(
                    f"🚀 Публикация успешно опубликована!\n\n"
                    f"📋 Опубликовано в: {networks_text}"
                )

                await asyncio.sleep(3)
                try:
                    await loading_message.delete()
                except:
                    pass

                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.get_social_network_select_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Получаем подключенные социальные сети для организации
                social_networks = await self.kontur_content_client.get_social_networks_by_organization(
                    organization_id=state.organization_id
                )

                # Проверяем подключенные сети
                telegram_connected = self._is_network_connected(social_networks, "telegram")
                vkontakte_connected = self._is_network_connected(social_networks, "vkontakte")

                # Получаем текущие выбранные сети
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                data = {
                    "telegram_connected": telegram_connected,
                    "vkontakte_connected": vkontakte_connected,
                    "all_networks_connected": telegram_connected and vkontakte_connected,
                    "no_connected_networks": not telegram_connected and not vkontakte_connected,
                    "has_available_networks": telegram_connected or vkontakte_connected,
                    "has_selected_networks": has_selected_networks,
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    def _is_network_connected(self, social_networks: dict, network_type: str) -> bool:
        if not social_networks:
            return False
        return network_type in social_networks and len(social_networks[network_type]) > 0

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
                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_categories_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.get_categories_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                # Получаем категории организации
                categories = await self.kontur_content_client.get_categories_by_organization(
                    employee.organization_id
                )

                # Форматируем для отображения
                categories_data = []
                for category in categories:
                    categories_data.append({
                        "id": category.id,
                        "name": category.name,
                        "text_style": category.prompt_for_text_style,
                        "image_style": category.prompt_for_image_style,
                    })

                data = {
                    "categories": categories_data,
                    "has_categories": len(categories_data) > 0,
                }

                self.logger.info(
                    "Категории загружены",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: self._get_chat_id(dialog_manager),
                        "categories_count": len(categories_data),
                    }
                )

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def get_input_text_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "category_name": dialog_manager.dialog_data.get("category_name", ""),
            "input_text": dialog_manager.dialog_data.get("input_text", ""),
            "has_input_text": dialog_manager.dialog_data.get("has_input_text", False),
            # Text input error flags
            "has_void_input_text": dialog_manager.dialog_data.get("has_void_input_text", False),
            "has_small_input_text": dialog_manager.dialog_data.get("has_small_input_text", False),
            "has_big_input_text": dialog_manager.dialog_data.get("has_big_input_text", False),
            # Voice input error flags
            "has_invalid_voice_type": dialog_manager.dialog_data.get("has_invalid_voice_type", False),
            "has_long_voice_duration": dialog_manager.dialog_data.get("has_long_voice_duration", False),
            "has_voice_recognition_error": dialog_manager.dialog_data.get("has_voice_recognition_error", False),
            "has_empty_voice_text": dialog_manager.dialog_data.get("has_empty_voice_text", False),
        }

    async def get_preview_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.get_preview_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                tags = dialog_manager.dialog_data.get("publication_tags", [])
                name = dialog_manager.dialog_data.get("publication_name", "")
                text = dialog_manager.dialog_data.get("publication_text", "")

                # Проверяем наличие изображения
                has_image = False
                preview_image_media = None
                has_multiple_images = False
                current_image_index = 0
                total_images = 0

                # Приоритет: пользовательское изображение > сгенерированное
                if dialog_manager.dialog_data.get("custom_image_file_id"):
                    # Пользовательское изображение
                    has_image = True
                    from aiogram_dialog.api.entities import MediaAttachment, MediaId

                    file_id = dialog_manager.dialog_data["custom_image_file_id"]
                    preview_image_media = MediaAttachment(
                        file_id=MediaId(file_id),
                        type=ContentType.PHOTO
                    )
                elif dialog_manager.dialog_data.get("publication_images_url"):
                    # Сгенерированные изображения
                    has_image = True
                    from aiogram_dialog.api.entities import MediaAttachment

                    images_url = dialog_manager.dialog_data["publication_images_url"]
                    current_image_index = dialog_manager.dialog_data.get("current_image_index", 0)
                    total_images = len(images_url)
                    has_multiple_images = total_images > 1

                    # Показываем текущее изображение
                    if current_image_index < len(images_url):
                        preview_image_media = MediaAttachment(
                            url=images_url[current_image_index],
                            type=ContentType.PHOTO
                        )

                # Проверяем требования модерации
                requires_moderation = employee.required_moderation
                can_publish_directly = not requires_moderation

                data = {
                    "category_name": dialog_manager.dialog_data.get("category_name", ""),
                    "publication_name": name,
                    "publication_text": text,
                    "has_tags": bool(tags),
                    "publication_tags": ", ".join(tags) if tags else "",
                    "has_scheduled_time": False,
                    "publish_time": "",
                    "has_image": has_image,
                    "preview_image_media": preview_image_media,
                    "has_multiple_images": has_multiple_images,
                    "current_image_index": current_image_index + 1,  # Показываем пользователю с 1
                    "total_images": total_images,
                    "requires_moderation": requires_moderation,
                    "can_publish_directly": can_publish_directly,
                    "is_custom_image": dialog_manager.dialog_data.get("is_custom_image", False),
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def _get_current_image_data(self, dialog_manager: DialogManager) -> tuple[bytes, str] | None:
        """Получает данные текущего изображения для передачи в API"""
        try:
            # Проверяем пользовательское изображение
            if dialog_manager.dialog_data.get("custom_image_file_id"):
                file_id = dialog_manager.dialog_data["custom_image_file_id"]
                image_content = await self.bot.download(file_id)
                return image_content.read(), f"{file_id}.jpg"

            # Проверяем сгенерированное изображение
            elif dialog_manager.dialog_data.get("publication_images_url"):
                images_url = dialog_manager.dialog_data["publication_images_url"]
                current_index = dialog_manager.dialog_data.get("current_image_index", 0)

                if current_index < len(images_url):
                    current_url = images_url[current_index]
                    image_content, content_type = await self.download_image(current_url)
                    filename = f"generated_image_{current_index}.jpg"
                    return image_content, filename

            return None
        except Exception as err:
            self.logger.error(f"Ошибка получения данных изображения: {err}")
            return None

    async def get_edit_title_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "publication_name": dialog_manager.dialog_data.get("publication_name", ""),
            # Error flags
            "has_void_title": dialog_manager.dialog_data.get("has_void_title", False),
            "has_big_title": dialog_manager.dialog_data.get("has_big_title", False),
        }

    async def get_edit_tags_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        tags = dialog_manager.dialog_data.get("publication_tags", [])
        return {
            "publication_tags": ", ".join(tags) if tags else "Нет тегов",
            # Error flags
            "has_too_many_tags": dialog_manager.dialog_data.get("has_too_many_tags", False),
        }

    async def get_edit_content_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "publication_text": dialog_manager.dialog_data.get("publication_text", ""),
            # Error flags
            "has_void_content": dialog_manager.dialog_data.get("has_void_content", False),
            "has_small_content": dialog_manager.dialog_data.get("has_small_content", False),
            "has_big_content": dialog_manager.dialog_data.get("has_big_content", False),
        }

    async def get_regenerate_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "has_regenerate_prompt": dialog_manager.dialog_data.get("regenerate_prompt", "") != "",
            "regenerate_prompt": dialog_manager.dialog_data.get("regenerate_prompt", ""),
            # Error flags
            "has_void_regenerate_prompt": dialog_manager.dialog_data.get("has_void_regenerate_prompt", False),
            "has_small_regenerate_prompt": dialog_manager.dialog_data.get("has_small_regenerate_prompt", False),
            "has_big_regenerate_prompt": dialog_manager.dialog_data.get("has_big_regenerate_prompt", False),
            "has_regenerate_api_error": dialog_manager.dialog_data.get("has_regenerate_api_error", False),
        }

    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "has_image": dialog_manager.dialog_data.get("has_image", False),
            "is_custom_image": dialog_manager.dialog_data.get("is_custom_image", False),
        }

    async def get_image_prompt_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "has_image_prompt": dialog_manager.dialog_data.get("image_prompt", "") != "",
            "image_prompt": dialog_manager.dialog_data.get("image_prompt", ""),
            # Error flags
            "has_void_image_prompt": dialog_manager.dialog_data.get("has_void_image_prompt", False),
            "has_small_image_prompt": dialog_manager.dialog_data.get("has_small_image_prompt", False),
            "has_big_image_prompt": dialog_manager.dialog_data.get("has_big_image_prompt", False),
            "has_image_generation_error": dialog_manager.dialog_data.get("has_image_generation_error", False),
        }

    async def get_upload_image_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            # Error flags
            "has_invalid_image_type": dialog_manager.dialog_data.get("has_invalid_image_type", False),
            "has_big_image_size": dialog_manager.dialog_data.get("has_big_image_size", False),
            "has_image_processing_error": dialog_manager.dialog_data.get("has_image_processing_error", False),
        }

    async def _convert_voice_to_text(self, organization_id: int, voice_data: io.BytesIO) -> str:
        text = await self.kontur_content_client.transcribe_audio(
            organization_id,
            audio_content=voice_data.read(),
            audio_filename="audio.mp3",
        )
        return text

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        chat_id = self._get_chat_id(dialog_manager)
        return await self._get_state_by_chat_id(chat_id)

    async def _get_state_by_chat_id(self, chat_id: int) -> model.UserState:
        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]

    def _get_chat_id(self, dialog_manager: DialogManager) -> int:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            return dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            return dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

    async def _get_selected_image_data(self, dialog_manager: DialogManager) -> tuple[
        str | None, bytes | None, str | None]:
        """Получает данные выбранного изображения для сохранения"""
        # Пользовательское изображение
        if dialog_manager.dialog_data.get("custom_image_file_id"):
            file_id = dialog_manager.dialog_data["custom_image_file_id"]
            image_content = await self.bot.download(file_id)
            return None, image_content.read(), f"{file_id}.jpg"

        # Сгенерированное изображение
        elif dialog_manager.dialog_data.get("publication_images_url"):
            images_url = dialog_manager.dialog_data["publication_images_url"]
            current_index = dialog_manager.dialog_data.get("current_image_index", 0)

            if current_index < len(images_url):
                selected_url = images_url[current_index]
                return selected_url, None, None

        return None, None, None

    async def download_image(self, image_url: str) -> tuple[bytes, str]:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                response.raise_for_status()
                content = await response.read()
                content_type = response.headers.get('content-type', 'image/png')
                return content, content_type

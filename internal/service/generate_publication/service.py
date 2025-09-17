import io
import asyncio
from typing import Any
from aiogram_dialog.widgets.input import MessageInput

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.entities import MediaAttachment, MediaId
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
            kontur_publication_client: interface.IKonturPublicationClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client
        self.kontur_organization_client = kontur_organization_client
        self.kontur_publication_client = kontur_publication_client

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
                categories = await self.kontur_publication_client.get_categories_by_organization(
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
                category = await self.kontur_publication_client.get_category_by_id(
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
                text = text.strip()

                if not text:
                    await message.answer("❌ Текст не может быть пустым. Попробуйте снова.")
                    return

                if len(text) < 10:
                    await message.answer("❌ Слишком короткое описание. Напишите подробнее.")
                    return

                if len(text) > 2000:
                    await message.answer("❌ Слишком длинное описание (макс. 2000 символов).")
                    return

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

                # Обновляем окно
                await dialog_manager.update(dialog_manager.dialog_data)

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
                if message.content_type not in [ContentType.VOICE, ContentType.AUDIO]:
                    return

                await message.answer("🎤 Обрабатываю голосовое сообщение...")

                # Загружаем файл
                if message.voice:
                    file_id = message.voice.file_id
                    duration = message.voice.duration
                else:
                    file_id = message.audio.file_id
                    duration = message.audio.duration

                if duration > 300:  # 5 минут макс
                    await message.answer("❌ Голосовое сообщение слишком длинное (макс. 5 минут)")
                    return

                file = await self.bot.get_file(file_id)
                file_data = await self.bot.download_file(file.file_path)
                file_data = io.BytesIO(file_data.read())

                text = await self._convert_voice_to_text(file_data)

                if not text:
                    await message.answer(
                        "❌ Не удалось распознать голосовое сообщение. "
                        "Попробуйте еще раз или введите текст."
                    )
                    return

                # Сохраняем распознанный текст
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

                # Обновляем окно
                await dialog_manager.update(dialog_manager.dialog_data)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка обработки голосового сообщения")
                raise

    async def handle_choose_with_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_choose_with_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.dialog_data["need_image"] = True
                dialog_manager.dialog_data["image_status"] = "waiting"

                self.logger.info(
                    "Выбрана генерация с изображением",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )

                await dialog_manager.switch_to(model.GeneratePublicationStates.image_generation)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_choose_text_only(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_choose_text_only",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.dialog_data["need_image"] = False

                # Запускаем генерацию текста публикации
                await self._generate_publication_text(callback, dialog_manager)

                # Переходим к предпросмотру
                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_auto_generate_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_auto_generate_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.dialog_data["image_status"] = "generating"
                await dialog_manager.update(dialog_manager.dialog_data)

                await callback.answer("🎨 Начинаю генерацию изображения...")

                state = await self._get_state(dialog_manager)
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                # Сначала создаем публикацию
                if "publication_id" not in dialog_manager.dialog_data:
                    await self._generate_publication_text(callback, dialog_manager)

                publication_id = dialog_manager.dialog_data["publication_id"]

                # Генерируем изображение на основе текста
                image_data = await self.kontur_publication_client.regenerate_publication_image(
                    publication_id=publication_id,
                    prompt=None  # Используем автоматическую генерацию
                )

                # Сохраняем изображение
                dialog_manager.dialog_data["has_image"] = True
                dialog_manager.dialog_data["image_data"] = image_data
                dialog_manager.dialog_data["image_status"] = "generated"

                self.logger.info(
                    "Изображение сгенерировано автоматически",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "publication_id": publication_id,
                    }
                )

                await dialog_manager.update(dialog_manager.dialog_data)
                await callback.answer("✅ Изображение успешно сгенерировано!", show_alert=True)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                dialog_manager.dialog_data["image_status"] = "waiting"
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка генерации изображения", show_alert=True)
                raise

    async def handle_request_custom_prompt(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_request_custom_prompt",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.dialog_data["waiting_custom_prompt"] = True
                await dialog_manager.update(dialog_manager.dialog_data)

                await callback.answer("✏️ Введите описание для генерации изображения")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_custom_prompt_image(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            prompt: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_custom_prompt_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Проверяем, что мы действительно ждем промпт
                if not dialog_manager.dialog_data.get("waiting_custom_prompt", False):
                    await message.answer("❌ Сейчас не ожидается ввод описания для изображения")
                    return

                prompt = prompt.strip()

                if not prompt or len(prompt) < 5:
                    await message.answer("❌ Описание слишком короткое. Опишите подробнее.")
                    return

                dialog_manager.dialog_data["waiting_custom_prompt"] = False
                dialog_manager.dialog_data["image_status"] = "generating"
                await dialog_manager.update(dialog_manager.dialog_data)

                await message.answer("🎨 Генерирую изображение по вашему описанию...")

                # Создаем публикацию если еще не создана
                if "publication_id" not in dialog_manager.dialog_data:
                    await self._generate_publication_text_internal(message.chat.id, dialog_manager)

                publication_id = dialog_manager.dialog_data["publication_id"]

                # Генерируем изображение по промпту
                image_data = await self.kontur_publication_client.regenerate_publication_image(
                    publication_id=publication_id,
                    prompt=prompt
                )

                dialog_manager.dialog_data["has_image"] = True
                dialog_manager.dialog_data["image_data"] = image_data
                dialog_manager.dialog_data["image_status"] = "generated"
                dialog_manager.dialog_data["custom_image_prompt"] = prompt

                self.logger.info(
                    "Изображение сгенерировано по промпту",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "publication_id": publication_id,
                        "prompt_length": len(prompt),
                    }
                )

                await message.answer("✅ Изображение успешно сгенерировано!")
                await dialog_manager.update(dialog_manager.dialog_data)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                dialog_manager.dialog_data["image_status"] = "waiting"
                dialog_manager.dialog_data["waiting_custom_prompt"] = False
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка генерации изображения")
                raise

    async def handle_request_upload_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_request_upload_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.dialog_data["waiting_upload"] = True
                await dialog_manager.update(dialog_manager.dialog_data)

                await callback.answer("📤 Отправьте изображение для публикации")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_upload_image(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_upload_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                if not message.photo:
                    return

                # Проверяем, что мы действительно ждем загрузку
                if not dialog_manager.dialog_data.get("waiting_upload", False):
                    # Игнорируем фото, если не в режиме загрузки
                    return

                dialog_manager.dialog_data["waiting_upload"] = False
                await message.answer("📥 Загружаю изображение...")

                # Получаем файл максимального размера
                photo = message.photo[-1]
                file = await self.bot.get_file(photo.file_id)
                file_data = await self.bot.download_file(file.file_path)

                # Создаем публикацию если еще не создана
                if "publication_id" not in dialog_manager.dialog_data:
                    await self._generate_publication_text_internal(message.chat.id, dialog_manager)

                publication_id = dialog_manager.dialog_data["publication_id"]

                # TODO: Загружаем изображение в публикацию через API
                # await self.kontur_publication_client.upload_publication_image(
                #     publication_id=publication_id,
                #     image=file_data
                # )

                dialog_manager.dialog_data["has_image"] = True
                dialog_manager.dialog_data["uploaded_photo_id"] = photo.file_id
                dialog_manager.dialog_data["image_status"] = "uploaded"

                self.logger.info(
                    "Изображение загружено",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "publication_id": publication_id,
                        "file_size": photo.file_size,
                    }
                )

                await message.answer("✅ Изображение успешно загружено!")
                await dialog_manager.update(dialog_manager.dialog_data)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                dialog_manager.dialog_data["waiting_upload"] = False
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка загрузки изображения")
                raise

    async def handle_regenerate_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_regenerate_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.dialog_data["image_status"] = "generating"
                await dialog_manager.update(dialog_manager.dialog_data)

                await callback.answer("🔄 Перегенерирую изображение...")

                publication_id = dialog_manager.dialog_data["publication_id"]

                # Используем предыдущий промпт если был
                prompt = dialog_manager.dialog_data.get("custom_image_prompt")

                image_data = await self.kontur_publication_client.regenerate_publication_image(
                    publication_id=publication_id,
                    prompt=prompt
                )

                dialog_manager.dialog_data["image_data"] = image_data
                dialog_manager.dialog_data["image_status"] = "generated"

                await dialog_manager.update(dialog_manager.dialog_data)
                await callback.answer("✅ Изображение перегенерировано!", show_alert=True)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                dialog_manager.dialog_data["image_status"] = "generated"
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка перегенерации", show_alert=True)
                raise

    async def handle_delete_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_delete_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                publication_id = dialog_manager.dialog_data.get("publication_id")

                if publication_id:
                    await self.kontur_publication_client.delete_publication_image(publication_id)

                dialog_manager.dialog_data["has_image"] = False
                dialog_manager.dialog_data["image_status"] = "waiting"
                dialog_manager.dialog_data.pop("image_data", None)
                dialog_manager.dialog_data.pop("uploaded_photo_id", None)

                await dialog_manager.update(dialog_manager.dialog_data)
                await callback.answer("🗑 Изображение удалено")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_edit_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_edit_text",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # TODO: Реализовать редактирование текста
                await callback.answer("🚧 Функция редактирования в разработке", show_alert=True)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_edit_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_edit_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.switch_to(model.GeneratePublicationStates.image_generation)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_schedule_time(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_schedule_time",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # TODO: Реализовать планирование времени публикации
                await callback.answer("🚧 Планирование времени в разработке", show_alert=True)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
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
                publication_id = dialog_manager.dialog_data["publication_id"]

                # Публикация уже создана как черновик по умолчанию
                self.logger.info(
                    "Публикация сохранена в черновики",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "publication_id": publication_id,
                    }
                )

                await callback.answer("💾 Сохранено в черновики!", show_alert=True)

                # Возвращаемся в меню контента
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
                publication_id = dialog_manager.dialog_data["publication_id"]

                await self.kontur_publication_client.send_publication_to_moderation(publication_id)

                self.logger.info(
                    "Публикация отправлена на модерацию",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "publication_id": publication_id,
                    }
                )

                await callback.answer("📤 Отправлено на модерацию!", show_alert=True)

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

    async def handle_publish(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_publish",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                publication_id = dialog_manager.dialog_data["publication_id"]

                # Получаем выбранные платформы из dialog_data
                selected_platforms = []
                platforms_data = dialog_manager.dialog_data.get("selected_platforms", {})

                for platform in ["telegram", "instagram", "vkontakte", "youtube"]:
                    if platforms_data.get(f"platform_{platform}", False):
                        selected_platforms.append(platform)

                if not selected_platforms:
                    await callback.answer("⚠️ Выберите хотя бы одну платформу", show_alert=True)
                    return

                # Публикуем на выбранные платформы
                await self.kontur_publication_client.publish_publication(
                    publication_id,
                    platforms=selected_platforms
                )

                self.logger.info(
                    "Публикация опубликована",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "publication_id": publication_id,
                        "platforms": selected_platforms,
                    }
                )

                await callback.answer(
                    f"🚀 Опубликовано на {len(selected_platforms)} платформах!",
                    show_alert=True
                )

                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка публикации", show_alert=True)
                raise

    async def handle_refresh_categories(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_refresh_categories",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.update(dialog_manager.dialog_data)
                await callback.answer("🔄 Список обновлен")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_platform_toggle(
            self,
            callback: CallbackQuery,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка переключения платформ"""
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.handle_platform_toggle",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Инициализируем словарь выбранных платформ если его нет
                if "selected_platforms" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["selected_platforms"] = {}

                platform_id = checkbox.widget_id
                is_checked = checkbox.is_checked()

                dialog_manager.dialog_data["selected_platforms"][platform_id] = is_checked

                self.logger.info(
                    "Платформа переключена",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "platform": platform_id,
                        "selected": is_checked,
                    }
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
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
                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    # Методы для получения данных окон

    async def get_input_text_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "category_name": dialog_manager.dialog_data.get("category_name", ""),
            "input_text": dialog_manager.dialog_data.get("input_text", ""),
            "has_input_text": dialog_manager.dialog_data.get("has_input_text", False),
        }

    async def get_image_option_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "category_name": dialog_manager.dialog_data.get("category_name", ""),
        }

    async def get_image_generation_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        image_status = dialog_manager.dialog_data.get("image_status", "waiting")
        has_image = dialog_manager.dialog_data.get("has_image", False)

        # Создаем медиа объект для отображения изображения
        image_media = None
        if has_image:
            if "uploaded_photo_id" in dialog_manager.dialog_data:
                # Используем загруженное фото
                image_media = MediaAttachment(
                    ContentType.PHOTO,
                    file_id=MediaId(dialog_manager.dialog_data["uploaded_photo_id"])
                )
            elif "image_data" in dialog_manager.dialog_data:
                # Используем сгенерированное изображение
                # TODO: Конвертировать BytesIO в MediaAttachment
                pass

        # Определяем, когда показывать кнопки генерации
        show_generation_buttons = image_status == "waiting" and not has_image

        return {
            "category_name": dialog_manager.dialog_data.get("category_name", ""),
            "image_status": image_status,
            "has_image": has_image,
            "image_media": image_media,
            "show_generation_buttons": show_generation_buttons,
            "can_regenerate": image_status == "generated",
            "can_continue": has_image or dialog_manager.dialog_data.get("need_image") == False,
            "not_generating": image_status != "generating",
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

                publication_id = dialog_manager.dialog_data.get("publication_id")
                publication = None

                if publication_id:
                    publication = await self.kontur_publication_client.get_publication_by_id(
                        publication_id
                    )

                # Форматируем теги
                tags_list = ""
                has_tags = False
                if publication and publication.tags:
                    tags_list = " ".join([f"#{tag}" for tag in publication.tags])
                    has_tags = True

                # Проверяем требования модерации
                requires_moderation = employee.required_moderation
                can_publish_directly = not requires_moderation

                # Создаем медиа объект для превью
                preview_image_media = None
                if dialog_manager.dialog_data.get("has_image"):
                    if "uploaded_photo_id" in dialog_manager.dialog_data:
                        preview_image_media = MediaAttachment(
                            ContentType.PHOTO,
                            file_id=MediaId(dialog_manager.dialog_data["uploaded_photo_id"])
                        )

                data = {
                    "category_name": dialog_manager.dialog_data.get("category_name", ""),
                    "publication_title": publication.name if publication else "Новая публикация",
                    "publication_text": publication.text if publication else dialog_manager.dialog_data.get(
                        "generated_text", ""),
                    "has_tags": has_tags,
                    "tags_list": tags_list,
                    "has_scheduled_time": False,
                    "publish_time": "",
                    "has_image": dialog_manager.dialog_data.get("has_image", False),
                    "preview_image_media": preview_image_media,
                    "requires_moderation": requires_moderation,
                    "can_publish_directly": can_publish_directly,
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def get_publish_locations_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Получение данных для окна выбора платформ"""
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService.get_publish_locations_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                # TODO: Получить реальные подключенные платформы из API организации
                # organization_platforms = await self.kontur_organization_client.get_connected_platforms(
                #     employee.organization_id
                # )

                # Пока используем статичные данные
                platforms_data = dialog_manager.dialog_data.get("selected_platforms", {})
                selected_count = sum(1 for selected in platforms_data.values() if selected)

                data = {
                    "telegram_available": True,
                    "instagram_available": True,
                    "vkontakte_available": True,
                    "youtube_available": False,  # Только для видео контента
                    "has_selected_platforms": selected_count > 0,
                    "selected_count": selected_count,
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    # Вспомогательные методы

    async def _generate_publication_text(
            self,
            callback: CallbackQuery,
            dialog_manager: DialogManager
    ) -> None:
        await callback.answer("⏳ Генерирую текст публикации...")

        chat_id = callback.message.chat.id
        await self._generate_publication_text_internal(chat_id, dialog_manager)

    async def _generate_publication_text_internal(
            self,
            chat_id: int,
            dialog_manager: DialogManager
    ) -> None:
        state = await self._get_state_by_chat_id(chat_id)
        employee = await self.kontur_employee_client.get_employee_by_account_id(
            state.account_id
        )

        category_id = dialog_manager.dialog_data["category_id"]
        input_text = dialog_manager.dialog_data["input_text"]
        need_images = dialog_manager.dialog_data.get("need_image", False)

        # Генерируем публикацию через API
        publication = await self.kontur_publication_client.generate_publication(
            organization_id=employee.organization_id,
            category_id=category_id,
            creator_id=state.account_id,
            need_images=need_images,
            text_reference=input_text,
        )

        dialog_manager.dialog_data["publication_id"] = publication.id
        dialog_manager.dialog_data["generated_text"] = publication.text
        dialog_manager.dialog_data["publication_title"] = publication.name

        self.logger.info(
            "Текст публикации сгенерирован",
            {
                common.TELEGRAM_CHAT_ID_KEY: chat_id,
                "publication_id": publication.id,
                "text_length": len(publication.text),
            }
        )

    async def _convert_voice_to_text(self, voice_data: io.BytesIO) -> str:
        """Конвертация голоса в текст (заглушка)"""
        # TODO: Интеграция с реальным STT сервисом (Whisper API, Yandex SpeechKit и т.д.)
        # Пока возвращаем тестовый текст
        await asyncio.sleep(2)  # Имитация обработки
        return "Это тестовый текст, распознанный из голосового сообщения. В реальной системе здесь будет результат распознавания речи."

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        """Получить состояние текущего пользователя"""
        chat_id = self._get_chat_id(dialog_manager)
        return await self._get_state_by_chat_id(chat_id)

    async def _get_state_by_chat_id(self, chat_id: int) -> model.UserState:
        """Получить состояние по chat_id"""
        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]

    def _get_chat_id(self, dialog_manager: DialogManager) -> int:
        """Получить chat_id из dialog_manager"""
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            return dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            return dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

import io
import asyncio
from typing import Any

import httpx
from aiogram_dialog.widgets.input import MessageInput

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, StartMode
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
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client
        self.kontur_organization_client = kontur_organization_client
        self.kontur_content_client = kontur_content_client

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
                await message.delete()

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
                loading_message = await callback.message.answer("🔄 Герегенерирую текст, это может занять время...")

                category_id = dialog_manager.dialog_data["category_id"]
                input_text = dialog_manager.dialog_data["input_text"]

                publication_data = await self.kontur_content_client.generate_publication_text(
                    category_id=category_id,
                    text_reference=input_text,
                )

                dialog_manager.dialog_data["publication_tags"] = publication_data["tags"]
                dialog_manager.dialog_data["publication_name"] = publication_data["name"]
                dialog_manager.dialog_data["publication_text"] = publication_data["text"]

                await loading_message.edit_text("✅ Пост успешно сгенерирован!")
                await asyncio.sleep(3)
                try:
                    await loading_message.delete()
                except:
                    pass

                # Переходим к предпросмотру
                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

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
                loading_message = await callback.message.answer(
                    "🔄 Генерирую текст и изображение, это может занять время..."
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
                image_url = await self.kontur_content_client.generate_publication_image(
                    category_id,
                    publication_data["text"],
                    input_text,
                )

                dialog_manager.dialog_data["publication_image_url"] = image_url
                dialog_manager.dialog_data["has_image"] = True
                dialog_manager.dialog_data["is_custom_image"] = False

                await loading_message.edit_text("✅ Публикация успешно создана!")
                await asyncio.sleep(2)
                try:
                    await loading_message.delete()
                except:
                    pass

                # Переходим к предпросмотру
                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при генерации", show_alert=True)
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
                loading_message = await callback.message.answer("🔄 Перегенерирую текст, это может занять время...")

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

                await loading_message.edit_text("✅ Пост успешно сгенерирован!")
                await asyncio.sleep(3)
                try:
                    await loading_message.delete()
                except:
                    pass

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
                if not prompt.strip():
                    await message.answer("❌ Введите указания для перегенерации")
                    return

                loading_message = await message.answer("🔄 Перегенерирую с учетом ваших пожеланий...")

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

                await loading_message.edit_text("✅ Пост успешно сгенерирован!")
                await asyncio.sleep(3)
                try:
                    await loading_message.delete()
                except:
                    pass

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при перегенерации")
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
                new_title = text.strip()

                if not new_title:
                    await message.answer("❌ Название не может быть пустым")
                    return

                if len(new_title) > 200:
                    await message.answer("❌ Слишком длинное название (макс. 200 символов)")
                    return

                dialog_manager.dialog_data["publication_name"] = new_title

                await message.answer("✅ Название обновлено!")
                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

                self.logger.info(
                    "Название публикации изменено",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "new_title": new_title,
                    }
                )

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
                # Парсим теги из строки
                tags_raw = text.strip()
                if not tags_raw:
                    dialog_manager.dialog_data["publication_tags"] = []
                    await message.answer("✅ Теги удалены")
                else:
                    # Разделяем по запятым и очищаем
                    tags = [tag.strip() for tag in tags_raw.split(",")]
                    tags = [tag for tag in tags if tag]  # Убираем пустые

                    if len(tags) > 10:
                        await message.answer("❌ Слишком много тегов (макс. 10)")
                        return

                    dialog_manager.dialog_data["publication_tags"] = tags
                    await message.answer(f"✅ Сохранено {len(tags)} тегов")

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

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
                new_text = text.strip()

                if not new_text:
                    await message.answer("❌ Текст не может быть пустым")
                    return

                if len(new_text) > 4000:
                    await message.answer("❌ Слишком длинный текст (макс. 4000 символов)")
                    return

                if len(new_text) < 50:
                    await message.answer("⚠️ Текст слишком короткий. Минимум 50 символов.")
                    return

                dialog_manager.dialog_data["publication_text"] = new_text

                await message.answer("✅ Текст обновлен!")
                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

                self.logger.info(
                    "Текст публикации изменен",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "text_length": len(new_text),
                    }
                )

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
                loading_message = await callback.message.answer("🔄 Генерирую изображение, это может занять время...")

                category_id = dialog_manager.dialog_data["category_id"]
                publication_text = dialog_manager.dialog_data["publication_text"]
                text_reference = dialog_manager.dialog_data["input_text"]

                # Генерация через API
                image_url = await self.kontur_content_client.generate_publication_image(
                    category_id=category_id,
                    publication_text=publication_text,
                    text_reference=text_reference,
                    prompt=None
                )

                dialog_manager.dialog_data["publication_image_url"] = image_url
                dialog_manager.dialog_data["has_image"] = True

                await loading_message.edit_text("✅ Текст успешно обновлен!")
                await asyncio.sleep(3)
                try:
                    await loading_message.delete()
                except:
                    pass

                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

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
                if not prompt.strip():
                    await message.answer("❌ Введите описание изображения")
                    return

                loading_message = await message.answer("🔄 Перегенерирую с учетом ваших пожеланий...")

                category_id = dialog_manager.dialog_data["category_id"]
                publication_text = dialog_manager.dialog_data["publication_text"]
                text_reference = dialog_manager.dialog_data["input_text"]

                image_url = await self.kontur_content_client.generate_publication_image(
                    category_id=category_id,
                    publication_text=publication_text,
                    text_reference=text_reference,
                    prompt=prompt
                )

                dialog_manager.dialog_data["publication_image_url"] = image_url
                dialog_manager.dialog_data["has_image"] = True

                await loading_message.edit_text("✅ Изображение успешно сгенерирован!")
                await asyncio.sleep(3)
                try:
                    await loading_message.delete()
                except:
                    pass
                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при генерации изображения")
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
                    await message.answer("❌ Пожалуйста, отправьте изображение")
                    return

                # Проверяем размер файла (если доступно)
                if message.photo:
                    # Берем фото с наибольшим разрешением
                    photo = message.photo[-1]

                    # Проверяем размер (если доступно)
                    if hasattr(photo, 'file_size') and photo.file_size:
                        if photo.file_size > 10 * 1024 * 1024:  # 10 МБ
                            await message.answer("❌ Файл слишком большой (макс. 10 МБ)")
                            return

                    await message.answer("📸 Загружаю изображение...")

                    # Сохраняем file_id для дальнейшего использования
                    dialog_manager.dialog_data["custom_image_file_id"] = photo.file_id
                    dialog_manager.dialog_data["has_image"] = True
                    dialog_manager.dialog_data["is_custom_image"] = True

                    # Удаляем сгенерированное изображение если было
                    dialog_manager.dialog_data.pop("publication_image_url", None)

                    self.logger.info(
                        "Пользовательское изображение загружено",
                        {
                            common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                            "file_id": photo.file_id,
                            "file_size": getattr(photo, 'file_size', 'unknown'),
                        }
                    )

                    await message.answer("✅ Изображение загружено!")
                    await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

                    span.set_status(Status(StatusCode.OK))
                else:
                    await message.answer("❌ Не удалось получить изображение")

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при загрузке изображения")
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
                dialog_manager.dialog_data.pop("publication_image_url", None)
                dialog_manager.dialog_data.pop("custom_image_file_id", None)
                dialog_manager.dialog_data.pop("is_custom_image", None)

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

                # Подготавливаем данные об изображении
                image_url = dialog_manager.dialog_data.get("publication_image_url")  # от OpenAI
                image_content = None
                image_filename = None

                # Если есть пользовательское изображение из Telegram
                telegram_file_id = dialog_manager.dialog_data.get("custom_image_file_id")
                if telegram_file_id:
                    file = await self.bot.get_file(telegram_file_id)
                    file_data = await self.bot.download_file(file.file_path)
                    image_content = file_data.read()
                    image_filename = f"user_image_{telegram_file_id[:8]}.jpg"

                    self.logger.info(
                        "Подготовлено пользовательское изображение для публикации",
                        {
                            common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                            "file_id": telegram_file_id,
                            "image_size": len(image_content),
                        }
                    )

                # Вызываем HTTP клиент с подготовленными данными
                await self.kontur_content_client.create_publication(
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

                self.logger.info(
                    "Публикация сохранена в черновики",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "has_generated_image": bool(image_url),
                        "has_user_image": bool(image_content),
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
                state = await self._get_state(dialog_manager)

                category_id = dialog_manager.dialog_data["category_id"]
                text_reference = dialog_manager.dialog_data["input_text"]
                tags = dialog_manager.dialog_data["publication_tags"]
                name = dialog_manager.dialog_data["publication_name"]
                text = dialog_manager.dialog_data["publication_text"]

                # Подготавливаем изображение
                image_url = dialog_manager.dialog_data.get("publication_image_url")
                image_content = None
                image_filename = None

                telegram_file_id = dialog_manager.dialog_data.get("custom_image_file_id")
                if telegram_file_id:
                    file = await self.bot.get_file(telegram_file_id)
                    file_data = await self.bot.download_file(file.file_path)
                    image_content = file_data.read()
                    image_filename = f"user_image_{telegram_file_id[:8]}.jpg"

                    self.logger.info(
                        "Подготовлено пользовательское изображение для модерации",
                        {
                            common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                            "file_id": telegram_file_id,
                            "image_size": len(image_content),
                        }
                    )

                await self.kontur_content_client.create_publication(
                    state.organization_id,
                    category_id,
                    state.account_id,
                    text_reference,
                    name,
                    text,
                    tags,
                    "moderation",  # статус модерации
                    image_url=image_url,
                    image_content=image_content,
                    image_filename=image_filename,
                )

                self.logger.info(
                    "Отправлено на модерацию",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "has_generated_image": bool(image_url),
                        "has_user_image": bool(image_content),
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
                # TODO: Реализовать
                await callback.answer("🚧 Функция в разработке", show_alert=True)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка публикации", show_alert=True)
                raise

    async def handle_platform_toggle(
            self,
            callback: CallbackQuery,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None:
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
                elif dialog_manager.dialog_data.get("publication_image_url"):
                    # Сгенерированное изображение
                    has_image = True
                    from aiogram_dialog.api.entities import MediaAttachment

                    image_url = dialog_manager.dialog_data["publication_image_url"]
                    preview_image_media = MediaAttachment(
                        url=image_url,
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
                    "vkontakte_available": True,
                    "has_selected_platforms": selected_count > 0,
                    "selected_count": selected_count,
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def get_regenerate_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Данные для окна перегенерации с промптом"""
        return {
            "has_regenerate_prompt": dialog_manager.dialog_data.get("regenerate_prompt", "") != "",
            "regenerate_prompt": dialog_manager.dialog_data.get("regenerate_prompt", ""),
        }

    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Данные для меню управления изображением"""
        return {
            "has_image": dialog_manager.dialog_data.get("has_image", False),
            "is_custom_image": dialog_manager.dialog_data.get("is_custom_image", False),
        }

    async def get_image_prompt_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Данные для окна генерации изображения с промптом"""
        return {
            "has_image_prompt": dialog_manager.dialog_data.get("image_prompt", "") != "",
            "image_prompt": dialog_manager.dialog_data.get("image_prompt", ""),
        }

    async def _convert_voice_to_text(self, voice_data: io.BytesIO) -> str:
        text = await self.kontur_content_client.transcribe_audio(
            audio_content=voice_data.read(),
            audio_filename=voice_data.name,
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
        """Получить chat_id из dialog_manager"""
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            return dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            return dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

    async def _download_image_from_url(
            self,
            image_url: str
    ) -> bytes:
        with self.tracer.start_as_current_span(
                "GeneratePublicationDialogService._download_image_from_url",
                kind=SpanKind.CLIENT,
        ) as span:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url)
                    response.raise_for_status()

                span.set_status(Status(StatusCode.OK))
                return response.content

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

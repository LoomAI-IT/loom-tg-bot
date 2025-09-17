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
                category_id = dialog_manager.dialog_data["category_id"]
                input_text = dialog_manager.dialog_data["input_text"]

                publication_data = await self.kontur_publication_client.generate_publication_text(
                    category_id=category_id,
                    text_reference=input_text,
                )

                dialog_manager.dialog_data["publication_tags"] = publication_data["tags"]
                dialog_manager.dialog_data["publication_name"] = publication_data["name"]
                dialog_manager.dialog_data["publication_text"] = publication_data["text"]

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
                "GeneratePublicationDialogService.handle_generate_text",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                category_id = dialog_manager.dialog_data["category_id"]
                input_text = dialog_manager.dialog_data["input_text"]

                publication_data = await self.kontur_publication_client.generate_publication_text(
                    category_id=category_id,
                    text_reference=input_text,
                )

                dialog_manager.dialog_data["publication_tags"] = publication_data["tags"]
                dialog_manager.dialog_data["publication_name"] = publication_data["name"]
                dialog_manager.dialog_data["publication_text"] = publication_data["text"]

                image_url = await self.kontur_publication_client.generate_publication_image(
                    category_id,
                    publication_data["text"],
                    input_text,
                )

                dialog_manager.dialog_data["publication_image_url"] = image_url

                # Переходим к предпросмотру
                await dialog_manager.switch_to(model.GeneratePublicationStates.preview)

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
                # TODO: Реализовать
                await callback.answer("🚧 Функция в разработке", show_alert=True)

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
                state = await self._get_state(dialog_manager)

                category_id = dialog_manager.dialog_data["category_id"]
                text_reference = dialog_manager.dialog_data["input_text"]
                tags = dialog_manager.dialog_data["publication_tags"]
                name = dialog_manager.dialog_data["publication_name"]
                text = dialog_manager.dialog_data["publication_text"]
                image_url = dialog_manager.dialog_data.get("publication_image_url")

                await self.kontur_publication_client.create_publication(
                    state.organization_id,
                    category_id,
                    state.account_id,
                    text_reference,
                    name,
                    text,
                    tags,
                    "draft",
                    image_url,
                )

                self.logger.info(
                    "Публикация сохранена в черновики",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
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
                image_url = dialog_manager.dialog_data.get("publication_image_url")

                await self.kontur_publication_client.create_publication(
                    state.organization_id,
                    category_id,
                    state.account_id,
                    text_reference,
                    name,
                    text,
                    tags,
                    "moderation",
                    image_url,
                )

                self.logger.info(
                    "Отправлено на модерацию",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )

                await callback.answer("💾 Отправлено на модерацию!", show_alert=True)

                # Возвращаемся в меню контента
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

                tags = dialog_manager.dialog_data["publication_tags"]
                name = dialog_manager.dialog_data["publication_name"]
                text = dialog_manager.dialog_data["publication_text"]
                image_url = dialog_manager.dialog_data.get("publication_image_url")

                # Проверяем требования модерации
                requires_moderation = employee.required_moderation
                can_publish_directly = not requires_moderation

                # Нужно реализовать гле-то это
                preview_image_media = None

                data = {
                    "category_name": dialog_manager.dialog_data.get("category_name", ""),
                    "publication_name": name,
                    "publication_text": text,
                    "has_tags": bool(tags),
                    "tags_list": tags,
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

    async def _convert_voice_to_text(self, voice_data: io.BytesIO) -> str:
        """Конвертация голоса в текст (заглушка)"""
        # TODO: Интеграция с реальным STT сервисом (Whisper API, Yandex SpeechKit и т.д.)
        # Пока возвращаем тестовый текст
        await asyncio.sleep(2)  # Имитация обработки
        return "Это тестовый текст, распознанный из голосового сообщения. В реальной системе здесь будет результат распознавания речи."

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

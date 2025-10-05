import asyncio
from typing import Any

from aiogram.enums import ParseMode
from aiogram_dialog.widgets.input import MessageInput

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class ModerationPublicationService(interface.IModerationPublicationService):
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

    async def handle_navigate_publication(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_navigate_publication",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало навигации по публикациям")
                dialog_manager.show_mode = ShowMode.EDIT

                current_index = dialog_manager.dialog_data.get("current_index", 0)
                moderation_list = dialog_manager.dialog_data.get("moderation_list", [])

                # Определяем направление навигации
                if button.widget_id == "prev_publication":
                    self.logger.info("Переход к предыдущей публикации")
                    new_index = max(0, current_index - 1)
                else:  # next_publication
                    self.logger.info("Переход к следующей публикации")
                    new_index = min(len(moderation_list) - 1, current_index + 1)

                if new_index == current_index:
                    self.logger.info("Достигнут край списка")
                    await callback.answer("Это крайняя публикация в списке")
                    return

                # Обновляем индекс
                dialog_manager.dialog_data["current_index"] = new_index

                # Сбрасываем рабочие данные для новой публикации
                dialog_manager.dialog_data.pop("working_publication", None)

                await callback.answer()
                self.logger.info("Навигация завершена")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось переключить публикацию", show_alert=True)
                raise

    async def handle_reject_comment_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            comment: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_reject_comment_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало обработки комментария отклонения")
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                dialog_manager.dialog_data.pop("has_void_reject_comment", None)
                dialog_manager.dialog_data.pop("has_small_reject_comment", None)
                dialog_manager.dialog_data.pop("has_big_reject_comment", None)

                comment = comment.strip()
                if not comment:
                    self.logger.info("Пустой комментарий отклонения")
                    dialog_manager.dialog_data["has_void_reject_comment"] = True
                    return

                if len(comment) < 10:
                    self.logger.info("Слишком короткий комментарий отклонения")
                    dialog_manager.dialog_data["has_small_reject_comment"] = True
                    return

                if len(comment) > 500:
                    self.logger.info("Слишком длинный комментарий отклонения")
                    dialog_manager.dialog_data["has_big_reject_comment"] = True
                    return

                dialog_manager.dialog_data["reject_comment"] = comment

                self.logger.info("Комментарий отклонения сохранен")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_send_rejection(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_send_rejection",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало отклонения публикации")
                dialog_manager.show_mode = ShowMode.EDIT

                state = await self._get_state(dialog_manager)
                original_pub = dialog_manager.dialog_data["original_publication"]
                publication_id = original_pub["id"]
                reject_comment = dialog_manager.dialog_data.get("reject_comment", "Нет комментария")

                # Отклоняем публикацию через API
                await self.loom_content_client.moderate_publication(
                    publication_id=publication_id,
                    moderator_id=state.account_id,
                    moderation_status="rejected",
                    moderation_comment=reject_comment,
                )

                creator_state = await self.state_repo.state_by_account_id(original_pub["creator_id"])
                if creator_state:
                    self.logger.info("Отправка уведомления автору о отклонении")
                    await self.bot.send_message(
                        chat_id=creator_state[0].tg_chat_id,
                        text=f"Ваша публикация была отклонена с комментарием:\n<b>{reject_comment}</b>",
                        parse_mode=ParseMode.HTML,

                    )

                await self._remove_current_publication_from_list(dialog_manager)

                await callback.answer("Публикация отклонена", show_alert=True)

                await dialog_manager.switch_to(model.ModerationPublicationStates.moderation_list)
                self.logger.info("Публикация отклонена успешно")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось отклонить публикацию", show_alert=True)
                raise

    async def handle_regenerate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_regenerate_text",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало перегенерации текста")
                dialog_manager.show_mode = ShowMode.EDIT

                await callback.answer()
                dialog_manager.dialog_data["is_regenerating_text"] = True
                await dialog_manager.show()

                working_pub = dialog_manager.dialog_data["working_publication"]

                # Перегенерация через API
                regenerated_data = await self.loom_content_client.regenerate_publication_text(
                    category_id=working_pub["category_id"],
                    publication_text=working_pub["text"],
                    prompt=None
                )

                # Обновляем данные
                dialog_manager.dialog_data["working_publication"]["text"] = regenerated_data["text"]
                dialog_manager.dialog_data["is_regenerating_text"] = False

                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)
                self.logger.info("Текст перегенерирован")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось перегенерировать текст", show_alert=True)
                raise

    async def handle_regenerate_text_with_prompt(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            prompt: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_regenerate_text_with_prompt",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало перегенерации текста с промптом")
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                dialog_manager.dialog_data.pop("has_void_regenerate_prompt", None)
                dialog_manager.dialog_data.pop("has_small_regenerate_prompt", None)
                dialog_manager.dialog_data.pop("has_big_regenerate_prompt", None)

                prompt = message.html_text.replace('\n', '<br/>')
                if not prompt:
                    self.logger.info("Пустой промпт для перегенерации")
                    dialog_manager.dialog_data["has_void_regenerate_prompt"] = True
                    return

                dialog_manager.dialog_data["is_regenerating_text"] = True
                dialog_manager.dialog_data["has_regenerate_prompt"] = True
                await dialog_manager.show()

                working_pub = dialog_manager.dialog_data["working_publication"]

                # Перегенерация через API
                regenerated_data = await self.loom_content_client.regenerate_publication_text(
                    category_id=working_pub["category_id"],
                    publication_text=working_pub["text"],
                    prompt=prompt
                )

                # Обновляем данные
                dialog_manager.dialog_data["working_publication"]["text"] = regenerated_data["text"]
                dialog_manager.dialog_data["regenerate_prompt"] = prompt
                dialog_manager.dialog_data["is_regenerating_text"] = False
                dialog_manager.dialog_data["has_regenerate_prompt"] = False

                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)

                self.logger.info("Текст перегенерирован с промптом")
                span.set_status(Status(StatusCode.OK))
            except Exception as err:

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
                "ModerationPublicationDialogService.handle_edit_text",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало редактирования текста")
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                dialog_manager.dialog_data.pop("has_void_text", None)
                dialog_manager.dialog_data.pop("has_big_text", None)
                dialog_manager.dialog_data.pop("has_small_text", None)

                new_text = message.html_text.replace('\n', '<br/>')
                if not new_text:
                    self.logger.info("Пустой текст публикации")
                    dialog_manager.dialog_data["has_void_text"] = True
                    return

                if len(new_text) > 4000:
                    self.logger.info("Слишком длинный текст публикации")
                    dialog_manager.dialog_data["has_big_text"] = True
                    return

                if len(new_text) < 50:
                    self.logger.info("Слишком короткий текст публикации")
                    dialog_manager.dialog_data["has_small_text"] = True
                    return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_publication"]["text"] = new_text

                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)
                self.logger.info("Текст отредактирован")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_generate_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_generate_new_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало генерации нового изображения")
                dialog_manager.show_mode = ShowMode.EDIT

                await callback.answer()
                dialog_manager.dialog_data["is_generating_image"] = True
                await dialog_manager.show()

                working_pub = dialog_manager.dialog_data["working_publication"]
                category_id = working_pub["category_id"]
                publication_text = working_pub["text"]

                # Передаем текущее изображение если есть
                current_image_content = None
                current_image_filename = None

                if await self._get_current_image_data_for_moderation(dialog_manager):
                    self.logger.info("Используется текущее изображение для генерации")
                    current_image_content, current_image_filename = await self._get_current_image_data_for_moderation(
                        dialog_manager)

                # Генерация через API - возвращает массив из 3 URL
                images_url = await self.loom_content_client.generate_publication_image(
                    category_id=category_id,
                    publication_text=publication_text,
                    text_reference=publication_text[:200],
                    image_content=current_image_content,
                    image_filename=current_image_filename,
                )

                # Обновляем рабочую версию с множественными изображениями
                dialog_manager.dialog_data["working_publication"]["generated_images_url"] = images_url
                dialog_manager.dialog_data["working_publication"]["has_image"] = True
                dialog_manager.dialog_data["working_publication"]["current_image_index"] = 0
                # Удаляем старые данные изображения
                dialog_manager.dialog_data["working_publication"].pop("custom_image_file_id", None)
                dialog_manager.dialog_data["working_publication"].pop("is_custom_image", None)
                dialog_manager.dialog_data["working_publication"].pop("image_url", None)
                dialog_manager.dialog_data["is_generating_image"] = False

                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)
                self.logger.info("Изображение сгенерировано")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось сгенерировать изображение", show_alert=True)
                raise

    async def handle_generate_image_with_prompt(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            prompt: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_generate_image_with_prompt",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало генерации изображения с промптом")
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                dialog_manager.dialog_data.pop("has_void_image_prompt", None)
                dialog_manager.dialog_data.pop("has_small_image_prompt", None)
                dialog_manager.dialog_data.pop("has_big_image_prompt", None)
                dialog_manager.dialog_data.pop("has_image_generation_error", None)

                prompt = prompt.strip()
                if not prompt:
                    self.logger.info("Пустой промпт для генерации изображения")
                    dialog_manager.dialog_data["has_void_image_prompt"] = True
                    return

                dialog_manager.dialog_data["image_prompt"] = prompt
                dialog_manager.dialog_data["is_generating_image"] = True

                await dialog_manager.show()

                working_pub = dialog_manager.dialog_data["working_publication"]
                category_id = working_pub["category_id"]
                publication_text = working_pub["text"]

                # Передаем текущее изображение если есть
                current_image_content = None
                current_image_filename = None

                if await self._get_current_image_data_for_moderation(dialog_manager):
                    self.logger.info("Используется текущее изображение для генерации")
                    current_image_content, current_image_filename = await self._get_current_image_data_for_moderation(
                        dialog_manager)

                # Генерация с промптом - возвращает массив из 3 URL
                images_url = await self.loom_content_client.generate_publication_image(
                    category_id=category_id,
                    publication_text=publication_text,
                    text_reference=publication_text[:200],
                    prompt=prompt,
                    image_content=current_image_content,
                    image_filename=current_image_filename,
                )

                # Обновляем рабочую версию с множественными изображениями
                dialog_manager.dialog_data["working_publication"]["generated_images_url"] = images_url
                dialog_manager.dialog_data["working_publication"]["has_image"] = True
                dialog_manager.dialog_data["working_publication"]["current_image_index"] = 0
                # Удаляем старые данные изображения
                dialog_manager.dialog_data["working_publication"].pop("custom_image_file_id", None)
                dialog_manager.dialog_data["working_publication"].pop("is_custom_image", None)
                dialog_manager.dialog_data["working_publication"].pop("image_url", None)
                dialog_manager.dialog_data["is_generating_image"] = False

                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)
                self.logger.info("Изображение сгенерировано с промптом")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_image_upload",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало загрузки изображения")
                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                dialog_manager.dialog_data.pop("has_invalid_image_type", None)
                dialog_manager.dialog_data.pop("has_big_image_size", None)

                if message.content_type != ContentType.PHOTO:
                    self.logger.info("Неверный тип файла изображения")
                    dialog_manager.dialog_data["has_invalid_image_type"] = True
                    return

                if message.photo:
                    photo = message.photo[-1]  # Берем наибольшее разрешение

                    # Проверяем размер
                    if hasattr(photo, 'file_size') and photo.file_size:
                        if photo.file_size > 10 * 1024 * 1024:  # 10 МБ
                            self.logger.info("Размер изображения превышает допустимый")
                            dialog_manager.dialog_data["has_big_image_size"] = True
                            return

                    # Обновляем рабочую версию
                    dialog_manager.dialog_data["working_publication"]["custom_image_file_id"] = photo.file_id
                    dialog_manager.dialog_data["working_publication"]["has_image"] = True
                    dialog_manager.dialog_data["working_publication"]["is_custom_image"] = True
                    # Удаляем URL если был
                    dialog_manager.dialog_data["working_publication"].pop("image_url", None)

                    await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)
                    self.logger.info("Изображение загружено")
                else:
                    self.logger.info("Ошибка обработки изображения")
                    dialog_manager.dialog_data["has_image_processing_error"] = True

                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_remove_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_remove_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало удаления изображения")
                dialog_manager.show_mode = ShowMode.EDIT

                dialog_manager.dialog_data["working_publication"]["has_image"] = False
                dialog_manager.dialog_data["working_publication"].pop("image_url", None)
                dialog_manager.dialog_data["working_publication"].pop("custom_image_file_id", None)
                dialog_manager.dialog_data["working_publication"].pop("is_custom_image", None)

                await callback.answer("Изображение удалено", show_alert=True)

                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)
                self.logger.info("Изображение удалено")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось удалить изображение", show_alert=True)
                raise

    async def handle_save_edits(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_save_edits",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало сохранения изменений")
                dialog_manager.show_mode = ShowMode.EDIT

                if not self._has_changes(dialog_manager):
                    self.logger.info("Нет изменений для сохранения")
                    await callback.answer("Нет изменений для сохранения")
                    return

                # Сохраняем изменения
                await self._save_publication_changes(dialog_manager)

                # Обновляем оригинальную версию
                dialog_manager.dialog_data["original_publication"] = dialog_manager.dialog_data["working_publication"]

                del dialog_manager.dialog_data["working_publication"]

                await callback.answer("Изменения сохранены", show_alert=True)
                await dialog_manager.switch_to(model.ModerationPublicationStates.moderation_list)
                self.logger.info("Изменения сохранены")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось сохранить изменения", show_alert=True)
                raise

    async def handle_back_to_moderation_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_back_to_moderation_list",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Возврат к списку модерации")
                dialog_manager.show_mode = ShowMode.EDIT

                await dialog_manager.switch_to(model.ModerationPublicationStates.moderation_list)
                self.logger.info("Возврат к списку модерации выполнен")

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось вернуться к списку", show_alert=True)
                raise

    async def handle_back_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_back_to_content_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Возврат к меню контента")
                dialog_manager.show_mode = ShowMode.EDIT

                if await self._check_alerts(dialog_manager):
                    self.logger.info("Обнаружены алерты")
                    return

                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Возврат к меню контента выполнен")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось вернуться в меню", show_alert=True)
                raise

    async def handle_toggle_social_network(
            self,
            callback: CallbackQuery,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_toggle_social_network",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало переключения социальной сети")
                # Инициализируем словарь выбранных соцсетей если его нет
                if "selected_social_networks" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["selected_social_networks"] = {}

                network_id = checkbox.widget_id
                is_checked = checkbox.is_checked()

                # Сохраняем состояние чекбокса
                dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

                await callback.answer()
                self.logger.info("Социальная сеть переключена")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось переключить соцсеть", show_alert=True)
                raise

    async def handle_prev_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_prev_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало переключения на предыдущее изображение")
                working_pub = dialog_manager.dialog_data.get("working_publication", {})
                images_url = working_pub.get("generated_images_url", [])
                current_index = working_pub.get("current_image_index", 0)

                if current_index > 0:
                    dialog_manager.dialog_data["working_publication"]["current_image_index"] = current_index - 1
                else:
                    self.logger.info("Переход к последнему изображению")
                    dialog_manager.dialog_data["working_publication"]["current_image_index"] = len(images_url) - 1

                await callback.answer()
                self.logger.info("Переключение на предыдущее изображение выполнено")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_next_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_next_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало переключения на следующее изображение")
                working_pub = dialog_manager.dialog_data.get("working_publication", {})
                images_url = working_pub.get("generated_images_url", [])
                current_index = working_pub.get("current_image_index", 0)

                if current_index < len(images_url) - 1:
                    dialog_manager.dialog_data["working_publication"]["current_image_index"] = current_index + 1
                else:
                    self.logger.info("Переход к первому изображению")
                    dialog_manager.dialog_data["working_publication"]["current_image_index"] = 0

                await callback.answer()
                self.logger.info("Переключение на следующее изображение выполнено")
                span.set_status(Status(StatusCode.OK))
            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_publish_now(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService.handle_publish_with_selected_networks",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало публикации")
                # Проверяем, что выбрана хотя бы одна соцсеть
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                if not has_selected_networks:
                    self.logger.info("Не выбрана ни одна социальная сеть")
                    await callback.answer(
                        "Выберите хотя бы одну социальную сеть",
                        show_alert=True
                    )
                    return

                if self._has_changes(dialog_manager):
                    self.logger.info("Сохранение изменений перед публикацией")
                    await self._save_publication_changes(dialog_manager)

                original_pub = dialog_manager.dialog_data["original_publication"]
                publication_id = original_pub["id"]
                state = await self._get_state(dialog_manager)

                # Получаем выбранные социальные сети
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                tg_source = selected_networks.get("telegram_checkbox", False)
                vk_source = selected_networks.get("vkontakte_checkbox", False)

                # Обновляем публикацию с выбранными соцсетями
                await self.loom_content_client.change_publication(
                    publication_id=publication_id,
                    tg_source=tg_source,
                    vk_source=vk_source,
                )

                # Одобряем публикацию
                await self.loom_content_client.moderate_publication(
                    publication_id=publication_id,
                    moderator_id=state.account_id,
                    moderation_status="approved",
                )

                post_links = await self.loom_content_client.moderate_publication(
                    publication_id,
                    state.account_id,
                    "approved"
                )

                dialog_manager.dialog_data["post_links"] = post_links

                await self._remove_current_publication_from_list(dialog_manager)
                await callback.answer("Опубликовано!", show_alert=True)

                await dialog_manager.switch_to(model.ModerationPublicationStates.publication_success)
                self.logger.info("Публикация одобрена и опубликована")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:

                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Не удалось опубликовать", show_alert=True)
                raise

    # Вспомогательные методы
    def _has_changes(self, dialog_manager: DialogManager) -> bool:
        original = dialog_manager.dialog_data.get("original_publication", {})
        working = dialog_manager.dialog_data.get("working_publication", {})

        if not original or not working:
            return False

        # Сравниваем текстовые поля
        fields_to_compare = ["text", ]
        for field in fields_to_compare:
            if original.get(field) != working.get(field):
                return True

        # Проверяем изменения изображения более детально

        # 1. Проверяем, изменилось ли наличие изображения
        if original.get("has_image", False) != working.get("has_image", False):
            return True

        # 2. Если есть пользовательское изображение - это всегда изменение
        if working.get("custom_image_file_id"):
            # Проверяем, было ли это изображение в оригинале
            if original.get("custom_image_file_id") != working.get("custom_image_file_id"):
                return True

        # 3. Проверяем изменение URL (новое сгенерированное изображение)
        original_url = original.get("image_url", "")
        working_url = working.get("image_url", "")

        # Игнорируем базовый URL и сравниваем только если оба не пустые
        if working_url and original_url:
            # Если URL изменился - это новое изображение
            if original_url != working_url:
                return True
        elif working_url != original_url:
            # Один пустой, другой нет - есть изменения
            return True

        return False

    async def _save_publication_changes(self, dialog_manager: DialogManager) -> None:
        working_pub = dialog_manager.dialog_data["working_publication"]
        original_pub = dialog_manager.dialog_data["original_publication"]
        publication_id = working_pub["id"]

        # Определяем, что делать с изображением
        image_url = None
        image_content = None
        image_filename = None
        should_delete_image = False

        # Проверяем изменения изображения
        original_has_image = original_pub.get("has_image", False)
        working_has_image = working_pub.get("has_image", False)

        if not working_has_image and original_has_image:
            # Изображение было удалено
            should_delete_image = True

        elif working_has_image:
            # Проверяем тип изображения и получаем выбранное
            if working_pub.get("custom_image_file_id"):
                # Пользовательское изображение
                image_content = await self.bot.download(working_pub["custom_image_file_id"])
                image_filename = working_pub["custom_image_file_id"] + ".jpg"

            elif working_pub.get("generated_images_url"):
                # Выбранное из множественных сгенерированных
                images_url = working_pub["generated_images_url"]
                current_index = working_pub.get("current_image_index", 0)

                if current_index < len(images_url):
                    selected_url = images_url[current_index]
                    # Проверяем, изменилось ли изображение
                    original_url = original_pub.get("image_url", "")
                    if original_url != selected_url:
                        image_url = selected_url

            elif working_pub.get("image_url"):
                # Одиночное изображение
                original_url = original_pub.get("image_url", "")
                working_url = working_pub.get("image_url", "")

                if original_url != working_url:
                    image_url = working_url

        # Если нужно удалить изображение
        if should_delete_image:
            try:
                await self.loom_content_client.delete_publication_image(
                    publication_id=publication_id
                )
            except Exception as e:
                pass

        # Обновляем публикацию через API
        if image_url or image_content:
            await self.loom_content_client.change_publication(
                publication_id=publication_id,
                text=working_pub["text"],
                image_url=image_url,
                image_content=image_content,
                image_filename=image_filename,
            )
        else:
            # Обновляем только текстовые поля
            await self.loom_content_client.change_publication(
                publication_id=publication_id,
                text=working_pub["text"],
            )

    async def _get_current_image_data_for_moderation(self, dialog_manager: DialogManager) -> tuple[bytes, str] | None:
        try:
            working_pub = dialog_manager.dialog_data.get("working_publication", {})

            # Проверяем пользовательское изображение
            if working_pub.get("custom_image_file_id"):
                file_id = working_pub["custom_image_file_id"]
                image_content = await self.bot.download(file_id)
                return image_content.read(), f"{file_id}.jpg"

            # Проверяем сгенерированные изображения
            elif working_pub.get("generated_images_url"):
                images_url = working_pub["generated_images_url"]
                current_index = working_pub.get("current_image_index", 0)

                if current_index < len(images_url):
                    current_url = images_url[current_index]
                    # Загружаем изображение по URL
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(current_url) as response:
                            response.raise_for_status()
                            content = await response.read()
                            return content, f"generated_image_{current_index}.jpg"

            # Проверяем исходное изображение
            elif working_pub.get("image_url"):
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(working_pub["image_url"]) as response:
                        response.raise_for_status()
                        content = await response.read()
                        return content, "original_image.jpg"

            return None
        except Exception as err:
            return None

    async def _remove_current_publication_from_list(self, dialog_manager: DialogManager) -> None:
        moderation_list = dialog_manager.dialog_data.get("moderation_list", [])
        current_index = dialog_manager.dialog_data.get("current_index", 0)

        if moderation_list and current_index < len(moderation_list):
            moderation_list.pop(current_index)

            # Корректируем индекс если нужно
            if current_index >= len(moderation_list) and moderation_list:
                dialog_manager.dialog_data["current_index"] = len(moderation_list) - 1
            elif not moderation_list:
                dialog_manager.dialog_data["current_index"] = 0

            # Сбрасываем рабочие данные
            dialog_manager.dialog_data.pop("working_publication", None)
            dialog_manager.dialog_data.pop("selected_networks", None)

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

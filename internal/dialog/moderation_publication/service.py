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
            kontur_content_client: interface.IKonturContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.kontur_content_client = kontur_content_client

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
                current_index = dialog_manager.dialog_data.get("current_index", 0)
                moderation_list = dialog_manager.dialog_data.get("moderation_list", [])

                # Определяем направление навигации
                if button.widget_id == "prev_publication":
                    new_index = max(0, current_index - 1)
                else:  # next_publication
                    new_index = min(len(moderation_list) - 1, current_index + 1)

                if new_index == current_index:
                    await callback.answer()
                    return

                # Обновляем индекс
                dialog_manager.dialog_data["current_index"] = new_index

                # Сбрасываем рабочие данные для новой публикации
                dialog_manager.dialog_data.pop("working_publication", None)

                self.logger.info( "Навигация по публикациям")

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка навигации", show_alert=True)
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
                comment = comment.strip()

                if not comment:
                    await message.answer("❌ Комментарий не может быть пустым")
                    return

                if len(comment) < 10:
                    await message.answer("❌ Слишком короткий комментарий. Укажите причину подробнее.")
                    return

                if len(comment) > 500:
                    await message.answer("❌ Слишком длинный комментарий (макс. 500 символов)")
                    return

                dialog_manager.dialog_data["reject_comment"] = comment

                # Удаляем сообщение с комментарием
                await message.delete()

                self.logger.info("Комментарий отклонения введен")

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при сохранении комментария")
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
                state = await self._get_state(dialog_manager)
                original_pub = dialog_manager.dialog_data["original_publication"]
                publication_id = original_pub["id"]
                reject_comment = dialog_manager.dialog_data.get("reject_comment", "Нет комментария")

                # Отклоняем публикацию через API
                await self.kontur_content_client.moderate_publication(
                    publication_id=publication_id,
                    moderator_id=state.account_id,
                    moderation_status="rejected",
                    moderation_comment=reject_comment,
                )

                creator_state = await self.state_repo.state_by_account_id(original_pub["creator_id"])
                if creator_state:
                    await self.bot.send_message(
                        chat_id=creator_state[0].tg_chat_id,
                        text=f"Ваша публикация: <b>{original_pub["name"]}</b> была отклонена с комментарием:\n<b>{reject_comment}</b>",
                        parse_mode=ParseMode.HTML,

                    )

                self.logger.info("Публикация отклонена" )

                await callback.answer("❌ Публикация отклонена", show_alert=True)

                # Удаляем отклоненную публикацию из списка
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

                # Возвращаемся к основному окну
                await dialog_manager.switch_to(model.ModerationPublicationStates.moderation_list)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при отклонении", show_alert=True)
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
                await callback.answer()
                loading_message = await callback.message.answer("🔄 Перегенерирую текст, это может занять время...")

                working_pub = dialog_manager.dialog_data["working_publication"]

                # Перегенерация через API
                regenerated_data = await self.kontur_content_client.regenerate_publication_text(
                    category_id=working_pub["category_id"],
                    publication_text=working_pub["text"],
                    prompt=None
                )

                # Обновляем данные
                dialog_manager.dialog_data["working_publication"]["name"] = regenerated_data["name"]
                dialog_manager.dialog_data["working_publication"]["text"] = regenerated_data["text"]
                dialog_manager.dialog_data["working_publication"]["tags"] = regenerated_data["tags"]


                await loading_message.edit_text("✅ Пост успешно сгенерирован!")
                await asyncio.sleep(3)
                try:
                    await loading_message.delete()
                except:
                    pass

                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)

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
                "ModerationPublicationDialogService.handle_regenerate_text",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                loading_message = await message.answer("🔄 Перегенерирую с учетом ваших пожеланий...")

                working_pub = dialog_manager.dialog_data["working_publication"]

                # Перегенерация через API
                regenerated_data = await self.kontur_content_client.regenerate_publication_text(
                    category_id=working_pub["category_id"],
                    publication_text=working_pub["text"],
                    prompt=prompt
                )

                # Обновляем данные
                dialog_manager.dialog_data["working_publication"]["name"] = regenerated_data["name"]
                dialog_manager.dialog_data["working_publication"]["text"] = regenerated_data["text"]
                dialog_manager.dialog_data["working_publication"]["tags"] = regenerated_data["tags"]
                dialog_manager.dialog_data["regenerate_prompt"] = prompt
                dialog_manager.dialog_data["has_regenerate_prompt"] = True

                await loading_message.edit_text("✅ Пост успешно сгенерирован!")
                await asyncio.sleep(3)
                try:
                    await loading_message.delete()
                except:
                    pass

                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)

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
                "ModerationPublicationDialogService.handle_edit_title_save",
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

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_publication"]["name"] = new_title

                await message.answer("✅ Название обновлено!")
                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)

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
                "ModerationPublicationDialogService.handle_edit_tags_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                tags_raw = text.strip()

                if not tags_raw:
                    new_tags = []
                else:
                    # Парсим теги
                    new_tags = [tag.strip() for tag in tags_raw.split(",")]
                    new_tags = [tag for tag in new_tags if tag]

                    if len(new_tags) > 10:
                        await message.answer("❌ Слишком много тегов (макс. 10)")
                        return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_publication"]["tags"] = new_tags

                await message.answer(f"✅ Теги обновлены ({len(new_tags)} шт.)")
                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)

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
                "ModerationPublicationDialogService.handle_edit_content_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                new_text = text.strip()

                if not new_text:
                    await message.answer("❌ Текст не может быть пустым")
                    return

                if len(new_text) < 50:
                    await message.answer("❌ Слишком короткий текст (мин. 50 символов)")
                    return

                if len(new_text) > 4000:
                    await message.answer("❌ Слишком длинный текст (макс. 4000 символов)")
                    return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_publication"]["text"] = new_text

                await message.answer("✅ Текст обновлен!")
                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)

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
                "ModerationPublicationDialogService.handle_generate_new_image",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await callback.answer()
                loading_message = await callback.message.answer("🔄 Генерирую изображения, это может занять время...")

                working_pub = dialog_manager.dialog_data["working_publication"]
                category_id = working_pub["category_id"]
                publication_text = working_pub["text"]

                # Передаем текущее изображение если есть
                current_image_content = None
                current_image_filename = None

                if await self._get_current_image_data_for_moderation(dialog_manager):
                    current_image_content, current_image_filename = await self._get_current_image_data_for_moderation(
                        dialog_manager)

                # Генерация через API - возвращает массив из 3 URL
                images_url = await self.kontur_content_client.generate_publication_image(
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

                await loading_message.edit_text("✅ Изображения успешно сгенерированы!")
                await asyncio.sleep(2)
                try:
                    await loading_message.delete()
                except:
                    pass

                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка генерации", show_alert=True)
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
                if not prompt.strip():
                    await message.answer("❌ Введите описание изображения")
                    return

                loading_message = await message.answer("🔄 Генерирую изображения по вашему описанию...")

                working_pub = dialog_manager.dialog_data["working_publication"]
                category_id = working_pub["category_id"]
                publication_text = working_pub["text"]

                # Передаем текущее изображение если есть
                current_image_content = None
                current_image_filename = None

                if await self._get_current_image_data_for_moderation(dialog_manager):
                    current_image_content, current_image_filename = await self._get_current_image_data_for_moderation(
                        dialog_manager)

                # Генерация с промптом - возвращает массив из 3 URL
                images_url = await self.kontur_content_client.generate_publication_image(
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

                await loading_message.edit_text("✅ Изображения успешно сгенерированы!")
                await asyncio.sleep(2)
                try:
                    await loading_message.delete()
                except:
                    pass

                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка генерации")
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
                if message.content_type != ContentType.PHOTO:
                    await message.answer("❌ Пожалуйста, отправьте изображение")
                    return

                if message.photo:
                    photo = message.photo[-1]  # Берем наибольшее разрешение

                    # Проверяем размер
                    if hasattr(photo, 'file_size') and photo.file_size:
                        if photo.file_size > 10 * 1024 * 1024:  # 10 МБ
                            await message.answer("❌ Файл слишком большой (макс. 10 МБ)")
                            return

                    await message.answer("📸 Загружаю изображение...")

                    # Обновляем рабочую версию
                    dialog_manager.dialog_data["working_publication"]["custom_image_file_id"] = photo.file_id
                    dialog_manager.dialog_data["working_publication"]["has_image"] = True
                    dialog_manager.dialog_data["working_publication"]["is_custom_image"] = True
                    # Удаляем URL если был
                    dialog_manager.dialog_data["working_publication"].pop("image_url", None)

                    self.logger.info(
                        "Изображение загружено для модерации",
                        {
                            common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                            "file_id": photo.file_id,
                        }
                    )

                    await message.answer("✅ Изображение загружено!")
                    await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка загрузки")
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
                working_pub = dialog_manager.dialog_data["working_publication"]

                if working_pub.get("has_image"):
                    # Удаляем все данные об изображении из рабочей версии
                    dialog_manager.dialog_data["working_publication"]["has_image"] = False
                    dialog_manager.dialog_data["working_publication"].pop("image_url", None)
                    dialog_manager.dialog_data["working_publication"].pop("custom_image_file_id", None)
                    dialog_manager.dialog_data["working_publication"].pop("is_custom_image", None)

                    await callback.answer("✅ Изображение удалено", show_alert=True)
                else:
                    await callback.answer("ℹ️ Изображение отсутствует", show_alert=True)

                await dialog_manager.switch_to(model.ModerationPublicationStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка удаления", show_alert=True)
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
                if not self._has_changes(dialog_manager):
                    await callback.answer("ℹ️ Нет изменений для сохранения", show_alert=True)
                    return

                await callback.answer()
                loading_message = await callback.message.answer("💾 Сохраняю изменения...")

                # Сохраняем изменения
                await self._save_publication_changes(dialog_manager)

                # Обновляем оригинальную версию
                dialog_manager.dialog_data["original_publication"] = dialog_manager.dialog_data["working_publication"]

                del dialog_manager.dialog_data["working_publication"]


                await loading_message.edit_text("✅ Изменения сохранены!")
                await asyncio.sleep(2)
                try:
                    await loading_message.delete()
                except:
                    pass

                await dialog_manager.switch_to(model.ModerationPublicationStates.moderation_list)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка сохранения", show_alert=True)
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
                await dialog_manager.switch_to(model.ModerationPublicationStates.moderation_list)

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка сохранения", show_alert=True)
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
                # Инициализируем словарь выбранных соцсетей если его нет
                if "selected_social_networks" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["selected_social_networks"] = {}

                network_id = checkbox.widget_id
                is_checked = checkbox.is_checked()

                # Сохраняем состояние чекбокса
                dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

                self.logger.info(
                    "Социальная сеть переключена в модерации",
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
                working_pub = dialog_manager.dialog_data.get("working_publication", {})
                images_url = working_pub.get("generated_images_url", [])
                current_index = working_pub.get("current_image_index", 0)

                if current_index > 0:
                    dialog_manager.dialog_data["working_publication"]["current_image_index"] = current_index - 1
                else:
                    dialog_manager.dialog_data["working_publication"]["current_image_index"] = len(images_url) - 1

                await callback.answer()
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
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
                working_pub = dialog_manager.dialog_data.get("working_publication", {})
                images_url = working_pub.get("generated_images_url", [])
                current_index = working_pub.get("current_image_index", 0)

                if current_index < len(images_url) - 1:
                    dialog_manager.dialog_data["working_publication"]["current_image_index"] = current_index + 1
                else:
                    dialog_manager.dialog_data["working_publication"]["current_image_index"] = 0

                await callback.answer()
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_publish_with_selected_networks(
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
                # Проверяем, что выбрана хотя бы одна соцсеть
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                if not has_selected_networks:
                    await callback.answer(
                        "⚠️ Выберите хотя бы одну социальную сеть для публикации",
                        show_alert=True
                    )
                    return

                await self._publish_moderated_publication(callback, dialog_manager)
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при публикации", show_alert=True)
                raise

    async def _publish_moderated_publication(
            self,
            callback: CallbackQuery,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ModerationPublicationDialogService._publish_moderated_publication",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await callback.answer()
                loading_message = await callback.message.answer("🚀 Публикую пост...")

                # Если есть несохраненные изменения, сохраняем их перед публикацией
                if self._has_changes(dialog_manager):
                    await self._save_publication_changes(dialog_manager)

                original_pub = dialog_manager.dialog_data["original_publication"]
                publication_id = original_pub["id"]
                state = await self._get_state(dialog_manager)

                # Получаем выбранные социальные сети
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                tg_source = selected_networks.get("telegram_checkbox", False)
                vk_source = selected_networks.get("vkontakte_checkbox", False)

                # Обновляем публикацию с выбранными соцсетями
                await self.kontur_content_client.change_publication(
                    publication_id=publication_id,
                    tg_source=tg_source,
                    vk_source=vk_source,
                )

                # Одобряем публикацию
                await self.kontur_content_client.moderate_publication(
                    publication_id=publication_id,
                    moderator_id=state.account_id,
                    moderation_status="approved",
                )

                # Формируем сообщение о публикации
                published_networks = []
                if tg_source:
                    published_networks.append("📺 Telegram")
                if vk_source:
                    published_networks.append("🔗 VKontakte")

                networks_text = ", ".join(published_networks)

                self.logger.info(
                    "Публикация одобрена и опубликована",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "publication_id": publication_id,
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

                # Удаляем опубликованную публикацию из списка
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
                    dialog_manager.dialog_data.pop("selected_social_networks", None)

                # Возвращаемся к списку модерации
                await dialog_manager.switch_to(model.ModerationPublicationStates.moderation_list)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    # Вспомогательные методы
    def _has_changes(self, dialog_manager: DialogManager) -> bool:
        original = dialog_manager.dialog_data.get("original_publication", {})
        working = dialog_manager.dialog_data.get("working_publication", {})

        if not original or not working:
            return False

        # Сравниваем текстовые поля
        fields_to_compare = ["name", "text", "tags"]
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
                await self.kontur_content_client.delete_publication_image(
                    publication_id=publication_id
                )
                self.logger.info(f"Deleted image for publication {publication_id}")
            except Exception as e:
                self.logger.warning(f"Failed to delete image: {str(e)}")

        # Обновляем публикацию через API
        if image_url or image_content:
            await self.kontur_content_client.change_publication(
                publication_id=publication_id,
                name=working_pub["name"],
                text=working_pub["text"],
                tags=working_pub.get("tags", []),
                image_url=image_url,
                image_content=image_content,
                image_filename=image_filename,
            )
        else:
            # Обновляем только текстовые поля
            await self.kontur_content_client.change_publication(
                publication_id=publication_id,
                name=working_pub["name"],
                text=working_pub["text"],
                tags=working_pub.get("tags", []),
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
            self.logger.error(f"Ошибка получения данных изображения для модерации: {err}")
            return None

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
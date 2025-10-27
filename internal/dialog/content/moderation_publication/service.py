from typing import Any

from aiogram_dialog.widgets.input import MessageInput

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method

from internal.dialog.helpers import StateManager, AlertsManager, MessageExtractor

from internal.dialog.content.moderation_publication.helpers import (
    ValidationService, TextProcessor, ImageManager, ErrorFlagsManager, PublicationManager, StateRestorer
)



class ModerationPublicationService(interface.IModerationPublicationService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            loom_content_client: interface.ILoomContentClient,
            loom_domain: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.loom_content_client = loom_content_client
        self.loom_domain = loom_domain

        # Инициализация приватных сервисов
        self.state_manager = StateManager(
            state_repo=self.state_repo
        )
        self._validation = ValidationService(
            logger=self.logger
        )
        self._text_processor = TextProcessor(
            logger=self.logger
        )
        self.message_extractor = MessageExtractor(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client
        )
        self._alerts_manager = AlertsManager(
            self.state_repo
        )
        self._image_manager = ImageManager(
            logger=self.logger,
            bot=self.bot,
            loom_domain=self.loom_domain
        )
        self._publication_manager = PublicationManager(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client
        )
        self._state_restorer = StateRestorer(
            logger=self.logger,
            image_manager=self._image_manager
        )
        self._error_flags = ErrorFlagsManager()

    @auto_log()
    @traced_method()
    async def handle_navigate_publication(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        current_index = dialog_manager.dialog_data.get("current_index", 0)
        moderation_list = dialog_manager.dialog_data.get("moderation_list", [])

        # Определяем направление навигации
        if button.widget_id == "prev_publication":
            self.logger.info("Переход к предыдущей публикации")
            new_index = max(0, current_index - 1)
        else:
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

    @auto_log()
    @traced_method()
    async def handle_reject_comment_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            comment: str
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await message.delete()

        self._error_flags.clear_reject_comment_error_flags(dialog_manager=dialog_manager)

        comment = comment.strip()

        if not self._validation.validate_reject_comment(comment=comment, dialog_manager=dialog_manager):
            return

        dialog_manager.dialog_data["reject_comment"] = comment

    @auto_log()
    @traced_method()
    async def handle_send_rejection(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager)
        original_pub = dialog_manager.dialog_data["original_publication"]
        publication_id = original_pub["id"]
        reject_comment = dialog_manager.dialog_data.get("reject_comment", "Нет комментария")

        await self.loom_content_client.moderate_publication(
            publication_id=publication_id,
            moderator_id=state.account_id,
            moderation_status="rejected",
            moderation_comment=reject_comment,
        )
        # TODO сделать вебхук для отклонения публикации

        self._publication_manager.remove_current_publication_from_list(dialog_manager)

        await callback.answer("Публикация отклонена", show_alert=True)
        await dialog_manager.switch_to(state=model.ModerationPublicationStates.moderation_list)

    @auto_log()
    @traced_method()
    async def handle_regenerate_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()
        dialog_manager.dialog_data["is_regenerating_text"] = True
        await dialog_manager.show()

        working_pub = dialog_manager.dialog_data["working_publication"]

        async with tg_action(self.bot, callback.message.chat.id):
            regenerated_data = await self.loom_content_client.regenerate_publication_text(
                category_id=working_pub["category_id"],
                publication_text=working_pub["text"],
                prompt=None
            )

        # Сохраняем предыдущий текст на случай превышения лимита
        dialog_manager.dialog_data["previous_text"] = working_pub["text"]

        # Обновляем данные
        dialog_manager.dialog_data["working_publication"]["text"] = regenerated_data["text"]
        dialog_manager.dialog_data["is_regenerating_text"] = False

        # Проверяем длину текста с изображением
        if await self._text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_regenerate_text_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await message.delete()

        self._error_flags.clear_regenerate_prompt_error_flags(dialog_manager=dialog_manager)

        state = await self.state_manager.get_state(dialog_manager)

        # ВАЛИДАЦИЯ ТИПА КОНТЕНТА
        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для регенерации")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        # ОБРАБОТКА ТЕКСТА ИЛИ ГОЛОСА
        prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id,
            return_html=True
        )

        if not self._validation.validate_regenerate_prompt(prompt=prompt, dialog_manager=dialog_manager):
            return

        dialog_manager.dialog_data["regenerate_prompt"] = prompt
        dialog_manager.dialog_data["has_regenerate_prompt"] = True
        dialog_manager.dialog_data["is_regenerating_text"] = True

        await dialog_manager.show()

        working_pub = dialog_manager.dialog_data["working_publication"]

        # Сохраняем предыдущий текст на случай превышения лимита
        dialog_manager.dialog_data["previous_text"] = working_pub["text"]

        async with tg_action(self.bot, message.chat.id):
            regenerated_data = await self.loom_content_client.regenerate_publication_text(
                category_id=working_pub["category_id"],
                publication_text=working_pub["text"],
                prompt=prompt
            )

        dialog_manager.dialog_data["working_publication"]["text"] = regenerated_data["text"]
        dialog_manager.dialog_data["is_regenerating_text"] = False
        dialog_manager.dialog_data["has_regenerate_prompt"] = False

        # Проверяем длину текста с изображением
        if await self._text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_edit_text(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await message.delete()

        self._error_flags.clear_text_edit_error_flags(dialog_manager=dialog_manager)

        new_text = message.html_text.replace('\n', '<br/>')

        if not self._validation.validate_publication_text(text=new_text, dialog_manager=dialog_manager):
            return

        # Сохраняем предыдущий текст на случай превышения лимита
        working_pub = dialog_manager.dialog_data["working_publication"]
        dialog_manager.dialog_data["previous_text"] = working_pub["text"]

        # Обновляем рабочую версию
        dialog_manager.dialog_data["working_publication"]["text"] = new_text

        # Проверяем длину текста с изображением
        if await self._text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_generate_new_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()
        dialog_manager.dialog_data["is_generating_image"] = True
        await dialog_manager.show()

        working_pub = dialog_manager.dialog_data["working_publication"]
        category_id = working_pub["category_id"]
        publication_text = working_pub["text"]

        # Передаем текущее изображение если есть
        current_image_content = None
        current_image_filename = None

        if await self._image_manager.get_current_image_data(dialog_manager):
            self.logger.info("Используется текущее изображение для генерации")
            current_image_content, current_image_filename = await self._image_manager.get_current_image_data(
                dialog_manager)

        # Сохраняем предыдущее состояние на случай превышения лимита
        dialog_manager.dialog_data["previous_text"] = working_pub["text"]
        dialog_manager.dialog_data["previous_has_image"] = working_pub.get("has_image", False)

        async with tg_action(self.bot, callback.message.chat.id, "upload_photo"):
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

        # Проверяем длину текста с изображением
        if await self._text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_generate_image_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await message.delete()

        self._error_flags.clear_image_prompt_error_flags(dialog_manager=dialog_manager)

        state = await self.state_manager.get_state(dialog_manager)

        # ВАЛИДАЦИЯ ТИПА КОНТЕНТА
        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента для генерации изображения")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        # ОБРАБОТКА ТЕКСТА ИЛИ ГОЛОСА
        prompt = await self.message_extractor.process_voice_or_text_input(
            message=message,
            dialog_manager=dialog_manager,
            organization_id=state.organization_id,
            return_html=True
        )

        if not self._validation.validate_image_prompt(prompt=prompt, dialog_manager=dialog_manager):
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

        if await self._image_manager.get_current_image_data(dialog_manager):
            self.logger.info("Используется текущее изображение для генерации")
            current_image_content, current_image_filename = await self._image_manager.get_current_image_data(
                dialog_manager
            )

        # Сохраняем предыдущее состояние на случай превышения лимита
        dialog_manager.dialog_data["previous_text"] = working_pub["text"]
        dialog_manager.dialog_data["previous_has_image"] = working_pub.get("has_image", False)

        async with tg_action(self.bot, message.chat.id, "upload_photo"):
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

        # Проверяем длину текста с изображением
        if await self._text_processor.check_text_length_with_image(dialog_manager):
            return

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_image_upload(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await message.delete()

        self._error_flags.clear_image_upload_error_flags(dialog_manager=dialog_manager)

        if message.content_type != ContentType.PHOTO:
            self.logger.info("Неверный тип файла изображения")
            dialog_manager.dialog_data["has_invalid_image_type"] = True
            return

        if message.photo:
            photo = message.photo[-1]
            if hasattr(photo, 'file_size') and photo.file_size:
                if photo.file_size > 10 * 1024 * 1024:  # 10 МБ
                    self.logger.info("Размер изображения превышает допустимый")
                    dialog_manager.dialog_data["has_big_image_size"] = True
                    return

            # Сохраняем предыдущее состояние на случай превышения лимита
            working_pub = dialog_manager.dialog_data["working_publication"]
            dialog_manager.dialog_data["previous_text"] = working_pub["text"]
            dialog_manager.dialog_data["previous_has_image"] = working_pub.get("has_image", False)

            # Обновляем рабочую версию
            dialog_manager.dialog_data["working_publication"]["custom_image_file_id"] = photo.file_id
            dialog_manager.dialog_data["working_publication"]["has_image"] = True
            dialog_manager.dialog_data["working_publication"]["is_custom_image"] = True
            # Удаляем URL если был
            dialog_manager.dialog_data["working_publication"].pop("image_url", None)

            self.logger.info("Изображение загружено")

            # Проверяем длину текста с изображением
            if await self._text_processor.check_text_length_with_image(dialog_manager):
                return

            await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)
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
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        self._image_manager.clear_image_data(dialog_manager=dialog_manager)

        await callback.answer("Изображение удалено", show_alert=True)

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_save_edits(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        if not self._publication_manager.has_changes(dialog_manager):
            self.logger.info("Нет изменений для сохранения")
            await callback.answer("Нет изменений для сохранения")
            return

        # Сохраняем изменения
        await self._publication_manager.save_publication_changes(dialog_manager)

        # Обновляем оригинальную версию
        dialog_manager.dialog_data["original_publication"] = dialog_manager.dialog_data["working_publication"]

        del dialog_manager.dialog_data["working_publication"]

        await callback.answer("Изменения сохранены", show_alert=True)
        await dialog_manager.switch_to(state=model.ModerationPublicationStates.moderation_list)

    @auto_log()
    @traced_method()
    async def handle_back_to_moderation_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        await dialog_manager.switch_to(state=model.ModerationPublicationStates.moderation_list)

    @auto_log()
    @traced_method()
    async def handle_back_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager)

        if await self._alerts_manager.check_alerts(dialog_manager=dialog_manager, state=state):
            self.logger.info("Обнаружены алерты")
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
        if "selected_social_networks" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["selected_social_networks"] = {}

        network_id = checkbox.widget_id
        is_checked = checkbox.is_checked()

        # Сохраняем состояние чекбокса
        dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_prev_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._image_manager.navigate_images(
            dialog_manager=dialog_manager,
            direction="prev"
        )
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_next_image(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self._image_manager.navigate_images(
            dialog_manager=dialog_manager,
            direction="next"
        )
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_publish_now(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        if not self._validation.validate_selected_networks(dialog_manager):
            await callback.answer(
                "Выберите хотя бы одну социальную сеть",
                show_alert=True
            )
            return

        state = await self.state_manager.get_state(dialog_manager)
        post_links = await self._publication_manager.approve_and_publish(dialog_manager, state)

        dialog_manager.dialog_data["post_links"] = post_links

        self._publication_manager.remove_current_publication_from_list(dialog_manager)
        await callback.answer("Опубликовано!", show_alert=True)

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.publication_success)

    @auto_log()
    @traced_method()
    async def handle_remove_photo_from_long_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        # Удаляем изображение из рабочей версии
        self._image_manager.clear_image_data(dialog_manager=dialog_manager)

        self.logger.info("Изображение удалено из-за длинного текста")
        await callback.answer("Изображение удалено", show_alert=True)
        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_compress_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()
        await callback.message.edit_text(
            "Сжимаю текст, это может занять время... Не совершайте никаких действий",
            reply_markup=None
        )

        working_pub = dialog_manager.dialog_data["working_publication"]
        category_id = working_pub["category_id"]
        current_text = working_pub["text"]
        expected_length = dialog_manager.dialog_data.get("expected_length", 900)

        compress_prompt = f"Сожми текст до {expected_length} символов, сохраняя основной смысл и ключевые идеи"

        async with tg_action(self.bot, callback.message.chat.id):
            compressed_data = await self.loom_content_client.regenerate_publication_text(
                category_id=category_id,
                publication_text=current_text,
                prompt=compress_prompt
            )

        dialog_manager.dialog_data["working_publication"]["text"] = compressed_data["text"]

        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

    @auto_log()
    @traced_method()
    async def handle_restore_previous_text(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        self._state_restorer.restore_previous_state(dialog_manager)

        await callback.answer("Изменения отменены", show_alert=True)
        await dialog_manager.switch_to(state=model.ModerationPublicationStates.edit_preview)

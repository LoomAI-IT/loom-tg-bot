from aiogram.enums import ContentType
from aiogram.types import Message, PhotoSize
from aiogram_dialog import DialogManager

from internal.dialog.content.moderation_publication.helpers.dialog_data_helper import DialogDataHelper


class ValidationService:
    MIN_REJECT_COMMENT_LENGTH = 10
    MAX_REJECT_COMMENT_LENGTH = 500

    MIN_TEXT_PROMPT_LENGTH = 10
    MAX_TEXT_PROMPT_LENGTH = 4000

    MIN_IMAGE_PROMPT_LENGTH = 10
    MAX_IMAGE_PROMPT_LENGTH = 4000

    MIN_TEXT_LENGTH = 50
    MAX_TEXT_LENGTH = 4000

    def __init__(self, logger):
        self.logger = logger
        self.dialog_data_helper = DialogDataHelper()

    def validate_text_with_limits(
            self,
            text: str,
            min_length: int,
            max_length: int,
            dialog_manager: DialogManager,
            void_flag: str,
            small_flag: str,
            big_flag: str
    ) -> bool:
        if not text:
            self.logger.info(f"Пустой текст: {void_flag}")
            self.dialog_data_helper.set_validation_flag(dialog_manager, void_flag)
            return False

        if len(text) < min_length:
            self.logger.info(f"Слишком короткий текст: {small_flag}")
            self.dialog_data_helper.set_validation_flag(dialog_manager, small_flag)
            return False

        if len(text) > max_length:
            self.logger.info(f"Слишком длинный текст: {big_flag}")
            self.dialog_data_helper.set_validation_flag(dialog_manager, big_flag)
            return False

        return True

    def validate_reject_comment(
            self,
            comment: str,
            dialog_manager: DialogManager
    ) -> bool:
        return self.validate_text_with_limits(
            text=comment,
            min_length=self.MIN_REJECT_COMMENT_LENGTH,
            max_length=self.MAX_REJECT_COMMENT_LENGTH,
            dialog_manager=dialog_manager,
            void_flag="has_void_reject_comment",
            small_flag="has_small_reject_comment",
            big_flag="has_big_reject_comment"
        )

    def validate_regenerate_prompt(
            self,
            prompt: str,
            dialog_manager: DialogManager
    ) -> bool:
        return self.validate_text_with_limits(
            text=prompt,
            min_length=self.MIN_TEXT_PROMPT_LENGTH,
            max_length=self.MAX_TEXT_PROMPT_LENGTH,
            dialog_manager=dialog_manager,
            void_flag="has_void_regenerate_prompt",
            small_flag="has_small_regenerate_prompt",
            big_flag="has_big_regenerate_prompt"
        )

    def validate_edit_image_prompt(
            self,
            prompt: str,
            dialog_manager: DialogManager
    ) -> bool:
        return self.validate_text_with_limits(
            text=prompt,
            min_length=self.MIN_IMAGE_PROMPT_LENGTH,
            max_length=self.MAX_IMAGE_PROMPT_LENGTH,
            dialog_manager=dialog_manager,
            void_flag="has_void_edit_image_prompt",
            small_flag="has_small_edit_image_prompt",
            big_flag="has_big_edit_image_prompt"
        )

    def validate_combine_image_prompt(
            self,
            prompt: str,
            dialog_manager: DialogManager
    ) -> bool:
        return self.validate_text_with_limits(
            text=prompt,
            min_length=self.MIN_IMAGE_PROMPT_LENGTH,
            max_length=self.MAX_IMAGE_PROMPT_LENGTH,
            dialog_manager=dialog_manager,
            void_flag="has_void_combine_image_prompt",
            small_flag="has_small_combine_image_prompt",
            big_flag="has_big_combine_image_prompt"
        )

    def validate_publication_text(
            self,
            text: str,
            dialog_manager: DialogManager
    ) -> bool:
        return self.validate_text_with_limits(
            text=text,
            min_length=self.MIN_TEXT_LENGTH,
            max_length=self.MAX_TEXT_LENGTH,
            dialog_manager=dialog_manager,
            void_flag="has_void_text",
            small_flag="has_small_text",
            big_flag="has_big_text"
        )

    def validate_selected_networks(self, dialog_manager: DialogManager) -> bool:
        selected_networks = self.dialog_data_helper.get_selected_social_networks(dialog_manager)
        has_selected_networks = any(selected_networks.values())

        if not has_selected_networks:
            self.logger.info("Не выбрана ни одна социальная сеть")
            return False

        return True

    def validate_content_type(
            self,
            message: Message,
            dialog_manager: DialogManager,
            allowed_types: list = None
    ) -> bool:
        if allowed_types is None:
            allowed_types = [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]

        if message.content_type not in allowed_types:
            self.dialog_data_helper.set_validation_flag(dialog_manager, "has_invalid_content_type")
            return False
        return True

    def validate_message_content_type(
            self,
            message: Message,
            allowed_types: list[str],
            dialog_manager: DialogManager
    ) -> bool:
        if message.content_type not in allowed_types:
            self.logger.info(f"Неверный тип контента: {message.content_type}, ожидается {allowed_types}")

            return False
        return True

    def validate_image_size(
            self,
            photo: PhotoSize,
            dialog_manager: DialogManager,
            max_size_mb: int = 10
    ) -> bool:
        if hasattr(photo, 'file_size') and photo.file_size:
            max_size_bytes = max_size_mb * 1024 * 1024
            if photo.file_size > max_size_bytes:
                self.logger.info(f"Размер изображения превышает допустимый: {photo.file_size} > {max_size_bytes}")
                self.dialog_data_helper.set_validation_flag(dialog_manager, "has_big_image_size")
                return False
        return True

from aiogram.types import Message, ContentType
from aiogram_dialog import DialogManager


class ValidationService:
    MIN_TEXT_PROMPT_LENGTH = 10
    MAX_TEXT_PROMPT_LENGTH = 2000

    MIN_IMAGE_PROMPT_LENGTH = 10
    MAX_IMAGE_PROMPT_LENGTH = 2000

    MIN_EDIT_IMAGE_PROMPT_LENGTH = 10
    MAX_EDIT_IMAGE_PROMPT_LENGTH = 1000

    MIN_EDITED_TEXT_LENGTH = 50
    MAX_EDITED_TEXT_LENGTH = 4000

    MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
    MAX_COMBINE_IMAGES = 3
    MIN_COMBINE_IMAGES = 2

    def __init__(self, logger):
        self.logger = logger

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
            dialog_manager.dialog_data[void_flag] = True
            return False

        if len(text) < min_length:
            self.logger.info(f"Слишком короткий текст: {small_flag}")
            dialog_manager.dialog_data[small_flag] = True
            return False

        if len(text) > max_length:
            self.logger.info(f"Слишком длинный текст: {big_flag}")
            dialog_manager.dialog_data[big_flag] = True
            return False

        return True

    def validate_prompt(
            self,
            text: str,
            dialog_manager: DialogManager,
            void_flag: str,
            small_flag: str,
            big_flag: str
    ) -> bool:
        return self.validate_text_with_limits(
            text,
            self.MIN_TEXT_PROMPT_LENGTH,
            self.MAX_TEXT_PROMPT_LENGTH,
            dialog_manager,
            void_flag,
            small_flag,
            big_flag
        )

    def validate_input_text(self, text: str, dialog_manager: DialogManager) -> bool:
        return self.validate_text_with_limits(
            text,
            self.MIN_TEXT_PROMPT_LENGTH,
            self.MAX_TEXT_PROMPT_LENGTH,
            dialog_manager,
            "has_void_input_text",
            "has_small_input_text",
            "has_big_input_text"
        )

    def validate_edited_text(self, text: str, dialog_manager: DialogManager) -> bool:
        return self.validate_text_with_limits(
            text,
            self.MIN_EDITED_TEXT_LENGTH,
            self.MAX_EDITED_TEXT_LENGTH,
            dialog_manager,
            "has_void_text",
            "has_small_text",
            "has_big_text"
        )

    def validate_combine_prompt(
            self,
            prompt: str | None,
            dialog_manager: DialogManager
    ) -> bool:
        if not prompt:
            return True

        if len(prompt) < self.MIN_IMAGE_PROMPT_LENGTH:
            self.logger.info("Слишком короткий промпт для объединения")
            dialog_manager.dialog_data["has_small_combine_prompt"] = True
            return False

        if len(prompt) > self.MAX_IMAGE_PROMPT_LENGTH:
            self.logger.info("Слишком длинный промпт для объединения")
            dialog_manager.dialog_data["has_big_combine_prompt"] = True
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
            self.logger.info(f"Неверный тип контента: {message.content_type}")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return False
        return True

    def validate_image_content_type(
            self,
            message: Message,
            dialog_manager: DialogManager,
            error_flag: str = "has_invalid_image_type"
    ) -> bool:
        if message.content_type != ContentType.PHOTO:
            self.logger.info("Неверный тип контента для изображения")
            dialog_manager.dialog_data[error_flag] = True
            return False
        return True

    def validate_image_size(
            self,
            photo,
            dialog_manager: DialogManager,
            error_flag: str = "has_big_image_size"
    ) -> bool:
        if hasattr(photo, 'file_size') and photo.file_size:
            if photo.file_size > self.MAX_IMAGE_SIZE_BYTES:
                self.logger.info(f"Размер изображения превышает лимит: {photo.file_size} bytes")
                dialog_manager.dialog_data[error_flag] = True
                return False
        return True

    def validate_selected_networks(self, selected_networks: dict) -> bool:
        return any(selected_networks.values())

    def validate_combine_images_count(
            self,
            combine_images_list: list,
            dialog_manager: DialogManager,
            check_min: bool = True,
            check_max: bool = True
    ) -> bool:
        images_count = len(combine_images_list)

        if check_max and images_count >= self.MAX_COMBINE_IMAGES:
            self.logger.info(f"Достигнут лимит изображений для объединения: {images_count}")
            dialog_manager.dialog_data["combine_images_limit_reached"] = True
            return False

        if check_min and images_count < self.MIN_COMBINE_IMAGES:
            self.logger.info(f"Недостаточно изображений для объединения: {images_count}")
            dialog_manager.dialog_data["not_enough_combine_images"] = True
            return False

        return True

    def validate_edit_image_prompt(
            self,
            prompt: str,
            dialog_manager: DialogManager
    ) -> bool:
        if not prompt or len(prompt) < self.MIN_EDIT_IMAGE_PROMPT_LENGTH:
            self.logger.info("Слишком короткий промпт для редактирования")
            dialog_manager.dialog_data["has_small_edit_prompt"] = True
            return False

        if len(prompt) > self.MAX_EDIT_IMAGE_PROMPT_LENGTH:
            self.logger.info("Слишком длинный промпт для редактирования")
            dialog_manager.dialog_data["has_big_edit_prompt"] = True
            return False

        return True

    def validate_category_permission(self, employee) -> bool:
        return employee.setting_category_permission

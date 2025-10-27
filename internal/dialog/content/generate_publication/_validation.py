from aiogram_dialog import DialogManager


class _ValidationService:
    MIN_TEXT_PROMPT_LENGTH = 10
    MAX_TEXT_PROMPT_LENGTH = 2000

    MIN_IMAGE_PROMPT_LENGTH = 10
    MAX_IMAGE_PROMPT_LENGTH = 2000

    MIN_EDITED_TEXT_LENGTH = 50
    MAX_EDITED_TEXT_LENGTH = 4000

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

from aiogram_dialog import DialogManager


class ValidationService:
    MIN_REJECT_COMMENT_LENGTH = 10
    MAX_REJECT_COMMENT_LENGTH = 500

    MIN_TEXT_PROMPT_LENGTH = 10
    MAX_TEXT_PROMPT_LENGTH = 1000

    MIN_IMAGE_PROMPT_LENGTH = 10
    MAX_IMAGE_PROMPT_LENGTH = 1000

    MIN_TEXT_LENGTH = 50
    MAX_TEXT_LENGTH = 4000

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
        """Валидация промпта для регенерации текста"""
        return self.validate_text_with_limits(
            text=prompt,
            min_length=self.MIN_TEXT_PROMPT_LENGTH,
            max_length=self.MAX_TEXT_PROMPT_LENGTH,
            dialog_manager=dialog_manager,
            void_flag="has_void_regenerate_prompt",
            small_flag="has_small_regenerate_prompt",
            big_flag="has_big_regenerate_prompt"
        )

    def validate_image_prompt(
            self,
            prompt: str,
            dialog_manager: DialogManager
    ) -> bool:
        return self.validate_text_with_limits(
            text=prompt,
            min_length=self.MIN_IMAGE_PROMPT_LENGTH,
            max_length=self.MAX_IMAGE_PROMPT_LENGTH,
            dialog_manager=dialog_manager,
            void_flag="has_void_image_prompt",
            small_flag="has_small_image_prompt",
            big_flag="has_big_image_prompt"
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
        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
        has_selected_networks = any(selected_networks.values())

        if not has_selected_networks:
            self.logger.info("Не выбрана ни одна социальная сеть")
            return False

        return True

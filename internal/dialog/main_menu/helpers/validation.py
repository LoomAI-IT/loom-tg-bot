import re

from aiogram_dialog import DialogManager


class ValidationService:
    MIN_TEXT_LENGTH = 10
    MAX_TEXT_LENGTH = 2000

    def __init__(self, logger):
        self.logger = logger

    def validate_generate_text_prompt(self, text: str, dialog_manager: DialogManager) -> bool:
        if not text:
            self.logger.info("Пустой текст")
            dialog_manager.dialog_data["has_void_generate_text_prompt"] = True
            return False

        if len(text) < self.MIN_TEXT_LENGTH:
            self.logger.info("Слишком короткий текст")
            dialog_manager.dialog_data["has_small_generate_text_prompt"] = True
            return False

        if len(text) > self.MAX_TEXT_LENGTH:
            self.logger.info("Слишком длинный текст")
            dialog_manager.dialog_data["has_big_generate_text_prompt"] = True
            return False

        return True

    @staticmethod
    def is_valid_youtube_url(url: str) -> bool:
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        return bool(youtube_regex.match(url))

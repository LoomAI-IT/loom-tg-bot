import re

from aiogram_dialog import DialogManager

from internal import model
from internal.dialog.content.draft_publication.helpers.dialog_data_helper import DialogDataHelper


class TextProcessor:
    MAX_TEXT_WITH_IMAGE = 1024
    RECOMMENDED_TEXT_WITH_IMAGE = 800
    MAX_TEXT_WITHOUT_IMAGE = 4096
    RECOMMENDED_TEXT_WITHOUT_IMAGE = 3600

    def __init__(self, logger):
        self.logger = logger
        self.dialog_data_helper = DialogDataHelper()

    async def check_text_length_with_image(
            self,
            dialog_manager: DialogManager
    ) -> bool:
        working_pub = self.dialog_data_helper.get_working_publication_safe(dialog_manager)
        publication_text = working_pub.get("text", "")

        text_without_tags = re.sub(r'<[^>]+>', '', publication_text)
        text_length = len(text_without_tags)
        has_image = self.dialog_data_helper.get_working_image_has_image(dialog_manager)

        if has_image and text_length > self.MAX_TEXT_WITH_IMAGE:
            self.logger.info(f"Текст слишком длинный для публикации с изображением: {text_length} символов")
            self.dialog_data_helper.set_expected_length(dialog_manager, self.RECOMMENDED_TEXT_WITH_IMAGE)
            await dialog_manager.switch_to(state=model.ModerationPublicationStates.text_too_long_alert)
            return True

        if not has_image and text_length > self.MAX_TEXT_WITHOUT_IMAGE:
            self.logger.info(f"Текст слишком длинный: {text_length} символов")
            self.dialog_data_helper.set_expected_length(dialog_manager, self.RECOMMENDED_TEXT_WITHOUT_IMAGE)
            await dialog_manager.switch_to(state=model.ModerationPublicationStates.text_too_long_alert)
            return True

        return False

    @staticmethod
    def format_html_text(text: str) -> str:
        return text.replace('\n', '<br/>')

    @staticmethod
    def strip_text(text: str) -> str:
        return text.strip()

    @staticmethod
    def create_compress_prompt(expected_length: int) -> str:
        return f"Сожми текст до {expected_length} символов, сохраняя основной смысл и ключевые идеи"

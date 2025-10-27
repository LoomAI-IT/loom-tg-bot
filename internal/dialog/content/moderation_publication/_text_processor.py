import re

from aiogram_dialog import DialogManager

from internal import model


class _TextProcessor:
    MAX_TEXT_WITH_IMAGE = 1024
    RECOMMENDED_TEXT_WITH_IMAGE = 900
    MAX_TEXT_WITHOUT_IMAGE = 4096
    RECOMMENDED_TEXT_WITHOUT_IMAGE = 3600

    def __init__(self, logger):
        self.logger = logger

    async def check_text_length_with_image(
            self,
            dialog_manager: DialogManager
    ) -> bool:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        publication_text = working_pub.get("text", "")

        text_without_tags = re.sub(r'<[^>]+>', '', publication_text)
        text_length = len(text_without_tags)
        has_image = working_pub.get("has_image", False)

        if has_image and text_length > self.MAX_TEXT_WITH_IMAGE:
            self.logger.info(f"Текст слишком длинный для публикации с изображением: {text_length} символов")
            dialog_manager.dialog_data["expected_length"] = self.RECOMMENDED_TEXT_WITH_IMAGE
            await dialog_manager.switch_to(state=model.ModerationPublicationStates.text_too_long_alert)
            return True

        if not has_image and text_length > self.MAX_TEXT_WITHOUT_IMAGE:
            self.logger.info(f"Текст слишком длинный: {text_length} символов")
            dialog_manager.dialog_data["expected_length"] = self.RECOMMENDED_TEXT_WITHOUT_IMAGE
            await dialog_manager.switch_to(state=model.ModerationPublicationStates.text_too_long_alert)
            return True

        return False

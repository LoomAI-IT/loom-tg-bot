import re

from aiogram import Bot
from aiogram.types import Message, ContentType
from aiogram_dialog import DialogManager

from internal import interface, model


class _TextProcessor:
    """Сервис для обработки текстов и голосовых сообщений"""

    MAX_TEXT_WITH_IMAGE = 1024
    RECOMMENDED_TEXT_WITH_IMAGE = 800
    MAX_TEXT_WITHOUT_IMAGE = 4096
    RECOMMENDED_TEXT_WITHOUT_IMAGE = 3600

    def __init__(
            self,
            logger,
            bot: Bot,
            loom_content_client: interface.ILoomContentClient
    ):
        self.logger = logger
        self.bot = bot
        self.loom_content_client = loom_content_client

    async def process_voice_or_text_input(
            self,
            message: Message,
            dialog_manager: DialogManager,
            organization_id: int
    ) -> str:
        """Обрабатывает текстовые, голосовые и аудио сообщения"""
        if message.content_type == ContentType.TEXT:
            return message.text if hasattr(message, 'text') else message.html_text.replace('\n', '<br/>')
        else:
            return await self.speech_to_text(message, dialog_manager, organization_id)

    async def speech_to_text(
            self,
            message: Message,
            dialog_manager: DialogManager,
            organization_id: int
    ) -> str:
        """Преобразование голосового сообщения в текст"""
        if message.voice:
            file_id = message.voice.file_id
        else:
            file_id = message.audio.file_id

        dialog_manager.dialog_data["voice_transcribe"] = True
        await dialog_manager.show()

        file = await self.bot.get_file(file_id)
        file_data = await self.bot.download_file(file.file_path)

        text = await self.loom_content_client.transcribe_audio(
            organization_id,
            audio_content=file_data.read(),
            audio_filename="audio.mp3",
        )
        dialog_manager.dialog_data["voice_transcribe"] = False
        return text

    async def check_text_length_with_image(
            self,
            dialog_manager: DialogManager
    ) -> bool:
        """Проверяет длину текста с учетом наличия изображения"""
        publication_text = dialog_manager.dialog_data.get("publication_text", "")

        text_without_tags = re.sub(r'<[^>]+>', '', publication_text)
        text_length = len(text_without_tags)
        has_image = dialog_manager.dialog_data.get("has_image", False)

        if has_image and text_length > self.MAX_TEXT_WITH_IMAGE:
            self.logger.info(f"Текст слишком длинный для публикации с изображением: {text_length} символов")
            dialog_manager.dialog_data["expected_length"] = self.RECOMMENDED_TEXT_WITH_IMAGE
            await dialog_manager.switch_to(model.GeneratePublicationStates.text_too_long_alert)
            return True

        if not has_image and text_length > self.MAX_TEXT_WITHOUT_IMAGE:
            self.logger.info(f"Текст слишком длинный: {text_length} символов")
            dialog_manager.dialog_data["expected_length"] = self.RECOMMENDED_TEXT_WITHOUT_IMAGE
            await dialog_manager.switch_to(model.GeneratePublicationStates.text_too_long_alert)
            return True

        return False

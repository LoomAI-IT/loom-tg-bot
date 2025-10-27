from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import Message
from aiogram_dialog import DialogManager

from internal import interface


class MessageExtractor:
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
            organization_id: int,
            return_html: bool = False,
    ) -> str:
        if message.content_type == ContentType.TEXT:
            return message.text if not return_html else message.html_text.replace('\n', '<br/>')
        else:
            return await self.speech_to_text(
                message=message,
                dialog_manager=dialog_manager,
                organization_id=organization_id
            )

    async def extract_text_from_message(
            self,
            dialog_manager: DialogManager,
            message: Message,
            organization_id: int,
    ) -> str:
        text_parts = []

        if message.content_type in [ContentType.AUDIO, ContentType.VOICE]:
            audio_text = await self.speech_to_text(
                message=message,
                dialog_manager=dialog_manager,
                organization_id=organization_id
            )
            text_parts.append(audio_text)

        if message.html_text:
            text_parts.append(message.html_text)

        elif message.text:
            text_parts.append(message.text)

        elif message.caption:
            text_parts.append(message.caption)

        if message.forward_origin:
            if hasattr(message, 'forward_from_message') and message.forward_from_message:
                forwarded_text = await self.extract_text_from_message(
                    dialog_manager=dialog_manager,
                    message=message.forward_from_message,
                    organization_id=organization_id
                )
                if forwarded_text:
                    text_parts.append(f"[Пересланное сообщение]: {forwarded_text}")

        if message.reply_to_message:
            reply_text = await self.extract_text_from_message(
                dialog_manager=dialog_manager,
                message=message.reply_to_message,
                organization_id=organization_id
            )
            if reply_text:
                text_parts.append(f"[Ответ на]: {reply_text}")

        result = "\n\n".join(text_parts)

        if not result:
            return ""

        return result

    async def speech_to_text(
            self,
            message: Message,
            dialog_manager: DialogManager,
            organization_id: int
    ) -> str:
        if message.voice:
            file_id = message.voice.file_id
        else:
            file_id = message.audio.file_id

        dialog_manager.dialog_data["voice_transcribe"] = True
        await dialog_manager.show()

        file = await self.bot.get_file(file_id)
        file_data = await self.bot.download_file(file.file_path)

        text = await self.loom_content_client.transcribe_audio(
            organization_id=organization_id,
            audio_content=file_data.read(),
            audio_filename="audio.mp3",
        )
        dialog_manager.dialog_data["voice_transcribe"] = False
        return text

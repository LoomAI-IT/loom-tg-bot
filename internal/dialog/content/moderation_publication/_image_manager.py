import aiohttp
import time

from aiogram import Bot
from aiogram.types import ContentType
from aiogram_dialog.api.entities import MediaId, MediaAttachment
from aiogram_dialog import DialogManager


class _ImageManager:
    def __init__(
            self,
            logger,
            bot: Bot,
            loom_domain: str
    ):
        self.logger = logger
        self.bot = bot
        self.loom_domain = loom_domain

    def navigate_images(
            self,
            dialog_manager: DialogManager,
            direction: str
    ) -> None:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        images_url = working_pub.get("generated_images_url", [])
        current_index = working_pub.get("current_image_index", 0)

        if direction == "prev":
            if current_index > 0:
                dialog_manager.dialog_data["working_publication"]["current_image_index"] = current_index - 1
            else:
                self.logger.info("Переход к последнему изображению")
                dialog_manager.dialog_data["working_publication"]["current_image_index"] = len(images_url) - 1
        else:  # next
            if current_index < len(images_url) - 1:
                dialog_manager.dialog_data["working_publication"]["current_image_index"] = current_index + 1
            else:
                self.logger.info("Переход к первому изображению")
                dialog_manager.dialog_data["working_publication"]["current_image_index"] = 0

    async def get_current_image_data(
            self,
            dialog_manager: DialogManager
    ) -> tuple[bytes, str] | None:
        try:
            working_pub = dialog_manager.dialog_data.get("working_publication", {})

            # Проверяем пользовательское изображение
            if working_pub.get("custom_image_file_id"):
                file_id = working_pub["custom_image_file_id"]
                image_content = await self.bot.download(file_id)
                return image_content.read(), f"{file_id}.jpg"

            # Проверяем сгенерированные изображения
            elif working_pub.get("generated_images_url"):
                images_url = working_pub["generated_images_url"]
                current_index = working_pub.get("current_image_index", 0)

                if current_index < len(images_url):
                    current_url = images_url[current_index]
                    async with aiohttp.ClientSession() as session:
                        async with session.get(current_url) as response:
                            response.raise_for_status()
                            content = await response.read()
                            return content, f"generated_image_{current_index}.jpg"

            # Проверяем исходное изображение
            elif working_pub.get("image_url"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(working_pub["image_url"]) as response:
                        response.raise_for_status()
                        content = await response.read()
                        return content, "original_image.jpg"

            return None
        except Exception as err:
            self.logger.error(f"Ошибка при получении данных изображения: {err}")
            return None

    def get_moderation_image_media(
            self,
            publication_id: int,
            image_fid: str | None
    ) -> tuple[MediaAttachment | None, str | None]:
        if not image_fid:
            return None, None

        cache_buster = int(time.time())
        image_url = f"https://{self.loom_domain}/api/content/publication/{publication_id}/image/download?v={cache_buster}"

        preview_image_media = MediaAttachment(
            url=image_url,
            type=ContentType.PHOTO
        )

        return preview_image_media, image_url

    def get_edit_preview_image_media(self, working_pub: dict) -> MediaAttachment | None:
        if not working_pub.get("has_image"):
            return None

        # Кастомное загруженное изображение
        if working_pub.get("custom_image_file_id"):
            self.logger.info("Загрузка пользовательского изображения")
            return self.build_media_from_file_id(working_pub["custom_image_file_id"])

        # Сгенерированные изображения (несколько вариантов)
        if working_pub.get("generated_images_url"):
            self.logger.info("Загрузка сгенерированного изображения")
            images_url = working_pub["generated_images_url"]
            current_image_index = working_pub.get("current_image_index", 0)

            if current_image_index < len(images_url):
                return self.build_media_from_url(images_url[current_image_index])

        # Одиночное изображение по URL
        if working_pub.get("image_url"):
            self.logger.info("Загрузка изображения по URL")
            return self.build_media_from_url(working_pub["image_url"])

        return None

    def build_media_from_url(self, url: str) -> MediaAttachment:
        return MediaAttachment(
            url=url,
            type=ContentType.PHOTO
        )

    def build_media_from_file_id(self, file_id: str) -> MediaAttachment:
        return MediaAttachment(
            file_id=MediaId(file_id),
            type=ContentType.PHOTO
        )

    def clear_image_data(self, dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data["working_publication"]["has_image"] = False
        dialog_manager.dialog_data["working_publication"].pop("image_url", None)
        dialog_manager.dialog_data["working_publication"].pop("custom_image_file_id", None)
        dialog_manager.dialog_data["working_publication"].pop("is_custom_image", None)
        dialog_manager.dialog_data["working_publication"].pop("generated_images_url", None)
        dialog_manager.dialog_data["working_publication"].pop("current_image_index", None)

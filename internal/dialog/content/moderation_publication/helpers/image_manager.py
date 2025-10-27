import aiohttp
import time

from aiogram import Bot
from aiogram.types import ContentType
from aiogram_dialog.api.entities import MediaId, MediaAttachment
from aiogram_dialog import DialogManager

from internal.dialog.content.moderation_publication.helpers.dialog_data_helper import DialogDataHelper


class ImageManager:
    def __init__(
            self,
            logger,
            bot: Bot,
            loom_domain: str
    ):
        self.logger = logger
        self.bot = bot
        self.loom_domain = loom_domain

        self.dialog_data_helper = DialogDataHelper()

    def navigate_images(
            self,
            dialog_manager: DialogManager,
            direction: str
    ) -> None:
        working_pub = self.dialog_data_helper.get_working_publication_safe(dialog_manager)
        images_url = working_pub.get("generated_images_url", [])
        current_index = working_pub.get("current_image_index", 0)

        if direction == "prev":
            if current_index > 0:
                self.dialog_data_helper.set_working_image_index(dialog_manager, current_index - 1)
            else:
                self.logger.info("Переход к последнему изображению")
                self.dialog_data_helper.set_working_image_index(dialog_manager, len(images_url) - 1)
        else:  # next
            if current_index < len(images_url) - 1:
                self.dialog_data_helper.set_working_image_index(dialog_manager, current_index + 1)
            else:
                self.logger.info("Переход к первому изображению")
                self.dialog_data_helper.set_working_image_index(dialog_manager, 0)

    async def get_current_image_data(
            self,
            dialog_manager: DialogManager
    ) -> tuple[bytes, str] | None:
        try:
            working_pub = self.dialog_data_helper.get_working_publication_safe(dialog_manager)

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
        self.dialog_data_helper.set_working_image_has_image(dialog_manager, False)
        self.dialog_data_helper.remove_working_image_fields(
            dialog_manager,
            "image_url",
            "custom_image_file_id",
            "is_custom_image",
            "generated_images_url",
            "current_image_index"
        )

    async def prepare_current_image_for_generation(
            self,
            dialog_manager: DialogManager
    ) -> tuple[bytes | None, str | None]:
        image_data = await self.get_current_image_data(dialog_manager)
        if image_data:
            self.logger.info("Используется текущее изображение для генерации")
            return image_data
        return None, None

    def update_generated_images(
            self,
            dialog_manager: DialogManager,
            images_url: list[str]
    ) -> None:
        self.dialog_data_helper.set_working_generated_images(dialog_manager, images_url)
        self.dialog_data_helper.set_working_image_has_image(dialog_manager, True)
        self.dialog_data_helper.set_working_image_index(dialog_manager, 0)

        # Удаляем старые данные изображения
        self.dialog_data_helper.remove_working_image_fields(
            dialog_manager,
            "custom_image_file_id",
            "is_custom_image",
            "image_url"
        )

    def update_custom_image(
            self,
            dialog_manager: DialogManager,
            file_id: str
    ) -> None:
        self.dialog_data_helper.set_working_custom_image(dialog_manager, file_id)
        self.dialog_data_helper.set_working_image_has_image(dialog_manager, True)

        # Удаляем URL если был
        self.dialog_data_helper.remove_working_image_fields(
            dialog_manager,
            "image_url",
            "generated_images_url",
            "current_image_index"
        )

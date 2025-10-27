import aiohttp
from aiogram import Bot
from aiogram.types import BufferedInputFile, ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId

from internal import interface, model
from pkg.tg_action_wrapper import tg_action


class ImageManager:
    def __init__(
            self,
            logger,
            bot: Bot,
            loom_content_client: interface.ILoomContentClient
    ):
        self.logger = logger
        self.bot = bot
        self.loom_content_client = loom_content_client

    def navigate_images(
            self,
            dialog_manager: DialogManager,
            images_key: str,
            index_key: str,
            direction: str
    ) -> None:
        images_list = dialog_manager.dialog_data.get(images_key, [])
        current_index = dialog_manager.dialog_data.get(index_key, 0)

        if direction == "next":
            new_index = current_index + 1 if current_index < len(images_list) - 1 else 0
        else:  # prev
            new_index = current_index - 1 if current_index > 0 else len(images_list) - 1

        dialog_manager.dialog_data[index_key] = new_index

    def create_image_backup_dict(self, dialog_manager: DialogManager) -> dict | None:
        if dialog_manager.dialog_data.get("custom_image_file_id"):
            return {
                "type": "file_id",
                "value": dialog_manager.dialog_data["custom_image_file_id"]
            }
        elif dialog_manager.dialog_data.get("publication_images_url"):
            images_url = dialog_manager.dialog_data["publication_images_url"]
            current_index = dialog_manager.dialog_data.get("current_image_index", 0)
            return {
                "type": "url",
                "value": images_url,
                "index": current_index
            }
        return None

    def backup_current_image(self, dialog_manager: DialogManager) -> None:
        old_image_backup = self.create_image_backup_dict(dialog_manager)
        dialog_manager.dialog_data["old_generated_image_backup"] = old_image_backup

    def clear_image_data(self, dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data["has_image"] = False
        dialog_manager.dialog_data.pop("publication_images_url", None)
        dialog_manager.dialog_data.pop("custom_image_file_id", None)
        dialog_manager.dialog_data.pop("is_custom_image", None)
        dialog_manager.dialog_data.pop("current_image_index", None)

    def clear_temporary_image_data(self, dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("generated_images_url", None)
        dialog_manager.dialog_data.pop("combine_result_url", None)
        dialog_manager.dialog_data.pop("old_generated_image_backup", None)
        dialog_manager.dialog_data.pop("old_image_backup", None)
        dialog_manager.dialog_data.pop("image_edit_prompt", None)
        dialog_manager.dialog_data.pop("combine_images_list", None)
        dialog_manager.dialog_data.pop("combine_current_index", None)
        dialog_manager.dialog_data.pop("combine_prompt", None)
        dialog_manager.dialog_data.pop("showing_old_image", None)

    def set_generated_images(self, dialog_manager: DialogManager, images_url: list[str]) -> None:
        dialog_manager.dialog_data["publication_images_url"] = images_url
        dialog_manager.dialog_data["has_image"] = True
        dialog_manager.dialog_data["is_custom_image"] = False
        dialog_manager.dialog_data["current_image_index"] = 0
        dialog_manager.dialog_data.pop("custom_image_file_id", None)

    async def download_image(self, image_url: str) -> tuple[bytes, str]:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                response.raise_for_status()
                content = await response.read()
                content_type = response.headers.get('content-type', 'image/png')
                return content, content_type

    async def download_and_get_file_id(self, image_url: str, chat_id: int) -> str | None:
        try:
            image_content, _ = await self.download_image(image_url=image_url)

            message = await self.bot.send_photo(
                chat_id=chat_id,
                photo=BufferedInputFile(image_content, filename="tmp_image.png"),
            )
            await message.delete()
            return message.photo[-1].file_id
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке изображения: {e}")
            return None

    async def get_current_image_data(self, dialog_manager: DialogManager) -> tuple[bytes, str] | None:
        try:
            if dialog_manager.dialog_data.get("custom_image_file_id"):
                file_id = dialog_manager.dialog_data["custom_image_file_id"]
                image_content = await self.bot.download(file_id)
                return image_content.read(), f"{file_id}.jpg"

            elif dialog_manager.dialog_data.get("publication_images_url"):
                images_url = dialog_manager.dialog_data["publication_images_url"]
                current_index = dialog_manager.dialog_data.get("current_image_index", 0)

                if current_index < len(images_url):
                    current_url = images_url[current_index]
                    image_content, content_type = await self.download_image(current_url)
                    filename = f"generated_image_{current_index}.jpg"
                    return image_content, filename

            return None
        except Exception as err:
            self.logger.error(f"Ошибка при получении данных изображения: {err}")
            return None

    async def get_selected_image_data(self, dialog_manager: DialogManager) -> tuple[
        str | None, bytes | None, str | None
    ]:
        if dialog_manager.dialog_data.get("custom_image_file_id"):
            file_id = dialog_manager.dialog_data["custom_image_file_id"]
            image_content = await self.bot.download(file_id)
            return None, image_content.read(), f"{file_id}.jpg"

        elif dialog_manager.dialog_data.get("publication_images_url"):
            images_url = dialog_manager.dialog_data["publication_images_url"]
            current_index = dialog_manager.dialog_data.get("current_image_index", 0)

            if current_index < len(images_url):
                selected_url = images_url[current_index]
                return selected_url, None, None

        return None, None, None

    async def combine_images_with_prompt(
            self,
            dialog_manager: DialogManager,
            state: model.UserState,
            combine_images_list: list[str],
            prompt: str,
            chat_id: int
    ) -> list[str] | None:
        images_content = []
        images_filenames = []

        for i, file_id in enumerate(combine_images_list):
            image_io = await self.bot.download(file_id)
            content = image_io.read()
            images_content.append(content)
            images_filenames.append(f"image_{i}.jpg")

        async with tg_action(self.bot, chat_id, "upload_photo"):
            combined_images_url = await self.loom_content_client.combine_images(
                organization_id=state.organization_id,
                category_id=dialog_manager.dialog_data["category_id"],
                images_content=images_content,
                images_filenames=images_filenames,
                prompt=prompt,
            )

        return combined_images_url

    def restore_image_from_backup(
            self,
            dialog_manager: DialogManager,
            backup_dict: dict | None
    ) -> None:
        if not backup_dict:
            self.clear_image_data(dialog_manager)
            return

        if backup_dict["type"] == "file_id":
            dialog_manager.dialog_data["custom_image_file_id"] = backup_dict["value"]
            dialog_manager.dialog_data["has_image"] = True
            dialog_manager.dialog_data["is_custom_image"] = True
            dialog_manager.dialog_data.pop("publication_images_url", None)
            dialog_manager.dialog_data.pop("current_image_index", None)
        elif backup_dict["type"] == "url":
            value = backup_dict["value"]
            if isinstance(value, list):
                dialog_manager.dialog_data["publication_images_url"] = value
                dialog_manager.dialog_data["current_image_index"] = backup_dict.get("index", 0)
            else:
                dialog_manager.dialog_data["publication_images_url"] = [value]
                dialog_manager.dialog_data["current_image_index"] = 0
            dialog_manager.dialog_data["has_image"] = True
            dialog_manager.dialog_data["is_custom_image"] = False
            dialog_manager.dialog_data.pop("custom_image_file_id", None)

    async def prepare_current_image_for_combine(
            self,
            dialog_manager: DialogManager,
            chat_id: int
    ) -> list[str]:
        """
        Подготавливает текущее изображение для комбинирования.
        Возвращает список с одним file_id.
        """
        combine_images_list = []

        if dialog_manager.dialog_data.get("custom_image_file_id"):
            file_id = dialog_manager.dialog_data["custom_image_file_id"]
            combine_images_list.append(file_id)
        elif dialog_manager.dialog_data.get("publication_images_url"):
            images_url = dialog_manager.dialog_data["publication_images_url"]
            current_index = dialog_manager.dialog_data.get("current_image_index", 0)
            if current_index < len(images_url):
                current_url = images_url[current_index]
                file_id = await self.download_and_get_file_id(current_url, chat_id)
                if file_id:
                    combine_images_list.append(file_id)

        return combine_images_list

    def get_preview_image_media(
            self,
            dialog_manager: DialogManager
    ) -> tuple[MediaAttachment | None, bool, int, int]:
        preview_image_media = None
        has_multiple_images = False
        current_image_index = 0
        total_images = 0

        if dialog_manager.dialog_data.get("custom_image_file_id"):
            self.logger.info("Используется кастомное изображение")
            file_id = dialog_manager.dialog_data["custom_image_file_id"]
            preview_image_media = MediaAttachment(
                file_id=MediaId(file_id),
                type=ContentType.PHOTO
            )
        elif dialog_manager.dialog_data.get("publication_images_url"):
            self.logger.info("Используется сгенерированное изображение")
            images_url = dialog_manager.dialog_data["publication_images_url"]
            current_image_index = dialog_manager.dialog_data.get("current_image_index", 0)
            total_images = len(images_url)
            has_multiple_images = total_images > 1

            if current_image_index < len(images_url):
                preview_image_media = MediaAttachment(
                    url=images_url[current_image_index],
                    type=ContentType.PHOTO
                )

        return preview_image_media, has_multiple_images, current_image_index, total_images

    def get_image_menu_media(self, dialog_manager: DialogManager) -> MediaAttachment | None:
        if dialog_manager.dialog_data.get("custom_image_file_id"):
            file_id = dialog_manager.dialog_data["custom_image_file_id"]
            return MediaAttachment(
                file_id=MediaId(file_id),
                type=ContentType.PHOTO
            )
        elif dialog_manager.dialog_data.get("publication_images_url"):
            images_url = dialog_manager.dialog_data["publication_images_url"]
            current_image_index = dialog_manager.dialog_data.get("current_image_index", 0)

            if current_image_index < len(images_url):
                return MediaAttachment(
                    url=images_url[current_image_index],
                    type=ContentType.PHOTO
                )
        return None

    def get_combine_images_media(
            self,
            dialog_manager: DialogManager
    ) -> tuple[MediaAttachment | None, int, int]:
        combine_images_list = dialog_manager.dialog_data.get("combine_images_list", [])
        combine_current_index = dialog_manager.dialog_data.get("combine_current_index", 0)
        combine_images_count = len(combine_images_list)

        combine_current_image_media = None
        if combine_images_list and combine_current_index < len(combine_images_list):
            file_id = combine_images_list[combine_current_index]
            combine_current_image_media = MediaAttachment(
                file_id=MediaId(file_id),
                type=ContentType.PHOTO
            )

        return combine_current_image_media, combine_current_index, combine_images_count

    def get_new_image_confirm_media(
            self,
            dialog_manager: DialogManager
    ) -> tuple[MediaAttachment | None, MediaAttachment | None, bool]:
        generated_images_url = dialog_manager.dialog_data.get("generated_images_url")
        combine_result_url = dialog_manager.dialog_data.get("combine_result_url")

        old_image_backup = dialog_manager.dialog_data.get("old_generated_image_backup") or \
                           dialog_manager.dialog_data.get("old_image_backup")

        showing_old_image = dialog_manager.dialog_data.get("showing_old_image", False)

        new_image_media = None
        old_image_media = None

        if generated_images_url and len(generated_images_url) > 0:
            new_image_media = MediaAttachment(
                url=generated_images_url[0],
                type=ContentType.PHOTO
            )
        elif combine_result_url:
            new_image_media = MediaAttachment(
                url=combine_result_url,
                type=ContentType.PHOTO
            )

        if old_image_backup:
            old_image_media = self._create_media_from_backup(old_image_backup)

        return new_image_media, old_image_media, showing_old_image

    def _create_media_from_backup(self, backup_dict: dict) -> MediaAttachment | None:
        if backup_dict["type"] == "file_id":
            return MediaAttachment(
                file_id=MediaId(backup_dict["value"]),
                type=ContentType.PHOTO
            )
        elif backup_dict["type"] == "url":
            value = backup_dict["value"]
            if isinstance(value, list):
                index = backup_dict.get("index", 0)
                if index < len(value):
                    return MediaAttachment(
                        url=value[index],
                        type=ContentType.PHOTO
                    )
            else:
                return MediaAttachment(
                    url=value,
                    type=ContentType.PHOTO
                )
        return None


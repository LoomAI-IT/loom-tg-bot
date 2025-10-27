from aiogram.types import ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId


class _ImageDataProvider:
    def __init__(self, logger):
        self.logger = logger

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

import aiohttp
import time

from aiogram import Bot
from aiogram.types import ContentType
from aiogram_dialog.api.entities import MediaId, MediaAttachment
from aiogram_dialog import DialogManager

from internal import interface
from internal.dialog.content.moderation_publication.helpers.dialog_data_helper import DialogDataHelper


class ImageManager:
    def __init__(
            self,
            logger,
            bot: Bot,
            loom_content_client: interface.ILoomContentClient,
            loom_domain: str,

    ):
        self.logger = logger
        self.bot = bot
        self.loom_content_client = loom_content_client
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

    def get_image_menu_media(self, dialog_manager: DialogManager) -> MediaAttachment | None:
        """Получение медиа для меню редактирования изображения"""
        working_pub = self.dialog_data_helper.get_working_publication_safe(dialog_manager)
        return self.get_edit_preview_image_media(working_pub)

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

    # ============= МЕТОДЫ ДЛЯ COMBINE IMAGES =============

    async def download_image(self, image_url: str) -> tuple[bytes, str]:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                response.raise_for_status()
                content = await response.read()
                content_type = response.headers.get('content-type', 'image/png')
                return content, content_type

    async def download_and_get_file_id(self, image_url: str, chat_id: int) -> str | None:
        try:
            from aiogram.types import BufferedInputFile
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

    def navigate_combine_images(
            self,
            dialog_manager: DialogManager,
            direction: str
    ) -> None:
        combine_images_list = self.dialog_data_helper.get_combine_images_list(dialog_manager)
        current_index = self.dialog_data_helper.get_combine_current_index(dialog_manager)

        if direction == "next":
            new_index = current_index + 1 if current_index < len(combine_images_list) - 1 else 0
        else:  # prev
            new_index = current_index - 1 if current_index > 0 else len(combine_images_list) - 1

        self.dialog_data_helper.set_combine_current_index(dialog_manager, new_index)

    def get_combine_images_media(
            self,
            dialog_manager: DialogManager
    ) -> tuple[MediaAttachment | None, int, int]:
        combine_images_list = self.dialog_data_helper.get_combine_images_list(dialog_manager)
        combine_current_index = self.dialog_data_helper.get_combine_current_index(dialog_manager)
        combine_images_count = len(combine_images_list)

        combine_current_image_media = None
        if combine_images_list and combine_current_index < len(combine_images_list):
            file_id = combine_images_list[combine_current_index]
            combine_current_image_media = MediaAttachment(
                file_id=MediaId(file_id),
                type=ContentType.PHOTO
            )

        return combine_current_image_media, combine_current_index, combine_images_count

    def upload_combine_image(
            self,
            photo,
            dialog_manager: DialogManager
    ) -> bool:
        combine_images_list = self.dialog_data_helper.get_combine_images_list(dialog_manager)
        combine_images_list.append(photo.file_id)
        new_index = len(combine_images_list) - 1
        self.dialog_data_helper.set_combine_images_list(dialog_manager, combine_images_list, new_index)

        self.logger.info(f"Изображение добавлено для объединения. Всего: {len(combine_images_list)}")
        return True

    def delete_combine_image(self, dialog_manager: DialogManager) -> None:
        combine_images_list = self.dialog_data_helper.get_combine_images_list(dialog_manager)
        current_index = self.dialog_data_helper.get_combine_current_index(dialog_manager)

        if current_index < len(combine_images_list):
            combine_images_list.pop(current_index)

            # Корректируем индекс
            if current_index >= len(combine_images_list) > 0:
                new_index = len(combine_images_list) - 1
            else:
                new_index = 0

            self.dialog_data_helper.set_combine_images_list(dialog_manager, combine_images_list, new_index)

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

        working_pub = self.dialog_data_helper.get_working_publication_safe(dialog_manager)
        custom_image_file_id = working_pub.get("custom_image_file_id")

        if custom_image_file_id:
            combine_images_list.append(custom_image_file_id)
        else:
            publication_images_url = working_pub.get("generated_images_url")
            if publication_images_url:
                current_index = working_pub.get("current_image_index", 0)
                if current_index < len(publication_images_url):
                    current_url = publication_images_url[current_index]
                    file_id = await self.download_and_get_file_id(current_url, chat_id)
                    if file_id:
                        combine_images_list.append(file_id)
            else:
                # Проверяем оригинальное изображение публикации
                image_url = working_pub.get("image_url")
                if image_url:
                    file_id = await self.download_and_get_file_id(image_url, chat_id)
                    if file_id:
                        combine_images_list.append(file_id)

        return combine_images_list

    def init_combine_from_scratch(self, dialog_manager: DialogManager) -> None:
        self.dialog_data_helper.set_combine_images_list(dialog_manager, [], 0)

    def cleanup_combine_data(self, dialog_manager: DialogManager) -> None:
        self.dialog_data_helper.clear_combine_data(dialog_manager)

    def should_return_to_new_image_confirm(self, dialog_manager: DialogManager) -> bool:
        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_result_url = self.dialog_data_helper.get_combined_image_result_url(dialog_manager)
        return generated_images_url is not None or combined_image_result_url is not None

    async def prepare_combine_image_from_new_image(
            self,
            dialog_manager: DialogManager,
            chat_id: int
    ) -> list[str]:
        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_result_url = self.dialog_data_helper.get_combined_image_result_url(dialog_manager)

        image_url = None
        if combined_image_result_url:
            image_url = combined_image_result_url
        elif generated_images_url and len(generated_images_url) > 0:
            image_url = generated_images_url[0]

        combine_images_list = []
        if image_url:
            file_id = await self.download_and_get_file_id(
                image_url=image_url,
                chat_id=chat_id
            )
            if file_id:
                combine_images_list.append(file_id)
                self.logger.info(f"Новая картинка добавлена в список для объединения: {file_id}")

        # Сохраняем backup
        previous_generation_backup = self.dialog_data_helper.get_previous_generation_backup(dialog_manager)
        original_image_backup = self.dialog_data_helper.get_original_image_backup(dialog_manager)

        if not previous_generation_backup and not original_image_backup:
            if combined_image_result_url:
                backup_dict = {
                    "type": "url",
                    "value": combined_image_result_url
                }
                self.dialog_data_helper.set_original_image_backup(dialog_manager, backup_dict)
            elif generated_images_url:
                backup_dict = {
                    "type": "url",
                    "value": generated_images_url,
                    "index": 0
                }
                self.dialog_data_helper.set_previous_generation_backup(dialog_manager, backup_dict)

        return combine_images_list

    # ============= МЕТОДЫ ДЛЯ NEW IMAGE CONFIRM =============

    def create_image_backup_dict(self, dialog_manager: DialogManager) -> dict | None:
        working_pub = self.dialog_data_helper.get_working_publication_safe(dialog_manager)
        custom_image_file_id = working_pub.get("custom_image_file_id")

        if custom_image_file_id:
            return {
                "type": "file_id",
                "value": custom_image_file_id
            }

        publication_images_url = working_pub.get("generated_images_url")
        if publication_images_url:
            current_index = working_pub.get("current_image_index", 0)
            return {
                "type": "url",
                "value": publication_images_url,
                "index": current_index
            }

        # Проверяем оригинальное изображение публикации
        image_url = working_pub.get("image_url")
        if image_url:
            return {
                "type": "url",
                "value": image_url
            }

        return None

    def create_new_image_backup_dict(self, dialog_manager: DialogManager) -> dict | None:
        """Создает backup из новых сгенерированных изображений в new_image_confirm"""
        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_result = self.dialog_data_helper.get_combined_image_result_url(dialog_manager)

        if combined_image_result:
            return {
                "type": "url",
                "value": combined_image_result
            }
        elif generated_images_url:
            return {
                "type": "url",
                "value": generated_images_url,
                "index": 0
            }

        return None

    def backup_current_image(self, dialog_manager: DialogManager) -> None:
        """
        Создает два типа backup:
        1. original_image_backup - создается только один раз для восстановления при "Отклонить"
        2. previous_generation_backup - обновляется при каждой генерации для показа "старой" картинки
        """
        # Создаем original_image_backup только если его еще нет (первая генерация)
        original_backup = self.dialog_data_helper.get_original_image_backup(dialog_manager)
        if not original_backup:
            # Это первая генерация - сохраняем текущую картинку публикации
            original_backup = self.create_image_backup_dict(dialog_manager=dialog_manager)
            self.dialog_data_helper.set_original_image_backup(dialog_manager, original_backup)

        # Создаем previous_generation_backup - сохраняем текущее состояние new_image_confirm
        # Если там есть картинка (это не первая генерация), сохраняем её
        # Если там пусто (первая генерация), сохраняем текущую картинку публикации
        new_image_backup = self.create_new_image_backup_dict(dialog_manager)
        if new_image_backup:
            self.dialog_data_helper.set_previous_generation_backup(dialog_manager, new_image_backup)
        else:
            # Первая генерация - используем текущую картинку публикации
            current_backup = self.create_image_backup_dict(dialog_manager=dialog_manager)
            self.dialog_data_helper.set_previous_generation_backup(dialog_manager, current_backup)

    def restore_image_from_backup(
            self,
            dialog_manager: DialogManager,
            backup_dict: dict | None
    ) -> None:
        if not backup_dict:
            self.clear_image_data(dialog_manager)
            return

        if backup_dict["type"] == "file_id":
            self.dialog_data_helper.set_working_custom_image(dialog_manager, backup_dict["value"])
            self.dialog_data_helper.set_working_image_has_image(dialog_manager, True)
            self.dialog_data_helper.remove_working_image_fields(
                dialog_manager,
                "generated_images_url",
                "current_image_index"
            )
        elif backup_dict["type"] == "url":
            value = backup_dict["value"]
            if isinstance(value, list):
                index = backup_dict.get("index", 0)
                self.dialog_data_helper.set_working_generated_images(dialog_manager, value)
                self.dialog_data_helper.set_working_image_index(dialog_manager, index)
            else:
                self.dialog_data_helper.set_working_generated_images(dialog_manager, [value])
                self.dialog_data_helper.set_working_image_index(dialog_manager, 0)
            self.dialog_data_helper.set_working_image_has_image(dialog_manager, True)
            self.dialog_data_helper.remove_working_image_fields(
                dialog_manager,
                "custom_image_file_id"
            )

    def get_new_image_confirm_media(
            self,
            dialog_manager: DialogManager
    ) -> tuple[MediaAttachment | None, MediaAttachment | None, bool]:
        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_result_url = self.dialog_data_helper.get_combined_image_result_url(dialog_manager)

        previous_generation_backup = self.dialog_data_helper.get_previous_generation_backup(dialog_manager)
        original_image_backup = self.dialog_data_helper.get_original_image_backup(dialog_manager)
        old_image_backup = previous_generation_backup or original_image_backup

        showing_old_image = self.dialog_data_helper.get_showing_old_image(dialog_manager)

        new_image_media = None
        old_image_media = None

        if combined_image_result_url:
            new_image_media = MediaAttachment(
                url=combined_image_result_url,
                type=ContentType.PHOTO
            )
        elif generated_images_url and len(generated_images_url) > 0:
            new_image_media = MediaAttachment(
                url=generated_images_url[0],
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


    def update_image_after_edit_from_confirm_new_image(
            self,
            dialog_manager: DialogManager,
            images_url: list[str]
    ) -> None:
        combined_image_result_url = self.dialog_data_helper.get_combined_image_result_url(dialog_manager)
        if combined_image_result_url:
            new_url = images_url[0] if images_url else None
            self.dialog_data_helper.set_combined_image_result_url(dialog_manager, new_url)
        else:
            generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
            if generated_images_url:
                self.dialog_data_helper.set_generated_images_url(dialog_manager, images_url)

    def confirm_new_image(self, dialog_manager: DialogManager) -> None:
        """Подтверждение нового изображения"""
        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_result_url = self.dialog_data_helper.get_combined_image_result_url(dialog_manager)

        if combined_image_result_url:
            self.dialog_data_helper.set_working_generated_images(dialog_manager, [combined_image_result_url])
            self.dialog_data_helper.set_working_image_has_image(dialog_manager, True)
            self.dialog_data_helper.set_working_image_index(dialog_manager, 0)
            self.dialog_data_helper.remove_working_image_fields(
                dialog_manager,
                "custom_image_file_id",
                "is_custom_image",
                "image_url"
            )
        elif generated_images_url:
            self.dialog_data_helper.set_working_generated_images(dialog_manager, generated_images_url)
            self.dialog_data_helper.set_working_image_has_image(dialog_manager, True)
            self.dialog_data_helper.set_working_image_index(dialog_manager, 0)
            self.dialog_data_helper.remove_working_image_fields(
                dialog_manager,
                "custom_image_file_id",
                "is_custom_image",
                "image_url"
            )

        self.dialog_data_helper.clear_temporary_image_data(dialog_manager)

    def reject_new_image(self, dialog_manager: DialogManager) -> None:
        # При отклонении всегда возвращаемся к самой первой картинке
        original_image_backup = self.dialog_data_helper.get_original_image_backup(dialog_manager)

        self.restore_image_from_backup(
            dialog_manager=dialog_manager,
            backup_dict=original_image_backup
        )
        # Очищаем данные текущей итерации, но сохраняем original_image_backup
        self.dialog_data_helper.clear_new_image_confirm_data(dialog_manager)

    def toggle_showing_old_image(
            self,
            dialog_manager: DialogManager,
            show_old: bool
    ) -> None:
        self.dialog_data_helper.set_showing_old_image(dialog_manager, show_old)

    # ============= МЕТОДЫ ДЛЯ ГЕНЕРАЦИИ С РЕФЕРЕНСАМИ =============

    async def generate_image_with_reference(
            self,
            dialog_manager: DialogManager,
            prompt: str,
            organization_id: int,
    ) -> list[str]:
        """Генерация изображения с использованием референсного изображения"""
        self.backup_current_image(dialog_manager)

        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)
        category_id = working_pub["category_id"]
        publication_text = working_pub["text"]

        reference_generation_image_file_id = self.dialog_data_helper.get_reference_generation_image_file_id(
            dialog_manager
        )

        image_content = None
        image_filename = None
        if reference_generation_image_file_id:
            image_io = await self.bot.download(reference_generation_image_file_id)
            image_content = image_io.read()
            image_filename = f"{reference_generation_image_file_id}.jpg"

        images_url = await self.loom_content_client.generate_publication_image(
            category_id=category_id,
            publication_text=publication_text,
            text_reference="",
            prompt=prompt,
            image_content=image_content,
            image_filename=image_filename,
        )

        return images_url

    async def use_current_image_as_reference(
            self,
            dialog_manager: DialogManager,
            chat_id: int
    ) -> str | None:
        """
        Использует текущее изображение публикации в качестве референса для генерации.
        Возвращает file_id изображения или None в случае ошибки.
        """
        working_pub = self.dialog_data_helper.get_working_publication_safe(dialog_manager)
        custom_image_file_id = working_pub.get("custom_image_file_id")

        if custom_image_file_id:
            # Если есть кастомное изображение, используем его
            return custom_image_file_id
        else:
            # Если изображение сгенерированное, конвертируем URL в file_id
            publication_images_url = working_pub.get("generated_images_url")
            if publication_images_url:
                current_index = working_pub.get("current_image_index", 0)
                if current_index < len(publication_images_url):
                    current_url = publication_images_url[current_index]

                    # Загружаем изображение и получаем file_id
                    file_id = await self.download_and_get_file_id(
                        image_url=current_url,
                        chat_id=chat_id
                    )

                    return file_id

        return None

import aiohttp
from aiogram import Bot
from aiogram.types import BufferedInputFile, ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId

from internal import interface, model
from pkg.tg_action_wrapper import tg_action
from internal.dialog.content.generate_publication.helpers.dialog_data_helper import DialogDataHelper


class ImageManager:
    def __init__(
            self,
            logger,
            bot: Bot,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.logger = logger
        self.bot = bot
        self.loom_content_client = loom_content_client
        self.dialog_data_helper = DialogDataHelper(self.logger)

    def navigate_images(
            self,
            dialog_manager: DialogManager,
            images_key: str,
            index_key: str,
            direction: str
    ) -> None:
        # Используем геттеры для получения данных
        if images_key == "publication_images_url":
            images_list = self.dialog_data_helper.get_publication_images_url(dialog_manager)
            current_index = self.dialog_data_helper.get_current_image_index(dialog_manager)
        elif images_key == "combine_images_list":
            images_list = self.dialog_data_helper.get_combine_images_list(dialog_manager)
            current_index = self.dialog_data_helper.get_combine_current_index(dialog_manager)
        else:
            # Fallback для неизвестных ключей
            images_list = []
            current_index = 0

        if direction == "next":
            new_index = current_index + 1 if current_index < len(images_list) - 1 else 0
        else:  # prev
            new_index = current_index - 1 if current_index > 0 else len(images_list) - 1

        # Используем сеттеры для установки нового индекса
        if index_key == "current_image_index":
            self.dialog_data_helper.set_current_image_index(dialog_manager, new_index)
        elif index_key == "combine_current_index":
            self.dialog_data_helper.set_combine_current_index(dialog_manager, new_index)

    def create_image_backup_dict(self, dialog_manager: DialogManager) -> dict | None:
        custom_image_file_id = self.dialog_data_helper.get_custom_image_file_id(dialog_manager)
        if custom_image_file_id:
            return {
                "type": "file_id",
                "value": custom_image_file_id
            }

        publication_images_url = self.dialog_data_helper.get_publication_images_url(dialog_manager)
        if publication_images_url:
            current_index = self.dialog_data_helper.get_current_image_index(dialog_manager)
            return {
                "type": "url",
                "value": publication_images_url,
                "index": current_index
            }
        return None

    def create_new_image_backup_dict(self, dialog_manager: DialogManager) -> dict | None:
        """Создает backup из новых сгенерированных изображений в new_image_confirm"""
        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_url = self.dialog_data_helper.get_combined_image_url(dialog_manager)

        if generated_images_url:
            return {
                "type": "url",
                "value": generated_images_url,
                "index": 0
            }
        elif combined_image_url:
            return {
                "type": "url",
                "value": combined_image_url
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
            original_backup = self.create_image_backup_dict(dialog_manager)
            self.dialog_data_helper.set_original_image_backup(dialog_manager, original_backup)

        # Создаем previous_generation_backup - сохраняем текущее состояние new_image_confirm
        # Если там есть картинка (это не первая генерация), сохраняем её
        # Если там пусто (первая генерация), сохраняем текущую картинку публикации
        new_image_backup = self.create_new_image_backup_dict(dialog_manager)
        if new_image_backup:
            self.dialog_data_helper.set_previous_generation_backup(dialog_manager, new_image_backup)
        else:
            # Первая генерация - используем текущую картинку публикации
            current_backup = self.create_image_backup_dict(dialog_manager)
            self.dialog_data_helper.set_previous_generation_backup(dialog_manager, current_backup)


    def set_generated_images(self, dialog_manager: DialogManager, images_url: list[str]) -> None:
        self.dialog_data_helper.set_publication_images_url(dialog_manager, images_url, 0)
        self.dialog_data_helper.set_has_image(dialog_manager, True)
        self.dialog_data_helper.set_is_custom_image(dialog_manager, False)
        self.dialog_data_helper.remove_field(dialog_manager, "custom_image_file_id")

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
            custom_image_file_id = self.dialog_data_helper.get_custom_image_file_id(dialog_manager)
            if custom_image_file_id:
                image_content = await self.bot.download(custom_image_file_id)
                return image_content.read(), f"{custom_image_file_id}.jpg"

            publication_images_url = self.dialog_data_helper.get_publication_images_url(dialog_manager)
            if publication_images_url:
                current_index = self.dialog_data_helper.get_current_image_index(dialog_manager)

                if current_index < len(publication_images_url):
                    current_url = publication_images_url[current_index]
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
        custom_image_file_id = self.dialog_data_helper.get_custom_image_file_id(dialog_manager)
        if custom_image_file_id:
            image_content = await self.bot.download(custom_image_file_id)
            return None, image_content.read(), f"{custom_image_file_id}.jpg"

        publication_images_url = self.dialog_data_helper.get_publication_images_url(dialog_manager)
        if publication_images_url:
            current_index = self.dialog_data_helper.get_current_image_index(dialog_manager)

            if current_index < len(publication_images_url):
                selected_url = publication_images_url[current_index]
                return selected_url, None, None

        return None, None, None

    def restore_image_from_backup(
            self,
            dialog_manager: DialogManager,
            backup_dict: dict | None
    ) -> None:
        if not backup_dict:
            self.dialog_data_helper.clear_all_image_data(dialog_manager)
            return

        if backup_dict["type"] == "file_id":
            self.dialog_data_helper.set_custom_image_file_id(dialog_manager, backup_dict["value"])
            self.dialog_data_helper.set_has_image(dialog_manager, True)
            self.dialog_data_helper.set_is_custom_image(dialog_manager, True)
            self.dialog_data_helper.remove_field(dialog_manager, "publication_images_url")
            self.dialog_data_helper.remove_field(dialog_manager, "current_image_index")
        elif backup_dict["type"] == "url":
            value = backup_dict["value"]
            if isinstance(value, list):
                index = backup_dict.get("index", 0)
                self.dialog_data_helper.set_publication_images_url(dialog_manager, value, index)
            else:
                self.dialog_data_helper.set_publication_images_url(dialog_manager, [value], 0)
            self.dialog_data_helper.set_has_image(dialog_manager, True)
            self.dialog_data_helper.set_is_custom_image(dialog_manager, False)
            self.dialog_data_helper.remove_field(dialog_manager, "custom_image_file_id")

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

        custom_image_file_id = self.dialog_data_helper.get_custom_image_file_id(dialog_manager)
        if custom_image_file_id:
            combine_images_list.append(custom_image_file_id)
        else:
            publication_images_url = self.dialog_data_helper.get_publication_images_url(dialog_manager)
            if publication_images_url:
                current_index = self.dialog_data_helper.get_current_image_index(dialog_manager)
                if current_index < len(publication_images_url):
                    current_url = publication_images_url[current_index]
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

        custom_image_file_id = self.dialog_data_helper.get_custom_image_file_id(dialog_manager)
        if custom_image_file_id:
            self.logger.info("Используется кастомное изображение")
            preview_image_media = MediaAttachment(
                file_id=MediaId(custom_image_file_id),
                type=ContentType.PHOTO
            )
        else:
            publication_images_url = self.dialog_data_helper.get_publication_images_url(dialog_manager)
            if publication_images_url:
                self.logger.info("Используется сгенерированное изображение")
                current_image_index = self.dialog_data_helper.get_current_image_index(dialog_manager)
                total_images = len(publication_images_url)
                has_multiple_images = total_images > 1

                if current_image_index < len(publication_images_url):
                    preview_image_media = MediaAttachment(
                        url=publication_images_url[current_image_index],
                        type=ContentType.PHOTO
                    )

        return preview_image_media, has_multiple_images, current_image_index, total_images

    def get_image_menu_media(self, dialog_manager: DialogManager) -> MediaAttachment | None:
        custom_image_file_id = self.dialog_data_helper.get_custom_image_file_id(dialog_manager)
        if custom_image_file_id:
            return MediaAttachment(
                file_id=MediaId(custom_image_file_id),
                type=ContentType.PHOTO
            )

        publication_images_url = self.dialog_data_helper.get_publication_images_url(dialog_manager)
        if publication_images_url:
            current_image_index = self.dialog_data_helper.get_current_image_index(dialog_manager)

            if current_image_index < len(publication_images_url):
                return MediaAttachment(
                    url=publication_images_url[current_image_index],
                    type=ContentType.PHOTO
                )
        return None

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

    def get_new_image_confirm_media(
            self,
            dialog_manager: DialogManager
    ) -> tuple[MediaAttachment | None, MediaAttachment | None, bool]:
        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_url = self.dialog_data_helper.get_combined_image_url(dialog_manager)

        old_image_backup = self.dialog_data_helper.get_previous_generation_backup(dialog_manager)

        showing_old_image = self.dialog_data_helper.get_showing_old_image(dialog_manager)

        new_image_media = None
        old_image_media = None

        if generated_images_url and len(generated_images_url) > 0:
            new_image_media = MediaAttachment(
                url=generated_images_url[0],
                type=ContentType.PHOTO
            )
        elif combined_image_url:
            new_image_media = MediaAttachment(
                url=combined_image_url,
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

    async def generate_new_image(
            self,
            dialog_manager: DialogManager,
    ) -> list[str]:
        self.backup_current_image(dialog_manager)

        category_id = self.dialog_data_helper.get_category_id(dialog_manager)
        publication_text = self.dialog_data_helper.get_publication_text(dialog_manager)
        generate_text_prompt = self.dialog_data_helper.get_generate_text_prompt(dialog_manager)

        images_url, has_no_data = await self.loom_content_client.generate_publication_image(
            category_id=category_id,
            publication_text=publication_text,
            text_reference=generate_text_prompt,
        )

        # Если нейросеть не стала генерировать изображение
        if has_no_data:
            self.dialog_data_helper.set_has_no_generate_image_result(dialog_manager, True)
            return []

        return images_url

    async def edit_image_with_prompt(
            self,
            dialog_manager: DialogManager,
            organization_id: int,
            prompt: str,
    ) -> list[str]:
        self.backup_current_image(dialog_manager)

        current_image_content = None
        current_image_filename = None

        if await self.get_current_image_data(dialog_manager=dialog_manager):
            current_image_content, current_image_filename = await self.get_current_image_data(
                dialog_manager=dialog_manager
            )

        images_url, has_no_data = await self.loom_content_client.edit_image(
            organization_id=organization_id,
            prompt=prompt,
            image_content=current_image_content,
            image_filename=current_image_filename,
        )

        # Если нейросеть не стала редактировать изображение
        if has_no_data:
            self.dialog_data_helper.set_has_no_image_edit_result(dialog_manager, True)
            return []

        return images_url

    async def generate_image_with_reference(
            self,
            dialog_manager: DialogManager,
            prompt: str,
    ) -> list[str]:
        self.backup_current_image(dialog_manager)

        category_id = self.dialog_data_helper.get_category_id(dialog_manager)
        publication_text = self.dialog_data_helper.get_publication_text(dialog_manager)
        generate_text_prompt = self.dialog_data_helper.get_generate_text_prompt(dialog_manager)
        reference_generation_image_file_id = self.dialog_data_helper.get_reference_generation_image_file_id(
            dialog_manager
        )

        image_content = None
        image_filename = None
        if reference_generation_image_file_id:
            image_io = await self.bot.download(reference_generation_image_file_id)
            image_content = image_io.read()
            image_filename = f"{reference_generation_image_file_id}.jpg"

        images_url, has_no_data = await self.loom_content_client.generate_publication_image(
            category_id=category_id,
            publication_text=publication_text,
            text_reference=generate_text_prompt,
            prompt=prompt,
            image_content=image_content,
            image_filename=image_filename,
        )

        # Если нейросеть не стала генерировать изображение
        if has_no_data:
            self.dialog_data_helper.set_has_no_generate_image_result(dialog_manager, True)
            return []

        return images_url

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

    async def process_combine_with_prompt(
            self,
            dialog_manager: DialogManager,
            state: model.UserState,
            combine_images_list: list[str],
            prompt: str,
            chat_id: int
    ) -> str | None:
        # Сохраняем backups как при обычной генерации
        self.backup_current_image(dialog_manager)

        images_content = []
        images_filenames = []

        for i, file_id in enumerate(combine_images_list):
            image_io = await self.bot.download(file_id)
            content = image_io.read()
            images_content.append(content)
            images_filenames.append(f"image_{i}.jpg")

        category_id = self.dialog_data_helper.get_category_id(dialog_manager)

        async with tg_action(self.bot, chat_id, "upload_photo"):
            combined_images_url, has_no_data = await self.loom_content_client.combine_images(
                organization_id=state.organization_id,
                category_id=category_id,
                images_content=images_content,
                images_filenames=images_filenames,
                prompt=prompt,
            )

        # Если нейросеть не стала объединять изображения
        if has_no_data:
            self.dialog_data_helper.set_has_no_combine_image_result(dialog_manager, True)
            return None

        return combined_images_url[0] if combined_images_url else None

    async def prepare_new_image_for_combine(
            self,
            dialog_manager: DialogManager,
            chat_id: int
    ) -> list[str]:
        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_url = self.dialog_data_helper.get_combined_image_url(dialog_manager)

        image_url = None
        if generated_images_url and len(generated_images_url) > 0:
            image_url = generated_images_url[0]
        elif combined_image_url:
            image_url = combined_image_url

        combine_images_list = []
        if image_url:
            file_id = await self.download_and_get_file_id(
                image_url=image_url,
                chat_id=chat_id
            )
            if file_id:
                combine_images_list.append(file_id)
                self.logger.info(f"Новая картинка добавлена в список для объединения: {file_id}")

        return combine_images_list

    def should_return_to_new_image_confirm(self, dialog_manager: DialogManager) -> bool:
        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_url = self.dialog_data_helper.get_combined_image_url(dialog_manager)
        return generated_images_url is not None or combined_image_url is not None

    async def edit_new_image_with_prompt(
            self,
            dialog_manager: DialogManager,
            organization_id: int,
            prompt: str,
    ) -> list[str]:
        # Создаем backup текущего изображения перед редактированием
        self.backup_current_image(dialog_manager)

        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_url = self.dialog_data_helper.get_combined_image_url(dialog_manager)

        image_url = None
        if generated_images_url and len(generated_images_url) > 0:
            image_url = generated_images_url[0]
        elif combined_image_url:
            image_url = combined_image_url

        current_image_content = None
        current_image_filename = None
        if image_url:
            current_image_content, _ = await self.download_image(image_url)
            current_image_filename = "current_image.jpg"

        images_url, has_no_data = await self.loom_content_client.edit_image(
                organization_id=organization_id,
                prompt=prompt,
                image_content=current_image_content,
                image_filename=current_image_filename,
            )

        # Если нейросеть не стала редактировать изображение
        if has_no_data:
            self.dialog_data_helper.set_has_no_image_edit_result(dialog_manager, True)
            return []

        return images_url

    def update_image_after_edit_from_confirm_new_image(
            self,
            dialog_manager: DialogManager,
            images_url: list[str]
    ) -> None:
        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        if generated_images_url:
            self.dialog_data_helper.set_generated_images_url(dialog_manager, images_url)
        else:
            combined_image_url = self.dialog_data_helper.get_combined_image_url(dialog_manager)
            if combined_image_url:
                new_url = images_url[0] if images_url else None
                self.dialog_data_helper.set_combine_image_url(dialog_manager, new_url)

    def confirm_new_image(self, dialog_manager: DialogManager) -> None:
        """Подтверждение нового изображения"""
        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_url = self.dialog_data_helper.get_combined_image_url(dialog_manager)

        if generated_images_url:
            self.set_generated_images(
                dialog_manager=dialog_manager,
                images_url=generated_images_url
            )
        elif combined_image_url:
            self.set_generated_images(
                dialog_manager=dialog_manager,
                images_url=[combined_image_url]
            )

        # Очищаем original_image_backup при подтверждении
        self.dialog_data_helper.set_original_image_backup(dialog_manager, None)
        self.dialog_data_helper.clear_temporary_image_data(dialog_manager)

    def reject_new_image(self, dialog_manager: DialogManager) -> None:
        backup_dict = self.dialog_data_helper.get_original_image_backup(dialog_manager)

        self.restore_image_from_backup(
            dialog_manager=dialog_manager,
            backup_dict=backup_dict
        )
        # Очищаем original_image_backup при отклонении
        self.dialog_data_helper.set_original_image_backup(dialog_manager, None)
        self.dialog_data_helper.clear_temporary_image_data(dialog_manager)

    async def use_current_image_as_reference(
            self,
            dialog_manager: DialogManager,
            chat_id: int
    ) -> str | None:
        """
        Использует текущее изображение публикации в качестве референса для генерации.
        Возвращает file_id изображения или None в случае ошибки.
        """
        custom_image_file_id = self.dialog_data_helper.get_custom_image_file_id(dialog_manager)

        if custom_image_file_id:
            # Если есть кастомное изображение, используем его
            return custom_image_file_id
        else:
            # Если изображение сгенерированное, конвертируем URL в file_id
            publication_images_url = self.dialog_data_helper.get_publication_images_url(dialog_manager)
            if publication_images_url:
                current_index = self.dialog_data_helper.get_current_image_index(dialog_manager)
                if current_index < len(publication_images_url):
                    current_url = publication_images_url[current_index]

                    # Загружаем изображение и получаем file_id
                    file_id = await self.download_and_get_file_id(
                        image_url=current_url,
                        chat_id=chat_id
                    )

                    return file_id

        return None

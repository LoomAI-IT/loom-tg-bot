from aiogram import Bot
from aiogram_dialog import DialogManager

from internal import interface, model
from internal.dialog.content.draft_publication.helpers.dialog_data_helper import DialogDataHelper
from internal.dialog.content.draft_publication.helpers.state_restorer import StateRestorer
from internal.dialog.content.draft_publication.helpers.image_manager import ImageManager


class PublicationManager:
    def __init__(
            self,
            logger,
            bot: Bot,
            loom_content_client: interface.ILoomContentClient,
            state_restorer: StateRestorer,
            image_manager: ImageManager,
    ):
        self.logger = logger
        self.bot = bot
        self.loom_content_client = loom_content_client
        self.state_restorer = state_restorer
        self.image_manager = image_manager
        self.dialog_data_helper = DialogDataHelper()

    def has_changes(self, dialog_manager: DialogManager) -> bool:
        original = self.dialog_data_helper.get_original_publication_safe(dialog_manager)
        working = self.dialog_data_helper.get_working_publication_safe(dialog_manager)

        if not original or not working:
            return False

        # Сравниваем текстовые поля
        if original.get("text") != working.get("text"):
            return True

        # Проверяем изменения изображения
        if original.get("has_image", False) != working.get("has_image", False):
            return True

        # Если есть пользовательское изображение - проверяем file_id
        if working.get("custom_image_file_id"):
            if original.get("custom_image_file_id") != working.get("custom_image_file_id"):
                return True

        # Проверяем изменение URL изображения
        original_url = original.get("image_url", "")
        working_url = working.get("image_url", "")

        if working_url and original_url:
            if original_url != working_url:
                return True
        elif working_url != original_url:
            return True

        return False

    async def save_publication_changes(self, dialog_manager: DialogManager) -> None:
        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)
        original_pub = self.dialog_data_helper.get_original_publication(dialog_manager)
        publication_id = working_pub["id"]

        # Определяем, что делать с изображением
        image_url = None
        image_content = None
        image_filename = None
        should_delete_image = False

        # Проверяем изменения изображения
        original_has_image = original_pub.get("has_image", False)
        working_has_image = working_pub.get("has_image", False)

        if not working_has_image and original_has_image:
            # Изображение было удалено
            should_delete_image = True

        elif working_has_image:
            # Проверяем тип изображения и получаем выбранное
            if working_pub.get("custom_image_file_id"):
                # Пользовательское изображение
                image_content = await self.bot.download(working_pub["custom_image_file_id"])
                image_filename = working_pub["custom_image_file_id"] + ".jpg"

            elif working_pub.get("generated_images_url"):
                # Выбранное из множественных сгенерированных
                images_url = working_pub["generated_images_url"]
                current_index = working_pub.get("current_image_index", 0)

                if current_index < len(images_url):
                    selected_url = images_url[current_index]
                    # Проверяем, изменилось ли изображение
                    original_url = original_pub.get("image_url", "")
                    if original_url != selected_url:
                        image_url = selected_url

            elif working_pub.get("image_url"):
                # Одиночное изображение
                original_url = original_pub.get("image_url", "")
                working_url = working_pub.get("image_url", "")

                if original_url != working_url:
                    image_url = working_url

        # Если нужно удалить изображение
        if should_delete_image:
            try:
                await self.loom_content_client.delete_publication_image(
                    publication_id=publication_id
                )
            except Exception as e:
                self.logger.error(f"Ошибка при удалении изображения: {e}")

        # Обновляем публикацию через API
        if image_url or image_content:
            await self.loom_content_client.change_publication(
                publication_id=publication_id,
                text=working_pub["text"],
                image_url=image_url,
                image_content=image_content,
                image_filename=image_filename,
            )
        else:
            # Обновляем только текстовые поля
            await self.loom_content_client.change_publication(
                publication_id=publication_id,
                text=working_pub["text"],
            )

    def remove_current_publication_from_list(self, dialog_manager: DialogManager) -> None:
        draft_list = self.dialog_data_helper.get_draft_list(dialog_manager)
        current_index = self.dialog_data_helper.get_current_index(dialog_manager)

        if draft_list and current_index < len(draft_list):
            draft_list.pop(current_index)

            # Корректируем индекс если нужно
            if current_index >= len(draft_list) and draft_list:
                self.dialog_data_helper.set_current_index(dialog_manager, len(draft_list) - 1)
            elif not draft_list:
                self.dialog_data_helper.set_current_index(dialog_manager, 0)

            # Сбрасываем рабочие данные
            self.dialog_data_helper.clear_working_publication_from_data(dialog_manager)
            self.dialog_data_helper.clear_selected_networks(dialog_manager)

    async def reject_publication(
            self,
            dialog_manager: DialogManager,
            state: model.UserState,
    ) -> None:
        _, publication_id, reject_comment = self.dialog_data_helper.get_reject_comment_data(dialog_manager)
        await self.loom_content_client.moderate_publication(
            publication_id=publication_id,
            moderator_id=state.account_id,
            moderation_status="rejected",
            moderation_comment=reject_comment,
        )

    async def generate_text(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        self.state_restorer.save_state_before_modification(dialog_manager, include_image=False)

        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)
        return await self.loom_content_client.regenerate_publication_text(
            category_id=working_pub["category_id"],
            publication_text=working_pub["text"],
            prompt="Используй тему поста, но сгенерируй пост по-другому как-нибудь не меняя смысл"
        )

    async def regenerate_text(
            self,
            dialog_manager: DialogManager,
            prompt: str,
    ) -> dict:
        self.state_restorer.save_state_before_modification(dialog_manager, include_image=False)

        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)
        return await self.loom_content_client.regenerate_publication_text(
            category_id=working_pub["category_id"],
            publication_text=working_pub["text"],
            prompt=prompt,
        )

    async def compress_text(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)
        expected_length = self.dialog_data_helper.get_expected_length(dialog_manager)

        compress_prompt = f"Сожми текст до {expected_length} символов, сохраняя основной смысл и ключевые идеи. МАКСИМАЛЬНО ЗАПРЕЩЕНО ДЕЛАТЬ ТЕКСТ ДЛИННЕЕ {expected_length} символов"
        return await self.loom_content_client.regenerate_publication_text(
            category_id=working_pub["category_id"],
            publication_text=working_pub["text"],
            prompt=compress_prompt
        )


    async def generate_image(
            self,
            dialog_manager: DialogManager,
    ) -> list[str]:
        self.state_restorer.save_state_before_modification(dialog_manager, include_image=True)
        self.image_manager.backup_current_image(dialog_manager)

        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)
        current_image_content, current_image_filename = await self.image_manager.prepare_current_image_for_generation(
            dialog_manager
        )

        return await self.loom_content_client.generate_publication_image(
            category_id=working_pub["category_id"],
            publication_text=working_pub["text"],
            text_reference=working_pub["text"][:100],
            image_content=current_image_content,
            image_filename=current_image_filename,
        )

    async def edit_image(
            self,
            dialog_manager: DialogManager,
            organization_id: int,
            edit_image_prompt: str
    ) -> list[str]:
        self.state_restorer.save_state_before_modification(dialog_manager, include_image=True)
        self.image_manager.backup_current_image(dialog_manager)
        current_image_content, current_image_filename = await self.image_manager.prepare_current_image_for_generation(
            dialog_manager
        )

        image_urls, has_no_data = await self.loom_content_client.edit_image(
            organization_id=organization_id,
            prompt=edit_image_prompt,
            image_content=current_image_content,
            image_filename=current_image_filename,
        )

        return image_urls

    async def edit_new_image_with_prompt(
            self,
            dialog_manager: DialogManager,
            organization_id: int,
            prompt: str,
    ) -> list[str]:
        self.image_manager.backup_current_image(dialog_manager)

        generated_images_url = self.dialog_data_helper.get_generated_images_url(dialog_manager)
        combined_image_result_url = self.dialog_data_helper.get_combined_image_result_url(dialog_manager)

        image_url = None
        if combined_image_result_url:
            image_url = combined_image_result_url
        elif generated_images_url and len(generated_images_url) > 0:
            image_url = generated_images_url[0]

        current_image_content = None
        current_image_filename = None
        if image_url:
            current_image_content, _ = await self.image_manager.download_image(image_url)
            current_image_filename = "current_image.jpg"

        images_url, has_no_data = await self.loom_content_client.edit_image(
            organization_id=organization_id,
            prompt=prompt,
            image_content=current_image_content,
            image_filename=current_image_filename,
        )

        return images_url

    async def combine_images(
            self,
            dialog_manager: DialogManager,
            prompt: str,
            organization_id: int,
    ) -> str | None:
        self.image_manager.backup_current_image(dialog_manager)

        images_content = []
        images_filenames = []
        combine_images_list = self.dialog_data_helper.get_combine_images_list(dialog_manager)
        for i, file_id in enumerate(combine_images_list):
            image_io = await self.bot.download(file_id)
            content = image_io.read()
            images_content.append(content)
            images_filenames.append(f"image_{i}.jpg")

        working_pub = self.dialog_data_helper.get_working_publication(dialog_manager)
        category_id = working_pub["category_id"]

        combined_images_url = await self.loom_content_client.combine_images(
            organization_id=organization_id,
            category_id=category_id,
            images_content=images_content,
            images_filenames=images_filenames,
            prompt=prompt,
        )

        return combined_images_url[0] if combined_images_url else None

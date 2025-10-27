from aiogram import Bot
from aiogram_dialog import DialogManager

from internal import interface, model
from internal.dialog.content.moderation_publication.helpers.dialog_data_helper import DialogDataHelper


class PublicationManager:
    def __init__(
            self,
            logger,
            bot: Bot,
            loom_content_client: interface.ILoomContentClient
    ):
        self.logger = logger
        self.bot = bot
        self.loom_content_client = loom_content_client
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

    async def approve_and_publish(
            self,
            dialog_manager: DialogManager,
            state: model.UserState,
    ) -> dict:
        original_pub = self.dialog_data_helper.get_original_publication(dialog_manager)
        publication_id = original_pub["id"]

        selected_networks = self.dialog_data_helper.get_selected_social_networks(dialog_manager)

        selected_sources = {
            "tg_source": selected_networks.get("telegram_checkbox", False),
            "vk_source": selected_networks.get("vkontakte_checkbox", False),
        }

        # Обновляем публикацию с выбранными соцсетями
        await self.loom_content_client.change_publication(
            publication_id=publication_id,
            tg_source=selected_sources["tg_source"],
            vk_source=selected_sources["vk_source"],
        )

        # Одобряем публикацию
        post_links = await self.loom_content_client.moderate_publication(
            publication_id=publication_id,
            moderator_id=state.account_id,
            moderation_status="approved",
        )

        return post_links

    def remove_current_publication_from_list(self, dialog_manager: DialogManager) -> None:
        moderation_list = self.dialog_data_helper.get_moderation_list(dialog_manager)
        current_index = self.dialog_data_helper.get_current_index(dialog_manager)

        if moderation_list and current_index < len(moderation_list):
            moderation_list.pop(current_index)

            # Корректируем индекс если нужно
            if current_index >= len(moderation_list) and moderation_list:
                self.dialog_data_helper.set_current_index(dialog_manager, len(moderation_list) - 1)
            elif not moderation_list:
                self.dialog_data_helper.set_current_index(dialog_manager, 0)

            # Сбрасываем рабочие данные
            self.dialog_data_helper.clear_working_publication_from_data(dialog_manager)
            self.dialog_data_helper.clear_selected_networks(dialog_manager)

    async def reject_publication(
            self,
            publication_id: int,
            moderator_id: int,
            comment: str
    ) -> None:
        await self.loom_content_client.moderate_publication(
            publication_id=publication_id,
            moderator_id=moderator_id,
            moderation_status="rejected",
            moderation_comment=comment,
        )

    async def regenerate_text(
            self,
            category_id: int,
            text: str,
            prompt: str | None = None
    ) -> dict:
        return await self.loom_content_client.regenerate_publication_text(
            category_id=category_id,
            publication_text=text,
            prompt=prompt
        )

    async def generate_image(
            self,
            category_id: int,
            publication_text: str,
            image_content: bytes | None = None,
            image_filename: str | None = None,
            prompt: str | None = None
    ) -> list[str]:
        return await self.loom_content_client.generate_publication_image(
            category_id=category_id,
            publication_text=publication_text,
            text_reference=publication_text[:200],
            prompt=prompt,
            image_content=image_content,
            image_filename=image_filename,
        )

    async def edit_image(
            self,
            organization_id: int,
            image_content: bytes | None = None,
            image_filename: str | None = None,
            prompt: str | None = None
    ) -> list[str]:
        return await self.loom_content_client.edit_image(
            organization_id=organization_id,
            prompt=prompt,
            image_content=image_content,
            image_filename=image_filename,
        )

    async def compress_text(
            self,
            category_id: int,
            text: str,
            expected_length: int
    ) -> dict:
        compress_prompt = f"Сожми текст до {expected_length} символов, сохраняя основной смысл и ключевые идеи"
        return await self.loom_content_client.regenerate_publication_text(
            category_id=category_id,
            publication_text=text,
            prompt=compress_prompt
        )

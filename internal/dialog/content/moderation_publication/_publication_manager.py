from aiogram import Bot
from aiogram_dialog import DialogManager

from internal import interface, model


class _PublicationManager:
    def __init__(
            self,
            logger,
            bot: Bot,
            loom_content_client: interface.ILoomContentClient
    ):
        self.logger = logger
        self.bot = bot
        self.loom_content_client = loom_content_client

    def has_changes(self, dialog_manager: DialogManager) -> bool:

        original = dialog_manager.dialog_data.get("original_publication", {})
        working = dialog_manager.dialog_data.get("working_publication", {})

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
        working_pub = dialog_manager.dialog_data["working_publication"]
        original_pub = dialog_manager.dialog_data["original_publication"]
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
        original_pub = dialog_manager.dialog_data["original_publication"]
        publication_id = original_pub["id"]

        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

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

    @staticmethod
    def remove_current_publication_from_list(dialog_manager: DialogManager) -> None:
        moderation_list = dialog_manager.dialog_data.get("moderation_list", [])
        current_index = dialog_manager.dialog_data.get("current_index", 0)

        if moderation_list and current_index < len(moderation_list):
            moderation_list.pop(current_index)

            # Корректируем индекс если нужно
            if current_index >= len(moderation_list) and moderation_list:
                dialog_manager.dialog_data["current_index"] = len(moderation_list) - 1
            elif not moderation_list:
                dialog_manager.dialog_data["current_index"] = 0

            # Сбрасываем рабочие данные
            dialog_manager.dialog_data.pop("working_publication", None)
            dialog_manager.dialog_data.pop("selected_networks", None)

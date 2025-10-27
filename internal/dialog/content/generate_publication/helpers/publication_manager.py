from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from internal import interface, model


class PublicationManager:
    def __init__(
            self,
            logger,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.logger = logger
        self.loom_content_client = loom_content_client

    async def send_to_moderation(
            self,
            state: model.UserState,
            category_id: int,
            text_reference: str,
            text: str,
            image_url: str | None,
            image_content: bytes | None,
            image_filename: str | None,
            selected_networks: dict
    ) -> dict:
        publication_data = await self.loom_content_client.create_publication(
            organization_id=state.organization_id,
            category_id=category_id,
            creator_id=state.account_id,
            text_reference=text_reference,
            text=text,
            moderation_status="moderation",
            image_url=image_url,
            image_content=image_content,
            image_filename=image_filename,
        )

        if selected_networks:
            self.logger.info("Установка выбранных соцсетей")
            tg_source = selected_networks.get("telegram_checkbox", False)
            vk_source = selected_networks.get("vkontakte_checkbox", False)

            await self.loom_content_client.change_publication(
                publication_id=publication_data["publication_id"],
                tg_source=tg_source,
                vk_source=vk_source,
            )

        return publication_data

    async def publish_now(
            self,
            dialog_manager: DialogManager,
            state: model.UserState,
            category_id: int,
            text_reference: str,
            text: str,
            image_url: str | None,
            image_content: bytes | None,
            image_filename: str | None,
            selected_networks: dict
    ) -> dict:
        # Создаем публикацию со статусом draft
        publication_data = await self.loom_content_client.create_publication(
            organization_id=state.organization_id,
            category_id=category_id,
            creator_id=state.account_id,
            text_reference=text_reference,
            text=text,
            moderation_status="draft",
            image_url=image_url,
            image_content=image_content,
            image_filename=image_filename,
        )

        # Устанавливаем выбранные соцсети
        tg_source = selected_networks.get("telegram_checkbox", False)
        vk_source = selected_networks.get("vkontakte_checkbox", False)

        await self.loom_content_client.change_publication(
            publication_id=publication_data["publication_id"],
            tg_source=tg_source,
            vk_source=vk_source,
        )

        # Модерируем публикацию (одобряем)
        post_links = await self.loom_content_client.moderate_publication(
            publication_id=publication_data["publication_id"],
            moderator_id=state.account_id,
            moderation_status="approved"
        )

        dialog_manager.dialog_data["post_links"] = post_links

        return publication_data

    async def add_to_drafts(
            self,
            dialog_manager: DialogManager,
            state: model.UserState,
            category_id: int,
            text_reference: str,
            text: str,
            image_url: str | None,
            image_content: bytes | None,
            image_filename: str | None,
            selected_networks: dict
    ) -> dict:
        publication_data = await self.loom_content_client.create_publication(
            organization_id=state.organization_id,
            category_id=category_id,
            creator_id=state.account_id,
            text_reference=text_reference,
            text=text,
            moderation_status="draft",
            image_url=image_url,
            image_content=image_content,
            image_filename=image_filename,
        )

        if selected_networks:
            tg_source = selected_networks.get("telegram_checkbox", False)
            vk_source = selected_networks.get("vkontakte_checkbox", False)

            await self.loom_content_client.change_publication(
                publication_id=publication_data["publication_id"],
                tg_source=tg_source,
                vk_source=vk_source,
            )

        return publication_data

    def toggle_social_network(
            self,
            checkbox: ManagedCheckbox,
            dialog_manager: DialogManager
    ) -> None:
        if "selected_social_networks" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["selected_social_networks"] = {}

        network_id = checkbox.widget_id
        is_checked = checkbox.is_checked()

        dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

    def remove_photo_from_long_text(self, dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data["has_image"] = False
        dialog_manager.dialog_data.pop("publication_images_url", None)
        dialog_manager.dialog_data.pop("custom_image_file_id", None)
        dialog_manager.dialog_data.pop("is_custom_image", None)
        dialog_manager.dialog_data.pop("current_image_index", None)
        self.logger.info("Изображение удалено из-за длинного текста")

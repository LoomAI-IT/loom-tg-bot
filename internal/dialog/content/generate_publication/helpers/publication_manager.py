from aiogram_dialog import DialogManager

from internal import interface, model
from internal.dialog.content.generate_publication.helpers import ImageManager
from internal.dialog.content.generate_publication.helpers.dialog_data_helper import DialogDataHelper


class PublicationManager:
    def __init__(
            self,
            logger,
            loom_content_client: interface.ILoomContentClient,
            image_manager: ImageManager,
    ):
        self.logger = logger
        self.loom_content_client = loom_content_client
        self.image_manager = image_manager
        self.dialog_data_helper = DialogDataHelper(self.logger)

    async def generate_publication_text(self, dialog_manager: DialogManager) -> str:
        category_id = self.dialog_data_helper.get_category_id(dialog_manager)
        generate_text_prompt = self.dialog_data_helper.get_generate_text_prompt(dialog_manager)

        publication_data = await self.loom_content_client.generate_publication_text(
            category_id=category_id,
            text_reference=generate_text_prompt,
        )

        return publication_data["text"]

    async def regenerate_publication_text(self, dialog_manager: DialogManager, regenerate_text_prompt: str) -> str:
        category_id = self.dialog_data_helper.get_category_id(dialog_manager)
        publication_text = self.dialog_data_helper.get_publication_text(dialog_manager)

        regenerated_data = await self.loom_content_client.regenerate_publication_text(
            category_id=category_id,
            publication_text=publication_text,
            prompt=regenerate_text_prompt
        )

        return regenerated_data["text"]

    async def compress_publication_text(self, dialog_manager: DialogManager) -> str:
        category_id = self.dialog_data_helper.get_category_id(dialog_manager)
        publication_text = self.dialog_data_helper.get_publication_text(dialog_manager)
        expected_length = self.dialog_data_helper.get_expected_length(dialog_manager)
        compress_prompt = f"Сожми текст до {expected_length} символов, сохраняя основной смысл и ключевые идеи. МАКСИМАЛЬНО ЗАПРЕЩЕНО ДЕЛАТЬ ТЕКСТ ДЛИННЕЕ {expected_length} символов"

        compressed_data = await self.loom_content_client.regenerate_publication_text(
            category_id=category_id,
            publication_text=publication_text,
            prompt=compress_prompt
        )

        return compressed_data["text"]

    async def send_to_moderation(
            self,
            dialog_manager: DialogManager,
            state: model.UserState,
    ) -> dict:
        text = self.dialog_data_helper.get_publication_text(dialog_manager)
        category_id = self.dialog_data_helper.get_category_id(dialog_manager)
        selected_networks = self.dialog_data_helper.get_selected_social_networks(dialog_manager)
        generate_text_prompt = self.dialog_data_helper.get_generate_text_prompt(dialog_manager)

        image_url, image_content, image_filename = await self.image_manager.get_selected_image_data(
            dialog_manager=dialog_manager
        )

        publication_data = await self.loom_content_client.create_publication(
            organization_id=state.organization_id,
            category_id=category_id,
            creator_id=state.account_id,
            text_reference=generate_text_prompt,
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
    ) -> dict:
        text = self.dialog_data_helper.get_publication_text(dialog_manager)
        category_id = self.dialog_data_helper.get_category_id(dialog_manager)
        generate_text_prompt = self.dialog_data_helper.get_generate_text_prompt(dialog_manager)
        selected_networks = self.dialog_data_helper.get_selected_social_networks(dialog_manager)

        image_url, image_content, image_filename = await self.image_manager.get_selected_image_data(
            dialog_manager=dialog_manager
        )

        publication_data = await self.loom_content_client.create_publication(
            organization_id=state.organization_id,
            category_id=category_id,
            creator_id=state.account_id,
            text_reference=generate_text_prompt,
            text=text,
            moderation_status="draft",
            image_url=image_url,
            image_content=image_content,
            image_filename=image_filename,
        )

        tg_source = selected_networks.get("telegram_checkbox", False)
        vk_source = selected_networks.get("vkontakte_checkbox", False)

        await self.loom_content_client.change_publication(
            publication_id=publication_data["publication_id"],
            tg_source=tg_source,
            vk_source=vk_source,
        )

        post_links = await self.loom_content_client.moderate_publication(
            publication_id=publication_data["publication_id"],
            moderator_id=state.account_id,
            moderation_status="approved"
        )

        self.dialog_data_helper.set_post_links(dialog_manager=dialog_manager, links=post_links)

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

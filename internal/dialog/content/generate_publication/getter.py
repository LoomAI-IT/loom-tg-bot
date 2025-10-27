from aiogram import Bot
from aiogram_dialog import DialogManager

from internal import interface
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method

from internal.dialog.helpers import StateManager

from internal.dialog.content.generate_publication.helpers import ImageManager, DataExtractor, SocialNetworkManager



class GeneratePublicationDataGetter(interface.IGeneratePublicationGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            loom_employee_client: interface.ILoomEmployeeClient,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.loom_employee_client = loom_employee_client
        self.loom_content_client = loom_content_client

        # Инициализация приватных сервисов
        self.state_manager = StateManager(
            state_repo=self.state_repo
        )
        self.image_manager = ImageManager(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client,
        )
        self.social_network_manager = SocialNetworkManager(
            logger=self.logger,
            loom_content_client=self.loom_content_client
        )
        self._data_extractor = DataExtractor(
            logger=self.logger
        )

    @auto_log()
    @traced_method()
    async def get_preview_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self.state_manager.get_state(dialog_manager)
        employee = await self.loom_employee_client.get_employee_by_account_id(
            state.account_id
        )

        text = dialog_manager.dialog_data.get("publication_text", "")

        preview_image_media, has_multiple_images, current_image_index, total_images = \
            self.image_manager.get_preview_image_media(dialog_manager)

        has_image = preview_image_media is not None

        # Загружаем и устанавливаем соцсети по умолчанию если нужно
        await self.social_network_manager.load_and_setup_default_networks(
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        requires_moderation = employee.required_moderation
        can_publish_directly = not requires_moderation

        data = {
            "category_name": dialog_manager.dialog_data.get("category_name", ""),
            "publication_text": text,
            "has_scheduled_time": False,
            "publish_time": "",
            "has_image": has_image,
            "preview_image_media": preview_image_media,
            "has_multiple_images": has_multiple_images,
            "current_image_index": current_image_index + 1,
            "total_images": total_images,
            "requires_moderation": requires_moderation,
            "can_publish_directly": can_publish_directly,
            "is_custom_image": dialog_manager.dialog_data.get("is_custom_image", False),
        }
        return data

    @auto_log()
    @traced_method()
    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self.state_manager.get_state(dialog_manager)

        data = await self.social_network_manager.get_social_network_data(
            dialog_manager=dialog_manager,
            organization_id=state.organization_id
        )

        return data

    @auto_log()
    @traced_method()
    async def get_input_text_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self._data_extractor.get_input_text_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_categories_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self.state_manager.get_state(dialog_manager)

        categories = await self.loom_content_client.get_categories_by_organization(
            state.organization_id
        )

        categories_data = []
        for category in categories:
            categories_data.append({
                "id": category.id,
                "name": category.name,
                "image_style": category.prompt_for_image_style,
            })

        data = {
            "categories": categories_data,
            "has_categories": len(categories_data) > 0,
        }

        return data

    @auto_log()
    @traced_method()
    async def get_edit_text_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self._data_extractor.get_edit_text_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        preview_image_media = self.image_manager.get_image_menu_media(dialog_manager)
        has_image = preview_image_media is not None

        flags_data = self._data_extractor.get_image_menu_flags(dialog_manager)

        return {
            "has_image": has_image,
            "preview_image_media": preview_image_media,
            **flags_data
        }

    @auto_log()
    @traced_method()
    async def get_upload_image_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self._data_extractor.get_upload_imagedialog_data_helper(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_text_too_long_alert_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self._data_extractor.get_text_too_long_alert_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_publication_success_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self._data_extractor.get_publication_success_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_combine_images_choice_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self._data_extractor.get_combine_images_choice_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_combine_images_upload_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        combine_current_image_media, combine_current_index, combine_images_count = \
            self.image_manager.get_combine_images_media(dialog_manager)

        flags_data = self._data_extractor.get_combine_images_upload_flags(dialog_manager)

        return {
            "combine_current_index": combine_current_index + 1,
            "combine_current_image_media": combine_current_image_media,
            **flags_data
        }

    @auto_log()
    @traced_method()
    async def get_combine_images_prompt_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        combine_current_image_media, combine_current_index, combine_images_count = \
            self.image_manager.get_combine_images_media(dialog_manager)

        flags_data = self._data_extractor.get_combine_images_prompt_flags(dialog_manager)

        return {
            "combine_current_index": combine_current_index + 1,
            "combine_current_image_media": combine_current_image_media,
            **flags_data
        }

    @auto_log()
    @traced_method()
    async def get_new_image_confirm_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        new_image_media, old_image_media, showing_old_image = \
            self.image_manager.get_new_image_confirm_media(dialog_manager)

        display_image_media = old_image_media if showing_old_image else new_image_media

        flags_data = self._data_extractor.get_new_image_confirm_flags(dialog_manager)

        return {
            "new_image_media": display_image_media,
            "has_old_image": old_image_media is not None,
            "showing_old_image": showing_old_image,
            "showing_new_image": not showing_old_image,
            **flags_data
        }

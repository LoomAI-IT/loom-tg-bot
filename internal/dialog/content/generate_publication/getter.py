from aiogram import Bot
from aiogram_dialog import DialogManager

from internal import interface
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method

from internal.dialog.helpers import StateManager
from aiogram.types import ContentType
from aiogram_dialog.api.entities import MediaAttachment, MediaId

from internal.dialog.content.generate_publication.helpers import ImageManager, DialogDataHelper, SocialNetworkManager


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
        self.dialog_data_helper = DialogDataHelper(
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

        text = self.dialog_data_helper.get_publication_text(dialog_manager)

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
            "category_name": self.dialog_data_helper.get_category_name(dialog_manager),
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
    async def get_generate_text_prompt_input_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self.dialog_data_helper.get_generate_text_prompt_input_data(dialog_manager)

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
    async def get_edit_publication_text_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self.dialog_data_helper.get_edit_publication_text_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_image_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        preview_image_media = self.image_manager.get_image_menu_media(dialog_manager)
        has_image = preview_image_media is not None

        flags_data = self.dialog_data_helper.get_image_menu_flags(dialog_manager)

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
        return self.dialog_data_helper.get_upload_imagedialog_data_helper(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_text_too_long_alert_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self.dialog_data_helper.get_text_too_long_alert_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_publication_success_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self.dialog_data_helper.get_publication_success_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_combine_images_choice_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return self.dialog_data_helper.get_combine_images_choice_data(dialog_manager)

    @auto_log()
    @traced_method()
    async def get_combine_images_upload_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        combine_current_image_media, combine_current_index, combine_images_count = \
            self.image_manager.get_combine_images_media(dialog_manager)

        flags_data = self.dialog_data_helper.get_combine_images_upload_flags(dialog_manager)

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

        flags_data = self.dialog_data_helper.get_combine_images_prompt_flags(dialog_manager)

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

        flags_data = self.dialog_data_helper.get_new_image_confirm_flags(dialog_manager)

        return {
            "new_image_media": display_image_media,
            "has_old_image": old_image_media is not None,
            "showing_old_image": showing_old_image,
            "showing_new_image": not showing_old_image,
            **flags_data
        }

    @auto_log()
    @traced_method()
    async def get_reference_generation_image_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:

        reference_generation_image_file_id = self.dialog_data_helper.get_reference_generation_image_file_id(
            dialog_manager)
        reference_generation_image_media = None

        if reference_generation_image_file_id:
            reference_generation_image_media = MediaAttachment(
                file_id=MediaId(reference_generation_image_file_id),
                type=ContentType.PHOTO
            )

        return {
            "has_reference_generation_image": self.dialog_data_helper.get_has_reference_generation_image(
                dialog_manager),
            "reference_generation_image_media": reference_generation_image_media,
            "is_generating_image": dialog_manager.dialog_data.get("is_generating_image", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            # Error flags
            "has_void_reference_generation_image_prompt": dialog_manager.dialog_data.get(
                "has_void_reference_generation_image_prompt",
                False),
            "has_small_reference_generation_image_prompt": dialog_manager.dialog_data.get(
                "has_small_reference_generation_image_prompt",
                False),
            "has_big_reference_generation_image_prompt": dialog_manager.dialog_data.get(
                "has_big_reference_generation_image_prompt",
                False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
            "has_invalid_reference_generation_image_type": dialog_manager.dialog_data.get(
                "has_invalid_reference_generation_image_type", False),
            "has_big_reference_generation_image_size": dialog_manager.dialog_data.get(
                "has_big_reference_generation_image_size", False),
        }

    @auto_log()
    @traced_method()
    async def get_reference_generation_image_upload_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        # Проверяем есть ли текущее изображение в публикации
        custom_image_file_id = self.dialog_data_helper.get_custom_image_file_id(dialog_manager)
        publication_images_url = self.dialog_data_helper.get_publication_images_url(dialog_manager)
        has_image = bool(custom_image_file_id or publication_images_url)

        return {
            "has_invalid_reference_generation_image_type": dialog_manager.dialog_data.get(
                "has_invalid_reference_generation_image_type", False),
            "has_big_reference_generation_image_size": dialog_manager.dialog_data.get(
                "has_big_reference_generation_image_size", False),
            "has_image": has_image,
        }

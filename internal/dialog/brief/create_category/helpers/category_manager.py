import datetime

from aiogram_dialog import DialogManager

from internal import interface, model


class CategoryManager:
    def __init__(
            self,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.loom_content_client = loom_content_client

    async def test_category_generation(
            self,
            test_category_data: dict,
            user_text_reference: str,
            organization_id: int,
    ) -> str:
        test_publication_text = await self.loom_content_client.test_generate_publication(
            user_text_reference=user_text_reference,
            organization_id=organization_id,
            name=test_category_data.get("name", ""),
            hint=test_category_data.get("hint", ""),
            goal=test_category_data.get("goal", ""),
            tone_of_voice=test_category_data.get("tone_of_voice", []),
            brand_rules=test_category_data.get("brand_rules", []),
            creativity_level=test_category_data.get("creativity_level", 5),
            audience_segment=test_category_data.get("audience_segment", ""),
            len_min=test_category_data.get("len_min", 200),
            len_max=test_category_data.get("len_max", 400),
            n_hashtags_min=test_category_data.get("n_hashtags_min", 1),
            n_hashtags_max=test_category_data.get("n_hashtags_max", 2),
            cta_type=test_category_data.get("cta_type", ""),
            cta_strategy=test_category_data.get("cta_strategy", {}),
            good_samples=test_category_data.get("good_samples", []),
            bad_samples=test_category_data.get("bad_samples", []),
            additional_info=test_category_data.get("additional_info", []),
            prompt_for_image_style=test_category_data.get("prompt_for_image_style", ""),
        )
        return test_publication_text

    async def save_category(
            self,
            dialog_manager: DialogManager,
            organization_id: int,
            category_data: dict
    ):
        category = model.Category(
            **category_data,
            organization_id=organization_id,
            good_samples=[],
            bad_samples=[],
            created_at="-"
        )
        dialog_manager.dialog_data["category_data"] = category.to_dict()

    async def create_category(
            self,
            organization_id: int,
            category_data: dict
    ) -> int:
        category_id = await self.loom_content_client.create_category(
            organization_id=organization_id,
            name=category_data.get("name"),
            hint=category_data.get("hint"),
            goal=category_data.get("goal"),
            tone_of_voice=category_data.get("tone_of_voice"),
            brand_rules=category_data.get("brand_rules"),
            creativity_level=category_data.get("creativity_level"),
            audience_segment=category_data.get("audience_segment"),
            len_min=category_data.get("len_min"),
            len_max=category_data.get("len_max"),
            n_hashtags_min=category_data.get("n_hashtags_min"),
            n_hashtags_max=category_data.get("n_hashtags_max"),
            cta_type=category_data.get("cta_type"),
            cta_strategy=category_data.get("cta_strategy"),
            good_samples=category_data.get("good_samples"),
            bad_samples=category_data.get("bad_samples"),
            additional_info=category_data.get("additional_info"),
            prompt_for_image_style=category_data.get("prompt_for_image_style"),
        )
        return category_id

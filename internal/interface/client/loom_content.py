import io
from typing import Protocol
from abc import abstractmethod
from datetime import datetime

from internal import model


class ILoomContentClient(Protocol):
    @abstractmethod
    async def get_social_networks_by_organization(self, organization_id: int) -> dict: pass

    @abstractmethod
    async def create_telegram(self, organization_id: int, telegram_channel_username: str, autoselect: bool): pass

    @abstractmethod
    async def update_telegram(
            self,
            organization_id: int,
            telegram_channel_username: str = None,
            autoselect: bool = None
    ): pass

    @abstractmethod
    async def check_telegram_channel_permission(self, telegram_channel_username: str) -> bool: pass

    @abstractmethod
    async def delete_telegram(self, organization_id: int): pass

    # ПУБЛИКАЦИИ
    @abstractmethod
    async def generate_publication_text(
            self,
            category_id: int,
            text_reference: str
    ) -> dict: pass

    @abstractmethod
    async def regenerate_publication_text(
            self,
            category_id: int,
            publication_text: str,
            prompt: str = None
    ) -> dict: pass

    @abstractmethod
    async def generate_publication_image(
            self,
            category_id: int,
            publication_text: str,
            text_reference: str,
            prompt: str = None,
            image_content: bytes = None,
            image_filename: str = None,
    ) -> list[str]: pass

    @abstractmethod
    async def create_publication(
            self,
            organization_id: int,
            category_id: int,
            creator_id: int,
            text_reference: str,
            text: str,
            moderation_status: str,
            image_url: str = None,
            image_content: bytes = None,
            image_filename: str = None,
    ) -> dict: pass

    @abstractmethod
    async def change_publication(
            self,
            publication_id: int,
            vk_source: bool = None,
            tg_source: bool = None,
            text: str = None,
            time_for_publication: datetime = None,
            image_url: str = None,
            image_content: bytes = None,
            image_filename: str = None,
    ) -> None: pass

    @abstractmethod
    async def delete_publication(
            self,
            publication_id: int,
    ) -> None: pass

    @abstractmethod
    async def delete_publication_image(self, publication_id: int) -> None: pass

    @abstractmethod
    async def send_publication_to_moderation(self, publication_id: int) -> None: pass

    @abstractmethod
    async def moderate_publication(
            self,
            publication_id: int,
            moderator_id: int,
            moderation_status: str,
            moderation_comment: str = ""
    ) -> dict: pass

    @abstractmethod
    async def get_publication_by_id(self, publication_id: int) -> model.Publication: pass

    @abstractmethod
    async def get_publications_by_organization(self, organization_id: int) -> list[model.Publication]: pass

    # РУБРИКИ
    @abstractmethod
    async def create_category(
            self,
            organization_id: int,
            name: str,
            hint: str,

            goal: str,
            tone_of_voice: list[str],
            brand_rules: list[str],

            creativity_level: int,
            audience_segment: str,

            len_min: int,
            len_max: int,

            n_hashtags_min: int,
            n_hashtags_max: int,

            cta_type: str,
            cta_strategy: dict,

            good_samples: list[dict],
            bad_samples: list[dict],
            additional_info: list[dict],

            prompt_for_image_style: str,
    ) -> int: pass

    @abstractmethod
    async def test_generate_publication(
            self,
            user_text_reference: str,
            organization_id: int,
            name: str,
            hint: str,

            goal: str,
            tone_of_voice: list[str],
            brand_rules: list[str],

            creativity_level: int,
            audience_segment: str,

            len_min: int,
            len_max: int,

            n_hashtags_min: int,
            n_hashtags_max: int,

            cta_type: str,
            cta_strategy: dict,

            good_samples: list[dict],
            bad_samples: list[dict],
            additional_info: list[dict],

            prompt_for_image_style: str
    ) -> str: pass


    @abstractmethod
    async def update_category(
            self,
            category_id: int,
            name: str = None,
            hint: str = None,
            goal: str = None,
            tone_of_voice: list[str] = None,
            brand_rules: list[str] = None,
            creativity_level: int = None,
            audience_segment: str = None,
            len_min: int = None,
            len_max: int = None,
            n_hashtags_min: int = None,
            n_hashtags_max: int = None,
            cta_type: str = None,
            cta_strategy: dict = None,
            good_samples: list[dict] = None,
            bad_samples: list[dict] = None,
            additional_info: list[dict] = None,
            prompt_for_image_style: str = None
    ) -> None: pass

    @abstractmethod
    async def get_category_by_id(self, category_id: int) -> model.Category: pass

    @abstractmethod
    async def get_categories_by_organization(self, organization_id: int) -> list[model.Category]: pass


    # НАРЕЗКА
    @abstractmethod
    async def generate_video_cut(
            self,
            organization_id: int,
            creator_id: int,
            youtube_video_reference: str,
    ) -> None: pass

    @abstractmethod
    async def change_video_cut(
            self,
            video_cut_id: int,
            name: str = None,
            description: str = None,
            tags: list[str] = None,
            inst_source: bool = None,
            youtube_source: bool = None
    ) -> None: pass

    @abstractmethod
    async def delete_video_cut(self, video_cut_id: int) -> None: pass

    @abstractmethod
    async def send_video_cut_to_moderation(self, video_cut_id: int) -> None: pass

    @abstractmethod
    async def get_video_cut_by_id(self, video_cut_id: int) -> model.VideoCut: pass

    @abstractmethod
    async def get_video_cuts_by_organization(self, organization_id: int) -> list[model.VideoCut]: pass

    @abstractmethod
    async def moderate_video_cut(
            self,
            video_cut_id: int,
            moderator_id: int,
            moderation_status: str,
            moderation_comment: str = ""
    ) -> None: pass

    @abstractmethod
    async def transcribe_audio(
            self,
            organization_id: int,
            audio_content: bytes = None,
            audio_filename: str = None,
    ) -> str: pass

    @abstractmethod
    async def combine_images(
            self,
            organization_id: int,
            images_content: list[bytes],
            images_filenames: list[str],
            prompt: str,
    ) -> list[str]: pass

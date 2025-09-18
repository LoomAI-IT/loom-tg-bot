import io
from typing import Protocol
from abc import abstractmethod
from datetime import datetime
from fastapi import UploadFile

from internal import model

class IKonturPublicationClient(Protocol):
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
            prompt: str = None
    ) -> str: pass

    @abstractmethod
    async def create_publication(
            self,
            organization_id: int,
            category_id: int,
            creator_id: int,
            text_reference: str,
            name: str,
            text: str,
            tags: list[str],
            moderation_status: str,
            image_url: str = None,
            image_content: bytes = None,
            image_filename: str = None,
    ) -> int: pass

    @abstractmethod
    async def change_publication(
            self,
            publication_id: int,
            vk_source_id: int = None,
            tg_source_id: int = None,
            name: str = None,
            text: str = None,
            tags: list[str] = None,
            time_for_publication: datetime = None,
            image_url: str = None,
            image_content: bytes = None,
            image_filename: str = None,
    ) -> None: pass

    @abstractmethod
    async def publish_publication(self, publication_id: int) -> None: pass

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
    ) -> None: pass

    @abstractmethod
    async def get_publication_by_id(self, publication_id: int) -> model.Publication: pass

    @abstractmethod
    async def get_publications_by_organization(self, organization_id: int) -> list[model.Publication]: pass

    @abstractmethod
    async def download_publication_image(self, publication_id: int) -> tuple[io.BytesIO, str]: pass

    # РУБРИКИ
    @abstractmethod
    async def create_category(
            self,
            organization_id: int,
            prompt_for_image_style: str,
            prompt_for_text_style: str
    ) -> int: pass

    @abstractmethod
    async def get_category_by_id(self, category_id: int) -> model.Category: pass

    @abstractmethod
    async def get_categories_by_organization(self, organization_id: int) -> list[model.Category]: pass

    @abstractmethod
    async def update_category(
            self,
            category_id: int,
            prompt_for_image_style: str = None,
            prompt_for_text_style: str = None
    ) -> None: pass

    @abstractmethod
    async def delete_category(self, category_id: int) -> None: pass

    # АВТОПОСТИНГ
    @abstractmethod
    async def create_autoposting(
            self,
            organization_id: int,
            filter_prompt: str,
            rewrite_prompt: str,
            tg_channels: list[str] = None
    ) -> int: pass

    @abstractmethod
    async def get_autoposting_by_organization(self, organization_id: int) -> list[model.Autoposting]: pass

    @abstractmethod
    async def update_autoposting(
            self,
            autoposting_id: int,
            filter_prompt: str = None,
            rewrite_prompt: str = None,
            tg_channels: list[str] = None
    ) -> None: pass

    @abstractmethod
    async def delete_autoposting(self, autoposting_id: int) -> None: pass

    # НАРЕЗКА
    @abstractmethod
    async def generate_video_cut(
            self,
            organization_id: int,
            creator_id: int,
            youtube_video_reference: str,
            time_for_publication: datetime = None
    ) -> None: pass

    @abstractmethod
    async def change_video_cut(
            self,
            video_cut_id: int,
            name: str = None,
            text: str = None,
            tags: list[str] = None,
            time_for_publication: datetime = None
    ) -> None: pass

    @abstractmethod
    async def send_video_cut_to_moderation(self, video_cut_id: int) -> None: pass

    @abstractmethod
    async def publish_video_cut(self, video_cut_id: int) -> None: pass

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
    async def download_video_cut(self, video_cut_id: int) -> tuple[io.BytesIO, str]: pass
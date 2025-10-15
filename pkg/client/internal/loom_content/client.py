from contextvars import ContextVar
from datetime import datetime

from opentelemetry.trace import SpanKind

from internal import model
from internal import interface
from pkg.client.client import AsyncHTTPClient
from pkg.trace_wrapper import traced_method


class LoomContentClient(interface.ILoomContentClient):
    def __init__(
            self,
            tel: interface.ITelemetry,
            host: str,
            port: int,
            log_context: ContextVar[dict],
    ):
        self.client = AsyncHTTPClient(
            host,
            port,
            prefix="/api/content",
            use_tracing=True,
            log_context=log_context,
            timeout=900
        )
        self.tracer = tel.tracer()

    @traced_method(SpanKind.CLIENT)
    async def get_social_networks_by_organization(self, organization_id: int) -> dict:
        response = await self.client.get(f"/social-network/organization/{organization_id}")
        json_response = response.json()

        return json_response["data"]

    @traced_method(SpanKind.CLIENT)
    async def create_telegram(self, organization_id: int, telegram_channel_username: str, autoselect: bool):
        body = {
            "organization_id": organization_id,
            "tg_channel_username": telegram_channel_username,
            "autoselect": autoselect,
        }
        await self.client.post(f"/social-network/telegram", json=body)

    @traced_method(SpanKind.CLIENT)
    async def check_telegram_channel_permission(self, telegram_channel_username: str) -> bool:
        response = await self.client.get(f"/social-network/telegram/check-permission/{telegram_channel_username}")
        json_response = response.json()

        return json_response["has_permission"]

    @traced_method(SpanKind.CLIENT)
    async def update_telegram(
            self,
            organization_id: int,
            telegram_channel_username: str = None,
            autoselect: bool = None
    ):
        body = {
            "organization_id": organization_id,
            "tg_channel_username": telegram_channel_username,
            "autoselect": autoselect,
        }
        await self.client.put(f"/social-network/telegram", json=body)

    @traced_method(SpanKind.CLIENT)
    async def delete_telegram(self, organization_id: int):
        await self.client.delete(f"/social-network/telegram/{organization_id}")

    # ПУБЛИКАЦИИ
    async def generate_publication_text(
            self,
            category_id: int,
            text_reference: str
    ) -> dict:
        body = {
            "category_id": category_id,
            "text_reference": text_reference,
        }
        response = await self.client.post("/publication/text/generate", json=body)
        json_response = response.json()

        return json_response

    @traced_method(SpanKind.CLIENT)
    async def regenerate_publication_text(
            self,
            category_id: int,
            publication_text: str,
            prompt: str = None
    ) -> dict:
        body = {
            "category_id": category_id,
            "publication_text": publication_text,
            "prompt": prompt,
        }
        response = await self.client.post("/publication/text/regenerate", json=body)
        json_response = response.json()

        return json_response

    @traced_method(SpanKind.CLIENT)
    async def generate_publication_image(
            self,
            category_id: int,
            publication_text: str,
            text_reference: str,
            prompt: str = None,
            image_content: bytes = None,
            image_filename: str = None,
    ) -> list[str]:
        data = {
            "category_id": category_id,
            "publication_text": publication_text,
            "text_reference": text_reference,
            "prompt": prompt,
        }
        if prompt is not None:
            data["prompt"] = prompt

        files = {}

        # Если есть содержимое файла
        if image_content and image_filename:
            files["image_file"] = (
                image_filename,
                image_content,
                "image/png"  # можно определять по расширению
            )

        # Отправляем запрос
        if files:
            response = await self.client.post("/publication/image/generate", data=data, files=files)
        else:
            response = await self.client.post("/publication/image/generate", data=data)
        json_response = response.json()
        return json_response

    @traced_method(SpanKind.CLIENT)
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
    ) -> dict:
        data = {
            "organization_id": str(organization_id),
            "category_id": str(category_id),
            "creator_id": str(creator_id),
            "text_reference": text_reference,
            "text": text,
            "moderation_status": moderation_status,
        }

        if image_url:
            data["image_url"] = image_url

        files = {}

        # Если есть содержимое файла
        if image_content and image_filename:
            files["image_file"] = (
                image_filename,
                image_content,
                "image/png"
            )

        if files:
            response = await self.client.post("/publication/create", data=data, files=files)
        else:
            response = await self.client.post("/publication/create", data=data)

        json_response = response.json()
        return json_response

    @traced_method(SpanKind.CLIENT)
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
    ) -> None:
        data = {}

        if vk_source is not None:
            data["vk_source"] = vk_source
        if tg_source is not None:
            data["tg_source"] = tg_source
        if text is not None:
            data["text"] = text
        if time_for_publication is not None:
            data["time_for_publication"] = time_for_publication.isoformat() if hasattr(time_for_publication,
                                                                                       'isoformat') else str(
                time_for_publication)

        if image_url is not None:
            data["image_url"] = image_url

        files = {}

        if image_content and image_filename:
            files["image_file"] = (
                image_filename,
                image_content,
                "image/png"
            )
        if files:
            response = await self.client.put(f"/publication/{publication_id}", data=data, files=files)
        elif data:  # Отправляем только если есть данные
            response = await self.client.put(f"/publication/{publication_id}", data=data)
        else:
            return None

        json_response = response.json()
        return json_response

    @traced_method(SpanKind.CLIENT)
    async def delete_publication(
            self,
            publication_id: int,
    ) -> None:
        await self.client.delete(f"/publication/{publication_id}")

    @traced_method(SpanKind.CLIENT)
    async def delete_publication_image(
            self,
            publication_id: int,
    ) -> None:
        await self.client.delete(f"/publication/{publication_id}/image")

    @traced_method(SpanKind.CLIENT)
    async def send_publication_to_moderation(
            self,
            publication_id: int,
    ) -> None:
        await self.client.post(f"/publication/{publication_id}/moderation/send")

    @traced_method(SpanKind.CLIENT)
    async def moderate_publication(
            self,
            publication_id: int,
            moderator_id: int,
            moderation_status: str,
            moderation_comment: str = ""
    ) -> dict:
        body = {
            "publication_id": publication_id,
            "moderator_id": moderator_id,
            "moderation_status": moderation_status.value if hasattr(moderation_status, 'value') else str(
                moderation_status),
            "moderation_comment": moderation_comment
        }
        response = await self.client.post("/publication/moderate", json=body)
        json_response = response.json()

        return json_response

    @traced_method(SpanKind.CLIENT)
    async def get_publication_by_id(self, publication_id: int) -> model.Publication:
        response = await self.client.get(f"/publication/{publication_id}")
        json_response = response.json()

        return model.Publication(**json_response)

    @traced_method(SpanKind.CLIENT)
    async def get_publications_by_organization(self, organization_id: int) -> list[model.Publication]:
        response = await self.client.get(f"/publication/organization/{organization_id}/publications")
        json_response = response.json()

        return [model.Publication(**pub) for pub in json_response]

    @traced_method(SpanKind.CLIENT)
    async def get_category_by_id(self, category_id: int) -> model.Category:
        response = await self.client.get(f"/publication/category/{category_id}")
        json_response = response.json()

        return model.Category(**json_response)

    @traced_method(SpanKind.CLIENT)
    async def get_categories_by_organization(self, organization_id: int) -> list[model.Category]:
        response = await self.client.get(f"/publication/organization/{organization_id}/categories")
        json_response = response.json()

        return [model.Category(**cat) for cat in json_response]

    # НАРЕЗКА
    async def generate_video_cut(
            self,
            organization_id: int,
            creator_id: int,
            youtube_video_reference: str,
    ) -> None:
        body = {
            "organization_id": organization_id,
            "creator_id": creator_id,
            "youtube_video_reference": youtube_video_reference
        }

        await self.client.post("/video-cut/vizard/generate", json=body)

    @traced_method(SpanKind.CLIENT)
    async def change_video_cut(
            self,
            video_cut_id: int,
            name: str = None,
            description: str = None,
            tags: list[str] = None,
            inst_source: bool = None,
            youtube_source: bool = None,
    ) -> None:
        body: dict = {"video_cut_id": video_cut_id}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if tags is not None:
            body["tags"] = tags
        if inst_source is not None:
            body["inst_source"] = inst_source
        if youtube_source is not None:
            body["youtube_source"] = youtube_source

        await self.client.put(f"/video-cut", json=body)

    @traced_method(SpanKind.CLIENT)
    async def delete_video_cut(self, video_cut_id: int) -> None:
        await self.client.delete(f"/video-cut/{video_cut_id}")

    @traced_method(SpanKind.CLIENT)
    async def send_video_cut_to_moderation(
            self,
            video_cut_id: int,
    ) -> None:
        await self.client.post(f"/video-cut/{video_cut_id}/moderation/send")

    @traced_method(SpanKind.CLIENT)
    async def get_video_cut_by_id(self, video_cut_id: int) -> model.VideoCut:
        response = await self.client.get(f"/video-cut/{video_cut_id}")
        json_response = response.json()

        return model.VideoCut(**json_response)

    @traced_method(SpanKind.CLIENT)
    async def get_video_cuts_by_organization(self, organization_id: int) -> list[model.VideoCut]:
        response = await self.client.get(f"/organization/{organization_id}/video-cuts")
        json_response = response.json()

        return [model.VideoCut(**cut) for cut in json_response]

    @traced_method(SpanKind.CLIENT)
    async def moderate_video_cut(
            self,
            video_cut_id: int,
            moderator_id: int,
            moderation_status: str,
            moderation_comment: str = ""
    ) -> None:
        body = {
            "video_cut_id": video_cut_id,
            "moderator_id": moderator_id,
            "moderation_status": moderation_status.value if hasattr(moderation_status, 'value') else str(
                moderation_status),
            "moderation_comment": moderation_comment
        }
        await self.client.post(f"/video-cut/moderate", json=body)

    @traced_method(SpanKind.CLIENT)
    async def transcribe_audio(
            self,
            organization_id: int,
            audio_content: bytes = None,
            audio_filename: str = None,
    ) -> str:
        data = {"organization_id": organization_id}
        files = {
            "audio_file": (
                audio_filename,
                audio_content,
                "audio/mp4"
            )
        }
        response = await self.client.get("/publication/audio/transcribe", data=data, files=files)

        json_response = response.json()

        return json_response["text"]

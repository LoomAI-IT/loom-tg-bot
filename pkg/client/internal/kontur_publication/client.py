import io
from datetime import datetime
from opentelemetry.trace import Status, StatusCode, SpanKind
from fastapi import UploadFile

from internal import model
from internal import interface
from pkg.client.client import AsyncHTTPClient


class KonturPublicationClient(interface.IKonturPublicationClient):
    def __init__(
            self,
            tel: interface.ITelemetry,
            host: str,
            port: int
    ):
        self.client = AsyncHTTPClient(
            host,
            port,
            prefix="/api/publication",
            use_tracing=True,
            logger=None,
        )
        self.tracer = tel.tracer()

    # ПУБЛИКАЦИИ
    async def generate_publication_text(
            self,
            category_id: int,
            text_reference: str
    ) -> dict:
        with self.tracer.start_as_current_span(
                "PublicationClient.generate_publication_text",
                kind=SpanKind.CLIENT
        ) as span:
            try:
                body = {
                    "category_id": category_id,
                    "text_reference": text_reference,
                }
                response = await self.client.post("/text/generate", json=body)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def regenerate_publication_text(
            self,
            category_id: int,
            publication_text: str,
            prompt: str = None
    ) -> dict:
        with self.tracer.start_as_current_span(
                "PublicationClient.regenerate_publication_text",
                kind=SpanKind.CLIENT
        ) as span:
            try:
                body = {
                    "category_id": category_id,
                    "publication_text": publication_text,
                    "prompt": prompt,
                }
                response = await self.client.post("/text/regenerate", json=body)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def generate_publication_image(
            self,
            category_id: int,
            publication_text: str,
            text_reference: str,
            prompt: str = None
    ) -> str:
        with self.tracer.start_as_current_span(
                "PublicationClient.generate_publication_image",
                kind=SpanKind.CLIENT
        ) as span:
            try:
                body = {
                    "category_id": category_id,
                    "publication_text": publication_text,
                    "text_reference": text_reference,
                    "prompt": prompt,
                }
                response = await self.client.post("/image/generate", json=body)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

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
            image_url: str = None
    ) -> int:
        with self.tracer.start_as_current_span(
                "PublicationClient.create_publication",
                kind=SpanKind.CLIENT
        ) as span:
            try:
                body = {
                    "organization_id": organization_id,
                    "category_id": category_id,
                    "creator_id": creator_id,
                    "text_reference": text_reference,
                    "name": name,
                    "text": text,
                    "tags": tags,
                    "moderation_status": moderation_status,
                    "image_url": image_url,
                }
                response = await self.client.post("/create", json=body)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def change_publication(
            self,
            publication_id: int,
            vk_source_id: int = None,
            tg_source_id: int = None,
            name: str = None,
            text: str = None,
            tags: list[str] = None,
            time_for_publication: datetime = None,
            image: UploadFile = None,
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.change_publication",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                # For multipart form data if image is provided
                if image:
                    files = {"image": (image.filename, await image.read(), image.content_type)}
                    data = {}
                    if vk_source_id is not None:
                        data["vk_source_id"] = vk_source_id
                    if tg_source_id is not None:
                        data["tg_source_id"] = tg_source_id
                    if name is not None:
                        data["name"] = name
                    if text is not None:
                        data["text"] = text
                    if tags is not None:
                        data["tags"] = ",".join(tags)
                    if time_for_publication is not None:
                        data["time_for_publication"] = time_for_publication.isoformat()

                    await self.client.put(f"/{publication_id}", data=data, files=files)
                else:
                    # JSON request
                    body = {}
                    if vk_source_id is not None:
                        body["vk_source_id"] = vk_source_id
                    if tg_source_id is not None:
                        body["tg_source_id"] = tg_source_id
                    if name is not None:
                        body["name"] = name
                    if text is not None:
                        body["text"] = text
                    if tags is not None:
                        body["tags"] = tags
                    if time_for_publication is not None:
                        body["time_for_publication"] = time_for_publication.isoformat()

                    await self.client.put(f"/{publication_id}", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def publish_publication(
            self,
            publication_id: int,
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.publish_publication",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                await self.client.post(f"/{publication_id}/publish")

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def delete_publication_image(
            self,
            publication_id: int,
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.delete_publication_image",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                await self.client.delete(f"/{publication_id}/image")

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def send_publication_to_moderation(
            self,
            publication_id: int,
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.send_publication_to_moderation",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                await self.client.post(f"/{publication_id}/moderation/send")

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def moderate_publication(
            self,
            publication_id: int,
            moderator_id: int,
            moderation_status: str,
            moderation_comment: str = ""
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.moderate_publication",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id,
                    "moderator_id": moderator_id,
                    "moderation_status": moderation_status.value if hasattr(moderation_status, 'value') else str(
                        moderation_status)
                }
        ) as span:
            try:
                body = {
                    "publication_id": publication_id,
                    "moderator_id": moderator_id,
                    "moderation_status": moderation_status.value if hasattr(moderation_status, 'value') else str(
                        moderation_status),
                    "moderation_comment": moderation_comment
                }
                await self.client.post("/moderate", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_publication_by_id(self, publication_id: int) -> model.Publication:
        with self.tracer.start_as_current_span(
                "PublicationClient.get_publication_by_id",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/{publication_id}")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return model.Publication(**json_response)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_publications_by_organization(self, organization_id: int) -> list[model.Publication]:
        with self.tracer.start_as_current_span(
                "PublicationClient.get_publications_by_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/organization/{organization_id}/publications")
                json_response = response.json()
                print(json_response, flush=True)
                span.set_status(Status(StatusCode.OK))
                return [model.Publication(**pub) for pub in json_response]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def download_publication_image(
            self,
            publication_id: int
    ) -> tuple[io.BytesIO, str]:
        with self.tracer.start_as_current_span(
                "PublicationClient.download_publication_image",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/{publication_id}/image/download")

                # Extract filename from Content-Disposition header or use default
                filename = "image.jpg"
                if "Content-Disposition" in response.headers:
                    content_disposition = response.headers["Content-Disposition"]
                    if "filename=" in content_disposition:
                        filename = content_disposition.split("filename=")[-1].strip('"')

                image_data = io.BytesIO(response.content)

                span.set_status(Status(StatusCode.OK))
                return image_data, filename
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    # РУБРИКИ
    async def create_category(
            self,
            organization_id: int,
            prompt_for_image_style: str,
            prompt_for_text_style: str
    ) -> int:
        with self.tracer.start_as_current_span(
                "PublicationClient.create_category",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                body = {
                    "organization_id": organization_id,
                    "prompt_for_image_style": prompt_for_image_style,
                    "prompt_for_text_style": prompt_for_text_style
                }
                response = await self.client.post("/category", json=body)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response["category_id"]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_category_by_id(self, category_id: int) -> model.Category:
        with self.tracer.start_as_current_span(
                "PublicationClient.get_category_by_id",
                kind=SpanKind.CLIENT,
                attributes={
                    "category_id": category_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/category/{category_id}")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return model.Category(**json_response)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_categories_by_organization(self, organization_id: int) -> list[model.Category]:
        with self.tracer.start_as_current_span(
                "PublicationClient.get_categories_by_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/organization/{organization_id}/categories")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return [model.Category(**cat) for cat in json_response]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def update_category(
            self,
            category_id: int,
            prompt_for_image_style: str = None,
            prompt_for_text_style: str = None
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.update_category",
                kind=SpanKind.CLIENT,
                attributes={
                    "category_id": category_id
                }
        ) as span:
            try:
                body = {}
                if prompt_for_image_style is not None:
                    body["prompt_for_image_style"] = prompt_for_image_style
                if prompt_for_text_style is not None:
                    body["prompt_for_text_style"] = prompt_for_text_style

                await self.client.put(f"/category/{category_id}", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def delete_category(self, category_id: int) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.delete_category",
                kind=SpanKind.CLIENT,
                attributes={
                    "category_id": category_id
                }
        ) as span:
            try:
                await self.client.delete(f"/category/{category_id}")

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    # АВТОПОСТИНГ
    async def create_autoposting(
            self,
            organization_id: int,
            filter_prompt: str,
            rewrite_prompt: str,
            tg_channels: list[str] = None
    ) -> int:
        with self.tracer.start_as_current_span(
                "PublicationClient.create_autoposting",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                body: dict = {
                    "organization_id": organization_id,
                    "filter_prompt": filter_prompt,
                    "rewrite_prompt": rewrite_prompt
                }
                if tg_channels is not None:
                    body["tg_channels"] = tg_channels

                response = await self.client.post("/autoposting", json=body)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response["autoposting_id"]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_autoposting_by_organization(self, organization_id: int) -> list[model.Autoposting]:
        with self.tracer.start_as_current_span(
                "PublicationClient.get_autoposting_by_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/organization/{organization_id}/autopostings")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return [model.Autoposting(**autoposting) for autoposting in json_response]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def update_autoposting(
            self,
            autoposting_id: int,
            filter_prompt: str = None,
            rewrite_prompt: str = None,
            tg_channels: list[str] = None
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.update_autoposting",
                kind=SpanKind.CLIENT,
                attributes={
                    "autoposting_id": autoposting_id
                }
        ) as span:
            try:
                body = {}
                if filter_prompt is not None:
                    body["filter_prompt"] = filter_prompt
                if rewrite_prompt is not None:
                    body["rewrite_prompt"] = rewrite_prompt
                if tg_channels is not None:
                    body["tg_channels"] = tg_channels

                await self.client.put(f"/autoposting/{autoposting_id}", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def delete_autoposting(self, autoposting_id: int) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.delete_autoposting",
                kind=SpanKind.CLIENT,
                attributes={
                    "autoposting_id": autoposting_id
                }
        ) as span:
            try:
                await self.client.delete(f"/autoposting/{autoposting_id}")

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    # НАРЕЗКА
    async def generate_video_cut(
            self,
            organization_id: int,
            creator_id: int,
            youtube_video_reference: str,
            time_for_publication: datetime = None
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.generate_video_cut",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id,
                    "creator_id": creator_id
                }
        ) as span:
            try:
                body = {
                    "organization_id": organization_id,
                    "creator_id": creator_id,
                    "youtube_video_reference": youtube_video_reference
                }
                if time_for_publication:
                    body["time_for_publication"] = time_for_publication.isoformat()

                await self.client.post("/video-cut/generate", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def change_video_cut(
            self,
            video_cut_id: int,
            name: str = None,
            text: str = None,
            tags: list[str] = None,
            time_for_publication: datetime = None
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.change_video_cut",
                kind=SpanKind.CLIENT,
                attributes={
                    "video_cut_id": video_cut_id
                }
        ) as span:
            try:
                body = {}
                if name is not None:
                    body["name"] = name
                if text is not None:
                    body["text"] = text
                if tags is not None:
                    body["tags"] = tags
                if time_for_publication is not None:
                    body["time_for_publication"] = time_for_publication.isoformat()

                await self.client.put(f"/video-cut/{video_cut_id}", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def send_video_cut_to_moderation(
            self,
            video_cut_id: int,
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.send_video_cut_to_moderation",
                kind=SpanKind.CLIENT,
                attributes={
                    "video_cut_id": video_cut_id
                }
        ) as span:
            try:
                await self.client.post(f"/video-cut/{video_cut_id}/moderation/send")

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def publish_video_cut(
            self,
            video_cut_id: int,
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.publish_video_cut",
                kind=SpanKind.CLIENT,
                attributes={
                    "video_cut_id": video_cut_id
                }
        ) as span:
            try:
                await self.client.post(f"/video-cut/{video_cut_id}/publish")

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_video_cut_by_id(self, video_cut_id: int) -> model.VideoCut:
        with self.tracer.start_as_current_span(
                "PublicationClient.get_video_cut_by_id",
                kind=SpanKind.CLIENT,
                attributes={
                    "video_cut_id": video_cut_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/video-cut/{video_cut_id}")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return model.VideoCut(**json_response)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_video_cuts_by_organization(self, organization_id: int) -> list[model.VideoCut]:
        with self.tracer.start_as_current_span(
                "PublicationClient.get_video_cuts_by_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/organization/{organization_id}/video-cuts")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return [model.VideoCut(**cut) for cut in json_response]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def moderate_video_cut(
            self,
            video_cut_id: int,
            moderator_id: int,
            moderation_status: str,
            moderation_comment: str = ""
    ) -> None:
        with self.tracer.start_as_current_span(
                "PublicationClient.moderate_video_cut",
                kind=SpanKind.CLIENT,
                attributes={
                    "video_cut_id": video_cut_id,
                    "moderator_id": moderator_id,
                    "moderation_status": moderation_status.value if hasattr(moderation_status, 'value') else str(
                        moderation_status)
                }
        ) as span:
            try:
                body = {
                    "moderator_id": moderator_id,
                    "moderation_status": moderation_status.value if hasattr(moderation_status, 'value') else str(
                        moderation_status),
                    "moderation_comment": moderation_comment
                }
                await self.client.post(f"/video-cut/{video_cut_id}/moderation/moderate", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def download_video_cut(
            self,
            video_cut_id: int
    ) -> tuple[io.BytesIO, str]:
        with self.tracer.start_as_current_span(
                "PublicationClient.download_video_cut",
                kind=SpanKind.CLIENT,
                attributes={
                    "video_cut_id": video_cut_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/video-cut/{video_cut_id}/download")

                # Extract filename from Content-Disposition header or use default
                filename = "video.mp4"
                if "Content-Disposition" in response.headers:
                    content_disposition = response.headers["Content-Disposition"]
                    if "filename=" in content_disposition:
                        filename = content_disposition.split("filename=")[-1].strip('"')

                video_data = io.BytesIO(response.content)

                span.set_status(Status(StatusCode.OK))
                return video_data, filename
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

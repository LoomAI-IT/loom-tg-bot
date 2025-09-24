import io
import json
from datetime import datetime
from opentelemetry.trace import Status, StatusCode, SpanKind

from internal import model
from internal import interface
from pkg.client.client import AsyncHTTPClient


class KonturContentClient(interface.IKonturContentClient):
    def __init__(
            self,
            tel: interface.ITelemetry,
            host: str,
            port: int
    ):
        self.client = AsyncHTTPClient(
            host,
            port,
            prefix="/api/content",
            use_tracing=True,
        )
        self.tracer = tel.tracer()

    async def get_social_networks_by_organization(self, organization_id: int) -> dict:
        with self.tracer.start_as_current_span(
                "KonturContentClient.get_social_networks_by_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/social-network/organization/{organization_id}")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response["data"]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    # ПУБЛИКАЦИИ
    async def generate_publication_text(
            self,
            category_id: int,
            text_reference: str
    ) -> dict:
        with self.tracer.start_as_current_span(
                "KonturContentClient.generate_publication_text",
                kind=SpanKind.CLIENT
        ) as span:
            try:
                body = {
                    "category_id": category_id,
                    "text_reference": text_reference,
                }
                response = await self.client.post("/publication/text/generate", json=body)
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
                "KonturContentClient.regenerate_publication_text",
                kind=SpanKind.CLIENT
        ) as span:
            try:
                body = {
                    "category_id": category_id,
                    "publication_text": publication_text,
                    "prompt": prompt,
                }
                response = await self.client.post("/publication/text/regenerate", json=body)
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
            prompt: str = None,
            image_content: bytes = None,
            image_filename: str = None,
    ) -> list[str]:
        with self.tracer.start_as_current_span(
                "KonturContentClient.generate_publication_image",
                kind=SpanKind.CLIENT
        ) as span:
            try:
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
            text: str,
            moderation_status: str,
            image_url: str = None,
            image_content: bytes = None,
            image_filename: str = None,
    ) -> dict:
        with self.tracer.start_as_current_span(
                "KonturContentClient.create_publication",
                kind=SpanKind.CLIENT
        ) as span:
            try:

                data = {
                    "organization_id": str(organization_id),
                    "category_id": str(category_id),
                    "creator_id": str(creator_id),
                    "text_reference": text_reference,
                    "name": "",
                    "text": text,
                    "tags": "",
                    "moderation_status": moderation_status,
                }

                # Добавляем image_url если есть
                if image_url:
                    data["image_url"] = image_url

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
                    response = await self.client.post("/publication/create", data=data, files=files)
                else:
                    response = await self.client.post("/publication/create", data=data)

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
            vk_source: bool = None,
            tg_source: bool = None,
            name: str = None,
            text: str = None,
            tags: list[str] = None,
            time_for_publication: datetime = None,
            image_url: str = None,
            image_content: bytes = None,
            image_filename: str = None,
    ) -> None:
        with self.tracer.start_as_current_span(
                "KonturContentClient.change_publication",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                # Формируем data только с непустыми значениями
                data = {}

                if vk_source is not None:
                    data["vk_source"] = vk_source
                if tg_source is not None:
                    data["tg_source"] = tg_source
                if name is not None:
                    data["name"] = name
                if text is not None:
                    data["text"] = text
                if tags is not None:
                    data["tags"] = json.dumps(tags)
                if time_for_publication is not None:
                    data["time_for_publication"] = time_for_publication.isoformat() if hasattr(time_for_publication,
                                                                                               'isoformat') else str(
                        time_for_publication)

                # ВАЖНО: добавляем image_url только если он действительно передан
                if image_url is not None:
                    data["image_url"] = image_url

                files = {}

                # Если есть содержимое файла
                if image_content and image_filename:
                    files["image_file"] = (
                        image_filename,
                        image_content,
                        "image/png"
                    )

                # Отправляем запрос
                if files:
                    response = await self.client.put(f"/publication/{publication_id}", data=data, files=files)
                elif data:  # Отправляем только если есть данные
                    response = await self.client.put(f"/publication/{publication_id}", data=data)
                else:
                    # Если нет данных для обновления, просто возвращаем успех
                    span.set_status(Status(StatusCode.OK))
                    return None

                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def delete_publication(
            self,
            publication_id: int,
    ) -> None:
        with self.tracer.start_as_current_span(
                "KonturContentClient.delete_publication",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                await self.client.delete(f"/publication/{publication_id}")

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
                "KonturContentClient.delete_publication_image",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                await self.client.delete(f"/publication/{publication_id}/image")

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
                "KonturContentClient.send_publication_to_moderation",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                await self.client.post(f"/publication/{publication_id}/moderation/send")

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
                "KonturContentClient.moderate_publication",
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
                await self.client.post("/publication/moderate", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_publication_by_id(self, publication_id: int) -> model.Publication:
        with self.tracer.start_as_current_span(
                "KonturContentClient.get_publication_by_id",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/publication/{publication_id}")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return model.Publication(**json_response)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_publications_by_organization(self, organization_id: int) -> list[model.Publication]:
        with self.tracer.start_as_current_span(
                "KonturContentClient.get_publications_by_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/publication/organization/{organization_id}/publications")
                json_response = response.json()

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
                "KonturContentClient.download_publication_image",
                kind=SpanKind.CLIENT,
                attributes={
                    "publication_id": publication_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/publication/{publication_id}/image/download")

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
                "KonturContentClient.create_category",
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
                response = await self.client.post("/publication/category", json=body)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response["category_id"]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_category_by_id(self, category_id: int) -> model.Category:
        with self.tracer.start_as_current_span(
                "KonturContentClient.get_category_by_id",
                kind=SpanKind.CLIENT,
                attributes={
                    "category_id": category_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/publication/category/{category_id}")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return model.Category(**json_response)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_categories_by_organization(self, organization_id: int) -> list[model.Category]:
        with self.tracer.start_as_current_span(
                "KonturContentClient.get_categories_by_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/publication/organization/{organization_id}/categories")
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
                "KonturContentClient.update_category",
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

                await self.client.put(f"/publication/category/{category_id}", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def delete_category(self, category_id: int) -> None:
        with self.tracer.start_as_current_span(
                "KonturContentClient.delete_category",
                kind=SpanKind.CLIENT,
                attributes={
                    "category_id": category_id
                }
        ) as span:
            try:
                await self.client.delete(f"/publication/category/{category_id}")

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
                "KonturContentClient.create_autoposting",
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

                response = await self.client.post("/publication/autoposting", json=body)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response["autoposting_id"]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_autoposting_by_organization(self, organization_id: int) -> list[model.Autoposting]:
        with self.tracer.start_as_current_span(
                "KonturContentClient.get_autoposting_by_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/publication/organization/{organization_id}/autopostings")
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
                "KonturContentClient.update_autoposting",
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

                await self.client.put(f"/publication/autoposting/{autoposting_id}", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def delete_autoposting(self, autoposting_id: int) -> None:
        with self.tracer.start_as_current_span(
                "KonturContentClient.delete_autoposting",
                kind=SpanKind.CLIENT,
                attributes={
                    "autoposting_id": autoposting_id
                }
        ) as span:
            try:
                await self.client.delete(f"/publication/autoposting/{autoposting_id}")

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
    ) -> None:
        with self.tracer.start_as_current_span(
                "KonturContentClient.generate_video_cut",
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

                await self.client.post("/video-cut/vizard/generate", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def change_video_cut(
            self,
            video_cut_id: int,
            name: str = None,
            description: str = None,
            tags: list[str] = None,
            inst_source: bool = None,
            youtube_source: bool = None,
    ) -> None:
        with self.tracer.start_as_current_span(
                "KonturContentClient.change_video_cut",
                kind=SpanKind.CLIENT,
                attributes={
                    "video_cut_id": video_cut_id
                }
        ) as span:
            try:
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

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def delete_video_cut(self, video_cut_id: int) -> None:
        with self.tracer.start_as_current_span(
                "KonturContentClient.delete_video_cut",
                kind=SpanKind.CLIENT,
                attributes={
                    "video_cut_id": video_cut_id
                }
        ) as span:
            try:
                await self.client.delete(f"/video-cut/{video_cut_id}")

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
                "KonturContentClient.send_video_cut_to_moderation",
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


    async def get_video_cut_by_id(self, video_cut_id: int) -> model.VideoCut:
        with self.tracer.start_as_current_span(
                "KonturContentClient.get_video_cut_by_id",
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
                "KonturContentClient.get_video_cuts_by_organization",
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
                "KonturContentClient.moderate_video_cut",
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
                    "video_cut_id": video_cut_id,
                    "moderator_id": moderator_id,
                    "moderation_status": moderation_status.value if hasattr(moderation_status, 'value') else str(
                        moderation_status),
                    "moderation_comment": moderation_comment
                }
                await self.client.post(f"/video-cut/moderate", json=body)

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
                "KonturContentClient.download_video_cut",
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

    async def transcribe_audio(
            self,
            organization_id: int,
            audio_content: bytes = None,
            audio_filename: str = None,
    ) -> str:
        with self.tracer.start_as_current_span(
                "KonturContentClient.transcribe_audio",
                kind=SpanKind.CLIENT
        ) as span:
            try:

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

                span.set_status(Status(StatusCode.OK))
                return json_response["text"]

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

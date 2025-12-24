from contextvars import ContextVar
from datetime import datetime
import json

import httpx
from opentelemetry.trace import SpanKind

from internal import model, common
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
        try:
            response = await self.client.post("/publication/text/generate", json=body)
        except httpx.HTTPStatusError as err:
            if err.response.status_code == 400:
                try:
                    response_data = err.response.json()
                except (json.JSONDecodeError, ValueError):
                    raise

                if response_data.get("insufficient_balance"):
                    raise common.ErrInsufficientBalance()
            raise
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
        try:
            response = await self.client.post("/publication/text/regenerate", json=body)
        except httpx.HTTPStatusError as err:
            if err.response.status_code == 400:
                try:
                    response_data = err.response.json()
                except (json.JSONDecodeError, ValueError):
                    raise

                if response_data.get("insufficient_balance"):
                    raise common.ErrInsufficientBalance()
            raise
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
    ) -> tuple[list[str] | None, bool]:
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
        try:
            if files:
                response = await self.client.post("/publication/image/generate", data=data, files=files)
            else:
                response = await self.client.post("/publication/image/generate", data=data)
        except httpx.HTTPStatusError as err:
            if err.response.status_code == 400:
                try:
                    response_data = err.response.json()
                except (json.JSONDecodeError, ValueError):
                    raise

                if response_data.get("insufficient_balance"):
                    raise common.ErrInsufficientBalance()
            raise
        json_response = response.json()

        # Проверяем флаг no_image_data от бэкенда
        if "no_image_data" in json_response and json_response["no_image_data"]:
            return None, True

        return json_response["images_url"], False

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
    ) -> int:
        body = {
            "organization_id": organization_id,
            "name": name,
            "hint": hint,
            "goal": goal,
            "tone_of_voice": tone_of_voice,
            "brand_rules": brand_rules,
            "creativity_level": creativity_level,
            "audience_segment": audience_segment,
            "len_min": len_min,
            "len_max": len_max,
            "n_hashtags_min": n_hashtags_min,
            "n_hashtags_max": n_hashtags_max,
            "cta_type": cta_type,
            "cta_strategy": cta_strategy,
            "good_samples": good_samples,
            "bad_samples": bad_samples,
            "additional_info": additional_info,
            "prompt_for_image_style": prompt_for_image_style,
        }
        response = await self.client.post(f"/publication/category", json=body)
        json_response = response.json()

        return json_response["category_id"]

    @traced_method(SpanKind.CLIENT)
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

            prompt_for_image_style: str,
    ) -> str:
        body = {
            "text_reference": user_text_reference,
            "organization_id": organization_id,
            "name": name,
            "hint": hint,
            "goal": goal,
            "tone_of_voice": tone_of_voice,
            "brand_rules": brand_rules,
            "creativity_level": creativity_level,
            "audience_segment": audience_segment,
            "len_min": len_min,
            "len_max": len_max,
            "n_hashtags_min": n_hashtags_min,
            "n_hashtags_max": n_hashtags_max,
            "cta_type": cta_type,
            "cta_strategy": cta_strategy,
            "good_samples": good_samples,
            "bad_samples": bad_samples,
            "additional_info": additional_info,
            "prompt_for_image_style": prompt_for_image_style,
        }
        response = await self.client.post(f"/publication/text/test-generate", json=body)
        json_response = response.json()

        return json_response["text"]

    @traced_method(SpanKind.CLIENT)
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
    ) -> None:
        body = {}

        if name is not None:
            body["name"] = name
        if goal is not None:
            body["goal"] = goal
        if tone_of_voice is not None:
            body["tone_of_voice"] = tone_of_voice
        if brand_rules is not None:
            body["brand_rules"] = brand_rules
        if creativity_level is not None:
            body["creativity_level"] = creativity_level
        if audience_segment is not None:
            body["audience_segment"] = audience_segment
        if len_min is not None:
            body["len_min"] = len_min
        if len_max is not None:
            body["len_max"] = len_max
        if n_hashtags_min is not None:
            body["n_hashtags_min"] = n_hashtags_min
        if n_hashtags_max is not None:
            body["n_hashtags_max"] = n_hashtags_max
        if cta_type is not None:
            body["cta_type"] = cta_type
        if cta_strategy is not None:
            body["cta_strategy"] = cta_strategy
        if good_samples is not None:
            body["good_samples"] = good_samples
        if bad_samples is not None:
            body["bad_samples"] = bad_samples
        if additional_info is not None:
            body["additional_info"] = additional_info
        if prompt_for_image_style is not None:
            body["prompt_for_image_style"] = prompt_for_image_style

        await self.client.put(f"/publication/category/{category_id}", json=body)

    @traced_method(SpanKind.CLIENT)
    async def generate_categories(self, organization_id: int) -> None:
        body = {
            "organization_id": organization_id
        }
        await self.client.post("/publication/categories/generate", json=body)

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
        try:
            await self.client.post("/video-cut/vizard/generate", json=body)
        except httpx.HTTPStatusError as err:
            if err.response.status_code == 400:
                try:
                    response_data = err.response.json()
                except (json.JSONDecodeError, ValueError):
                    raise

                if response_data.get("insufficient_balance"):
                    raise common.ErrInsufficientBalance()
            raise

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
        try:
            response = await self.client.get("/publication/audio/transcribe", data=data, files=files)
        except httpx.HTTPStatusError as err:
            if err.response.status_code == 400:
                try:
                    response_data = err.response.json()
                except (json.JSONDecodeError, ValueError):
                    raise

                if response_data.get("insufficient_balance"):
                    raise common.ErrInsufficientBalance()
            raise

        json_response = response.json()

        return json_response["text"]

    @traced_method(SpanKind.CLIENT)
    async def edit_image(
            self,
            organization_id: int,
            image_content: bytes,
            image_filename: str,
            prompt: str,
    ) -> tuple[list[str] | None, bool]:
        data: dict = {"organization_id": organization_id, "prompt": prompt}

        files = {"image_file": (
            image_filename,
            image_content,
            "image/png"
        )}
        try:
            response = await self.client.post("/image/edit", data=data, files=files)
        except httpx.HTTPStatusError as err:
            if err.response.status_code == 400:
                try:
                    response_data = err.response.json()
                except (json.JSONDecodeError, ValueError):
                    raise

                if response_data.get("insufficient_balance"):
                    raise common.ErrInsufficientBalance()
            raise
        json_response = response.json()

        # Проверяем, вернул ли бэкенд флаг no_image_data
        if "no_image_data" in json_response and json_response["no_image_data"]:
            return None, True

        return json_response["images_url"], False

    @traced_method(SpanKind.CLIENT)
    async def combine_images(
            self,
            organization_id: int,
            category_id: int,
            images_content: list[bytes],
            images_filenames: list[str],
            prompt: str,
    ) -> tuple[list[str] | None, bool]:
        data: dict = {"organization_id": organization_id, "category_id": category_id}

        if prompt is not None:
            data["prompt"] = prompt

        files = []
        for i, (content, filename) in enumerate(zip(images_content, images_filenames)):
            files.append((
                "images_files",
                (filename, content, "image/png")
            ))
        try:
            response = await self.client.post("/image/combine", data=data, files=files)
        except httpx.HTTPStatusError as err:
            if err.response.status_code == 400:
                try:
                    response_data = err.response.json()
                except (json.JSONDecodeError, ValueError):
                    raise

                if response_data.get("insufficient_balance"):
                    raise common.ErrInsufficientBalance()
            raise
        json_response = response.json()

        # Проверяем, вернул ли бэкенд флаг no_image_data
        if "no_image_data" in json_response and json_response["no_image_data"]:
            return None, True

        return json_response["images_url"], False

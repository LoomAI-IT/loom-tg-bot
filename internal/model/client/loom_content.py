from dataclasses import dataclass


@dataclass
class Publication:
    id: int
    organization_id: int
    category_id: int
    creator_id: int
    moderator_id: int | None

    vk_source: bool | None
    tg_source: bool | None

    vk_link: str | None
    tg_link: str | None

    text_reference: str
    text: str
    image_fid: str | None
    image_name: str | None

    openai_rub_cost: int

    moderation_status: str | None
    moderation_comment: str | None

    publication_at: str | None
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "category_id": self.category_id,
            "creator_id": self.creator_id,
            "moderator_id": self.moderator_id,
            "vk_source": self.vk_source,
            "tg_source": self.tg_source,
            "vk_link": self.vk_link,
            "tg_link": self.tg_link,
            "text_reference": self.text_reference,
            "text": self.text,
            "image_fid": self.image_fid,
            "image_name": self.image_name,
            "openai_rub_cost": self.openai_rub_cost,
            "moderation_status": self.moderation_status,
            "moderation_comment": self.moderation_comment,
            "publication_at": self.publication_at,
            "created_at": self.created_at,
        }


@dataclass
class Category:
    id: int
    organization_id: int
    name: str
    hint: str

    goal: str
    tone_of_voice: list[str]
    brand_rules: list[str]

    creativity_level: int
    audience_segment: str

    len_min: int
    len_max: int

    n_hashtags_min: int
    n_hashtags_max: int

    cta_type: str
    cta_strategy: dict

    good_samples: list[dict]
    bad_samples: list[dict]
    additional_info: list[dict]

    prompt_for_image_style: str

    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "hint": self.hint,
            "goal": self.goal,
            "tone_of_voice": self.tone_of_voice,
            "brand_rules": self.brand_rules,
            "creativity_level": self.creativity_level,
            "audience_segment": self.audience_segment,
            "len_min": self.len_min,
            "len_max": self.len_max,
            "n_hashtags_min": self.n_hashtags_min,
            "n_hashtags_max": self.n_hashtags_max,
            "cta_type": self.cta_type,
            "cta_strategy": self.cta_strategy,
            "good_samples": self.good_samples,
            "bad_samples": self.bad_samples,
            "additional_info": self.additional_info,
            "prompt_for_image_style": self.prompt_for_image_style,
            "created_at": self.created_at,
        }

@dataclass
class Autoposting:
    id: int
    organization_id: int

    filter_prompt: str
    rewrite_prompt: str
    tg_channels: list[str]

    created_at: str

@dataclass
class VideoCut:
    id: int
    project_id: int
    organization_id: int
    creator_id: int
    moderator_id: int

    inst_source: bool
    youtube_source: bool

    youtube_video_reference: str
    name: str
    description: str
    transcript: str
    tags: list[str]
    video_fid: str
    video_name: str
    original_url: str

    vizard_rub_cost: int
    moderation_status: str
    moderation_comment: str

    publication_at: str
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "organization_id": self.organization_id,
            "creator_id": self.creator_id,
            "moderator_id": self.moderator_id,
            "inst_source": self.inst_source,
            "youtube_source": self.youtube_source,
            "youtube_video_reference": self.youtube_video_reference,
            "name": self.name,
            "description": self.description,
            "transcript": self.transcript,
            "tags": self.tags,
            "video_fid": self.video_fid,
            "video_name": self.video_name,
            "original_url": self.original_url,
            "vizard_rub_cost": self.vizard_rub_cost,
            "moderation_status": self.moderation_status,
            "moderation_comment": self.moderation_comment,
            "publication_at": self.publication_at,
            "created_at": self.created_at
        }
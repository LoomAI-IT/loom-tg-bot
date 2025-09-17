from dataclasses import dataclass


@dataclass
class Publication:
    id: int
    organization_id: int
    category_id: int
    creator_id: int
    moderator_id: int | None

    vk_source_id: int | None
    tg_source_id: int | None

    text_reference: str
    name: str
    text: str
    tags: list[str]
    image_fid: str | None
    image_name: str | None

    openai_rub_cost: int

    moderation_status: str | None
    moderation_comment: str | None

    time_for_publication: str
    publication_at: str | None
    created_at: str


@dataclass
class Category:
    id: int
    organization_id: int

    name: str

    prompt_for_image_style: str
    prompt_for_text_style: str

    created_at: str

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

    inst_source_id: int
    youtube_source_id: int

    youtube_video_reference: str
    name: str
    description: str
    tags: list[str]
    video_fid: str
    video_name: str

    vizard_rub_cost: int
    moderation_status: str
    moderation_comment: str

    time_for_publication: str
    publication_at: str
    created_at: str
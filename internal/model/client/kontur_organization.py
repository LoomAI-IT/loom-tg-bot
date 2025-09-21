from dataclasses import dataclass


@dataclass
class Organization:
    id: int

    name: str
    rub_balance: str
    autoposting_moderation: bool
    video_cut_description_end_sample: str
    publication_text_end_sample: str

    created_at: str
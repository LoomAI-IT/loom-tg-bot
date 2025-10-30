from dataclasses import dataclass


@dataclass
class Organization:
    id: int
    name: str
    description: str
    rub_balance: str
    tone_of_voice: list[str]
    compliance_rules: list[dict]
    additional_info: list[dict]

    products: list[dict]
    locale: dict

    created_at: str


@dataclass
class CostMultiplier:
    id: int
    organization_id: int
    generate_text_cost_multiplier: float
    transcribe_audio_cost_multiplier: float
    generate_image_cost_multiplier: float
    generate_vizard_video_cut_cost_multiplier: float
    created_at: str
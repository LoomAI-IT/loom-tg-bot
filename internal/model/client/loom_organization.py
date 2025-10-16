from dataclasses import dataclass


@dataclass
class Organization:
    id: int
    name: str
    rub_balance: str
    tone_of_voice: list[str]
    compliance_rules: list[dict]
    additional_info: list[dict]

    products: list[dict]
    locale: dict

    created_at: str
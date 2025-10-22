from dataclasses import dataclass


@dataclass
class ModelPricing:
    input_price: float
    output_price: float
    cached_input_price: float = None


PRICING_TABLE: dict[str, ModelPricing] = {
    # GPT-5 модели (август 2025)
    'gpt-5': ModelPricing(1.25, 10.00, 0.125),
    'gpt-5-2025-08-07': ModelPricing(1.25, 10.00, 0.125),
    'gpt-5-mini': ModelPricing(0.25, 2.00, 0.025),
    'gpt-5-mini-2025-08-07': ModelPricing(0.25, 2.00, 0.025),
    'gpt-5-nano': ModelPricing(0.05, 0.40, 0.005),
    'gpt-5-nano-2025-08-07': ModelPricing(0.05, 0.40, 0.005),

    # GPT-4o модели
    'gpt-4o': ModelPricing(2.50, 10.00),
    'gpt-4o-mini': ModelPricing(0.15, 0.60),

    # GPT-4 модели
    'gpt-4': ModelPricing(30.00, 60.00),
    'gpt-4-turbo': ModelPricing(10.00, 30.00),

    # O-series reasoning модели (декабрь 2024 - январь 2025)
    'o3': ModelPricing(15.00, 60.00),
    'o3-mini': ModelPricing(3.00, 12.00),
    'o1': ModelPricing(15.00, 60.00),
    'o1-mini': ModelPricing(3.00, 12.00),
}

TRANSCRIPTION_PRICING = {
    'whisper-1': 0.006,
    'gpt-4o-transcribe': {
        'per_minute': 0.006,
        'input_tokens': 2.50,
        'output_tokens': 10.00
    },
    'gpt-4o-mini-transcribe': {
        'per_minute': 0.003,
        'input_tokens': 1.25,
        'output_tokens': 5.00
    }
}

IMAGE_PRICING = {
    "dall-e-3": {
        "1024x1024": {
            "standard": 0.040,
            "hd": 0.080
        },
        "1792x1024": {
            "standard": 0.080,
            "hd": 0.120
        },
        "1024x1792": {
            "standard": 0.080,
            "hd": 0.120
        }
    },
    "gpt-image-1": {
        "input_price": 10.00,
        "output_price": 40.00,
        "cached_input_price": 2.50
    }
}

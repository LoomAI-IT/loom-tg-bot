from dataclasses import dataclass


@dataclass
class ModelPricing:
    input_price: float  # За 1M токенов
    output_price: float  # За 1M токенов
    cached_input_price: float = None  # За 1M кешированных токенов


# Таблица цен для Claude моделей (актуальна на октябрь 2024)
CLAUDE_PRICING_TABLE = {
    # Claude 4 Opus
    "claude-opus-4-20250514": ModelPricing(
        input_price=15.00,
        output_price=75.00,
        cached_input_price=1.50
    ),

    # Claude Sonnet 4.5
    "claude-sonnet-4-5-20250929": ModelPricing(
        input_price=3.00,
        output_price=15.00,
        cached_input_price=0.30
    ),

    # Claude Sonnet 4
    "claude-sonnet-4-20250514": ModelPricing(
        input_price=3.00,
        output_price=15.00,
        cached_input_price=0.30
    ),

    # Claude 3.5 Sonnet
    "claude-3-5-sonnet-20241022": ModelPricing(
        input_price=3.00,
        output_price=15.00,
        cached_input_price=0.30
    ),

    "claude-3-5-sonnet-20240620": ModelPricing(
        input_price=3.00,
        output_price=15.00,
        cached_input_price=0.30
    ),

    # Claude 3 Opus
    "claude-3-opus-20240229": ModelPricing(
        input_price=15.00,
        output_price=75.00,
        cached_input_price=1.50
    ),

    # Claude 3 Sonnet
    "claude-3-sonnet-20240229": ModelPricing(
        input_price=3.00,
        output_price=15.00,
        cached_input_price=0.30
    ),

    # Claude 3 Haiku
    "claude-3-haiku-20240307": ModelPricing(
        input_price=0.25,
        output_price=1.25,
        cached_input_price=0.03
    ),

    # Алиасы без дат для удобства
    "claude-opus-4": ModelPricing(
        input_price=15.00,
        output_price=75.00,
        cached_input_price=1.50
    ),

    "claude-sonnet-4-5": ModelPricing(
        input_price=3.00,
        output_price=15.00,
        cached_input_price=0.30
    ),

    "claude-haiku-4-5": ModelPricing(
        input_price=1.00,
        output_price=5.00,
        cached_input_price=0.30
    ),

    "claude-sonnet-4": ModelPricing(
        input_price=3.00,
        output_price=15.00,
        cached_input_price=0.30
    ),

    "claude-3-5-sonnet": ModelPricing(
        input_price=3.00,
        output_price=15.00,
        cached_input_price=0.30
    ),

    "claude-3-opus": ModelPricing(
        input_price=15.00,
        output_price=75.00,
        cached_input_price=1.50
    ),

    "claude-3-sonnet": ModelPricing(
        input_price=3.00,
        output_price=15.00,
        cached_input_price=0.30
    ),

    "claude-3-haiku": ModelPricing(
        input_price=0.25,
        output_price=1.25,
        cached_input_price=0.03
    )
}
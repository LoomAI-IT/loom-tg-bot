import io
import re
import json
from typing import Literal

import httpx
import pypdf
import base64
import openai
from openai.types import ImagesResponse

from openai.types.audio import Transcription, TranscriptionVerbose
from pdf2image import convert_from_bytes
from openai.types.chat.chat_completion import ChatCompletion

from opentelemetry.trace import Status, StatusCode, SpanKind

from internal import interface
from pkg.trace_wrapper import traced_method

from .price import *


class OpenAIClient(interface.IOpenAIClient):
    def __init__(
            self,
            tel: interface.ITelemetry,
            api_key: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self._encoders = {}

        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            http_client=httpx.AsyncClient(proxy="http://32uLYMeQ:jLaDv4WK@193.160.72.227:62940")
        )

    @traced_method(SpanKind.CLIENT)
    async def generate_str(
            self,
            history: list,
            system_prompt: str,
            temperature: float,
            llm_model: str,
            pdf_file: bytes = None,
    ) -> tuple[str, dict]:
        messages = self._prepare_messages(history, system_prompt, pdf_file, llm_model)

        completion_response = await self.client.chat.completions.create(
            model=llm_model,
            messages=messages,
            temperature=temperature,
            reasoning_effort="high"
        )

        generate_cost = self._calculate_llm_cost(completion_response)
        llm_response = completion_response.choices[0].message.content

        return llm_response, generate_cost

    @traced_method()
    async def generate_json(
            self,
            history: list,
            system_prompt: str,
            temperature: float,
            llm_model: str,
            pdf_file: bytes = None,
    ) -> tuple[dict, dict]:

        llm_response_str, initial_generate_cost = await self.generate_str(
            history, system_prompt, temperature, llm_model, pdf_file
        )

        generate_cost = initial_generate_cost

        try:
            llm_response_json = self._extract_and_parse_json(llm_response_str)
        except Exception:
            llm_response_json, retry_generate_cost = await self._retry_llm_generate(
                history, llm_model, temperature, llm_response_str
            )
            generate_cost = {
                'total_cost': round(generate_cost["total_cost"] + retry_generate_cost["total_cost"], 6),
                'input_cost': round(generate_cost["input_cost"] + retry_generate_cost["input_cost"], 6),
                'output_cost': round(generate_cost["output_cost"] + retry_generate_cost["output_cost"], 6),
                'cached_tokens_savings': round(
                    generate_cost["cached_tokens_savings"] + retry_generate_cost["cached_tokens_savings"], 6),
                'reasoning_cost': round(generate_cost["reasoning_cost"] + retry_generate_cost["reasoning_cost"],
                                        6),
                'details': {
                    'model': llm_model,
                    'tokens': {
                        'total_input_tokens': generate_cost["total_input_tokens"] + retry_generate_cost[
                            "total_input_tokens"],
                        'regular_input_tokens': generate_cost["regular_input_tokens"] + retry_generate_cost[
                            "regular_input_tokens"],
                        'cached_tokens': generate_cost["cached_tokens"] + retry_generate_cost["cached_tokens"],
                        'output_tokens': generate_cost["output_tokens"] + retry_generate_cost["output_tokens"],
                        'reasoning_tokens': generate_cost["reasoning_tokens"] + retry_generate_cost[
                            "reasoning_tokens"],
                        'total_tokens': generate_cost["total_tokens"] + retry_generate_cost["total_tokens"]
                    },
                    'costs': {
                        'regular_input_cost': round(
                            generate_cost["regular_input_cost"] + retry_generate_cost["regular_input_cost"], 6),
                        'cached_input_cost': round(
                            generate_cost["cached_input_cost"] + retry_generate_cost["cached_input_cost"], 6),
                        'output_cost': round(generate_cost["output_cost"] + retry_generate_cost["output_cost"],
                                             6),
                        'reasoning_cost': round(
                            generate_cost["reasoning_cost"] + retry_generate_cost["reasoning_cost"], 6)
                    },
                    'pricing': {
                        'input_price_per_1m': generate_cost["total_cost"],
                        'output_price_per_1m': generate_cost["total_cost"],
                        'cached_input_price_per_1m': generate_cost["total_cost"]
                    }
                }
            }

        self.logger.info("Ответ от LLM", {"llm_response_str": llm_response_str})
        return llm_response_json, generate_cost

    @traced_method()
    async def transcribe_audio(
            self,
            audio_file: bytes,
            filename: str,
            audio_model: str,
            language: str = None,
            prompt: str = None,
            response_format: Literal["json", "text", "srt", "verbose_json", "vtt"] = "verbose_json",
            temperature: float = None,
            timestamp_granularities: list[Literal["word", "segment"]] = None
    ) -> tuple[str, dict]:
        """
        Транскрибирует аудиофайл и рассчитывает стоимость операции.

        Args:
            audio_file: Байты аудиофайла
            filename: Имя файла
            audio_model: Модель для транскрипции ("whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe")
            language: Язык аудио (ISO-639-1 код, например "ru", "en")
            prompt: Подсказка для улучшения точности транскрипции
            response_format: Формат ответа
            temperature: Температура семплирования (0-1)
            timestamp_granularities: Детализация временных меток ["word", "segment"]

        Returns:
            Tuple[результат_транскрипции, детали_стоимости_или_None]
        """
        audio_buffer = io.BytesIO(audio_file)
        audio_buffer.name = filename

        api_params: dict = {
            "model": audio_model,
            "file": audio_buffer,
            "response_format": response_format
        }

        if language:
            api_params["language"] = language
        if prompt:
            api_params["prompt"] = prompt
        if temperature is not None:
            api_params["temperature"] = temperature
        if timestamp_granularities:
            api_params["timestamp_granularities"] = timestamp_granularities

        transcript: TranscriptionVerbose = await self.client.audio.transcriptions.create(**api_params)

        cost_details = self._calculate_transcription_cost(audio_model, transcript)
        return transcript.text, cost_details

    @traced_method()
    async def generate_image(
            self,
            prompt: str,
            image_model: Literal["dall-e-3", "gpt-image-1"] = "gpt-image-1",
            size: str = None,
            quality: str = None,
            style: Literal["vivid", "natural"] = None,
            n: int = 1,
    ) -> tuple[list[str], dict]:
        """
        Генерирует изображения по текстовому описанию.

        Args:
            prompt: Текстовое описание желаемого изображения (до 4000 символов для DALL-E 3)
            image_model: Модель для генерации ("dall-e-3" или "gpt-image-1")
            size: Размер изображения:
                - DALL-E 3: "1024x1024", "1792x1024", "1024x1792"
                - gpt-image-1: "1024x1024", "1024x1536", "1536x1024"
            quality: Качество изображения:
                - DALL-E 3: "standard" или "hd"
                - gpt-image-1: "low", "medium", "high"
            style: Стиль изображения (только для DALL-E 3): "vivid" или "natural"
            n: Количество изображений (1 для DALL-E 3, 1-10 для gpt-image-1)

        Returns:
            Tuple[список изображений, детали стоимости]
            Каждое изображение содержит либо 'url', либо 'b64_json' в зависимости от response_format
        """

        params = {
            "model": image_model,
            "prompt": prompt,
            "n": n,
        }

        if image_model == "dall-e-3":
            if n != 1:
                self.logger.warning(f"DALL-E 3 поддерживает только n=1, изменено с {n} на 1")
                params["n"] = 1

            if size:
                if size not in ["1024x1024", "1792x1024", "1024x1792"]:
                    raise ValueError(f"Недопустимый размер для DALL-E 3: {size}")
                params["size"] = size
            else:
                params["size"] = "1024x1024"

            if quality:
                if quality not in ["standard", "hd"]:
                    raise ValueError(f"Недопустимое качество для DALL-E 3: {quality}")
                params["quality"] = quality
            else:
                params["quality"] = "standard"

            if style:
                params["style"] = style

        elif image_model == "gpt-image-1":
            if size:
                if size not in ["1024x1024", "1024x1536", "1536x1024"]:
                    raise ValueError(f"Недопустимый размер для gpt-image-1: {size}")
                params["size"] = size
            else:
                params["size"] = "1024x1024"

            if quality:
                if quality not in ["low", "medium", "high"]:
                    raise ValueError(f"Недопустимое качество для gpt-image-1: {quality}")
                params["quality"] = quality
            else:
                params["quality"] = "high"

            if style:
                self.logger.warning("gpt-image-1 не поддерживает параметр style, игнорируется")

        response: ImagesResponse = await self.client.images.generate(**params)

        images = []
        for img_data in response.data:
            images.append(img_data.b64_json)

        cost_details = self._calculate_image_cost(
            image_model=image_model,
            response=response,
            quality=params.get("quality"),
            size=params.get("size")
        )

        return images, cost_details

    @traced_method()
    async def edit_image(
            self,
            image: bytes,
            prompt: str,
            mask: bytes = None,
            quality: str = None,
            image_model: Literal["gpt-image-1"] = "gpt-image-1",
            size: str = None,
            n: int = 1,
    ) -> tuple[list[str], dict]:
        if image_model != "gpt-image-1":
            raise ValueError("Редактирование изображений поддерживается только для gpt-image-1")

        if isinstance(image, bytes):
            image_file = io.BytesIO(image)
            image_file.name = "image.png"
        else:
            image_file = image

        mask_file = None
        if mask:
            if isinstance(mask, bytes):
                mask_file = io.BytesIO(mask)
                mask_file.name = "mask.png"
            else:
                mask_file = mask

        params = {
            "image": image_file,
            "prompt": prompt,
            "model": image_model,
            "n": n,
        }

        # Добавляем маску если есть
        if mask_file:
            params["mask"] = mask_file

        if quality:
            if quality not in ["low", "medium", "high"]:
                params["quality"] = quality

        # Размер
        if size:
            if size not in ["1024x1024", "1024x1536", "1536x1024"]:
                raise ValueError(f"Недопустимый размер для редактирования: {size}")
            params["size"] = size
        else:
            params["size"] = "1024x1024"

        response: ImagesResponse = await self.client.images.edit(**params)

        images = []
        for img_data in response.data:
            images.append(img_data.b64_json)

        cost_details = self._calculate_image_cost(
            image_model=image_model,
            response=response,
            quality=quality,
            size=params.get("size")
        )

        return images, cost_details

    def _calculate_image_cost(
            self,
            image_model: str,
            response: ImagesResponse,
            quality: str = None,
            size: str = None,
    ) -> dict:
        """
        Рассчитывает стоимость операции с изображениями на основе токенов.

        Args:
            image_model: Используемая модель
            response: Ответ от API с информацией об usage
            quality: Качество изображения - для совместимости
            size: Размер изображения - для совместимости

        Returns:
            Словарь с деталями стоимости
        """
        if image_model not in IMAGE_PRICING:
            return {
                "error": f"Модель {image_model} не найдена в таблице цен",
                "model": image_model,
            }

        pricing = IMAGE_PRICING[image_model]

        if image_model == "dall-e-3":
            size_pricing = pricing.get(size, pricing.get("1024x1024"))
            price_per_image = size_pricing.get(quality, 0)
            count = len(response.data)
            total_cost = price_per_image * count

            return {
                "total_cost": round(total_cost, 4),
                "price_per_image": round(price_per_image, 4),
                "count": count,
                "billing_method": "per_image",
                "details": {
                    "model": image_model,
                    "quality": quality,
                    "size": size,
                }
            }
        if not hasattr(response, 'usage') or response.usage is None:
            return {
                "error": "Usage информация отсутствует в ответе API",
                "model": image_model,
            }

        usage = response.usage
        total_input_tokens = usage.input_tokens

        cached_tokens = 0
        if hasattr(usage, 'input_tokens_details') and usage.input_tokens_details:
            cached_tokens = getattr(usage.input_tokens_details, 'cached_tokens', 0)

        regular_input_tokens = total_input_tokens - cached_tokens
        output_tokens = usage.output_tokens
        regular_input_cost = (regular_input_tokens / 1_000_000) * pricing["input_price"]

        cached_input_cost = 0
        cached_tokens_savings = 0
        if cached_tokens > 0:
            cached_input_cost = (cached_tokens / 1_000_000) * pricing["cached_input_price"]
            full_price_for_cached = (cached_tokens / 1_000_000) * pricing["input_price"]
            cached_tokens_savings = full_price_for_cached - cached_input_cost

        total_input_cost = regular_input_cost + cached_input_cost
        output_cost = (output_tokens / 1_000_000) * pricing["output_price"]
        total_cost = total_input_cost + output_cost

        return {
            "total_cost": round(total_cost, 6),
            "input_cost": round(total_input_cost, 6),
            "output_cost": round(output_cost, 6),
            "cached_tokens_savings": round(cached_tokens_savings, 6),
            "billing_method": "per_token",
            "details": {
                "model": image_model,
                "quality": quality,
                "size": size,
                "tokens": {
                    "total_input_tokens": total_input_tokens,
                    "regular_input_tokens": regular_input_tokens,
                    "cached_tokens": cached_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": usage.total_tokens
                },
                "costs": {
                    "regular_input_cost": round(regular_input_cost, 6),
                    "cached_input_cost": round(cached_input_cost, 6),
                    "output_cost": round(output_cost, 6)
                },
                "pricing": {
                    "input_price_per_1m": pricing["input_price"],
                    "output_price_per_1m": pricing["output_price"],
                    "cached_input_price_per_1m": pricing["cached_input_price"]
                }
            }
        }

    async def download_image_from_url(
            self,
            image_url: str
    ) -> bytes:
        with self.tracer.start_as_current_span(
                "GPTClient.download_image_from_url",
                kind=SpanKind.CLIENT,
        ) as span:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url)
                    response.raise_for_status()

                span.set_status(Status(StatusCode.OK))
                return response.content

            except Exception as err:

                span.set_status(StatusCode.ERROR, str(err))
                raise

    def _prepare_messages(self, history: list, system_prompt: str, pdf_file: bytes, llm_model: str) -> list:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.extend([
            {"role": message["role"], "content": message["content"]}
            for message in history
        ])

        if pdf_file:
            if llm_model in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4-turbo-preview"]:
                # Vision модели - конвертируем в изображения
                images = self._pdf_to_images(pdf_file)
                content = [{"type": "text", "text": messages[-1]["content"]}]

                for img_base64 in images:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}",
                            "detail": "high"
                        }
                    })

                messages[-1]["content"] = content
            else:
                # Текстовые модели - извлекаем текст
                pdf_text = self._extract_text_from_pdf(pdf_file)
                messages[-1]["content"] += f"\n\nСодержимое PDF:\n{pdf_text}"

        return messages

    def _calculate_llm_cost(
            self,
            completion_response: ChatCompletion,
    ) -> dict:
        llm_model = completion_response.model

        if llm_model not in PRICING_TABLE:
            base_model = llm_model.split('-20')[0] if '-20' in llm_model else llm_model
            if base_model not in PRICING_TABLE:
                return {
                    'error': f'Модель {llm_model} не найдена в таблице цен',
                    'available_models': list(PRICING_TABLE.keys())
                }
            llm_model = base_model

        pricing = PRICING_TABLE[llm_model]

        usage = completion_response.usage
        total_input_tokens = usage.prompt_tokens

        cached_tokens = usage.prompt_tokens_details.cached_tokens
        regular_input_tokens = total_input_tokens - cached_tokens

        output_tokens = usage.completion_tokens
        reasoning_tokens = usage.completion_tokens_details.reasoning_tokens
        regular_input_cost = (regular_input_tokens / 1_000_000) * pricing.input_price

        cached_input_cost = 0
        cached_tokens_savings = 0
        if cached_tokens > 0 and pricing.cached_input_price:
            cached_input_cost = (cached_tokens / 1_000_000) * pricing.cached_input_price
            full_price_for_cached = (cached_tokens / 1_000_000) * pricing.input_price
            cached_tokens_savings = full_price_for_cached - cached_input_cost

        total_input_cost = regular_input_cost + cached_input_cost
        output_cost = (output_tokens / 1_000_000) * pricing.output_price
        reasoning_cost = (reasoning_tokens / 1_000_000) * pricing.output_price if reasoning_tokens > 0 else 0
        total_cost = total_input_cost + output_cost

        result = {
            'total_cost': round(total_cost, 6),
            'input_cost': round(total_input_cost, 6),
            'output_cost': round(output_cost, 6),
            'cached_tokens_savings': round(cached_tokens_savings, 6),
            'reasoning_cost': round(reasoning_cost, 6),
            'details': {
                'model': llm_model,
                'tokens': {
                    'total_input_tokens': total_input_tokens,
                    'regular_input_tokens': regular_input_tokens,
                    'cached_tokens': cached_tokens,
                    'output_tokens': output_tokens,
                    'reasoning_tokens': reasoning_tokens,
                    'total_tokens': usage.total_tokens
                },
                'costs': {
                    'regular_input_cost': round(regular_input_cost, 6),
                    'cached_input_cost': round(cached_input_cost, 6),
                    'output_cost': round(output_cost, 6),
                    'reasoning_cost': round(reasoning_cost, 6)
                },
                'pricing': {
                    'input_price_per_1m': pricing.input_price,
                    'output_price_per_1m': pricing.output_price,
                    'cached_input_price_per_1m': pricing.cached_input_price
                }
            }
        }

        return result

    async def _retry_llm_generate(
            self,
            history: list,
            llm_model: str,
            temperature: float,
            llm_response_str: str,
    ) -> tuple[dict, dict]:
        self.logger.warning("LLM потребовался retry", {"llm_response": llm_response_str})

        retry_messages = [
            *[{"role": msg["role"], "content": msg["content"]} for msg in history],
            {"role": "assistant", "content": llm_response_str},
            {"role": "user", "content": "Я же просил JSON формат, как в системном промпте, дай ответ в JSON формате или твой JSON не валидный, проверь его на валидность="},
        ]

        completion_response = await self.client.chat.completions.create(
            model=llm_model,
            messages=retry_messages,
            temperature=temperature,
        )
        generate_cost = self._calculate_llm_cost(completion_response)

        llm_response_str = completion_response.choices[0].message.content
        llm_response_json = self._extract_and_parse_json(llm_response_str)

        return llm_response_json, generate_cost

    def _extract_and_parse_json(self, text: str) -> dict:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        json_str = match.group(0)
        data = json.loads(json_str)
        return data

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        with self.tracer.start_as_current_span(
                "GPTClient._extract_text_from_pdf",
                kind=SpanKind.CLIENT,
        ) as span:
            try:
                reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
            except Exception as err:

                span.set_status(StatusCode.ERROR, str(err))
                raise

    def _pdf_to_images(self, pdf_bytes: bytes) -> list[str]:
        with self.tracer.start_as_current_span(
                "GPTClient._pdf_to_images",
                kind=SpanKind.CLIENT,
        ) as span:
            try:
                images = convert_from_bytes(pdf_bytes, dpi=200)
                base64_images = []

                for img in images:
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    img_data = buffer.getvalue()
                    base64_image = base64.b64encode(img_data).decode('utf-8')
                    base64_images.append(base64_image)

                return base64_images
            except Exception as err:

                span.set_status(StatusCode.ERROR, str(err))
                raise

    def _calculate_transcription_cost(
            self,
            audio_model: str,
            transcription_result: Transcription | TranscriptionVerbose
    ) -> dict:
        """
        Рассчитывает стоимость транскрипции на основе результата API.
        """
        if audio_model not in TRANSCRIPTION_PRICING:
            return {
                'error': f'Неизвестная модель: {audio_model}',
                'available_models': list(TRANSCRIPTION_PRICING.keys())
            }

        pricing = TRANSCRIPTION_PRICING[audio_model]

        # Для whisper-1 - только по минутам
        if audio_model == 'whisper-1':
            if isinstance(transcription_result, TranscriptionVerbose) and hasattr(transcription_result, 'duration'):
                duration_minutes = transcription_result.duration / 60
                cost = duration_minutes * pricing

                return {
                    'total_cost': round(cost, 6),
                    'model': audio_model,
                    'billing_method': 'per_minute',
                    'details': {
                        'duration_minutes': round(duration_minutes, 4),
                        'duration_seconds': round(transcription_result.duration, 2),
                        'price_per_minute': pricing
                    }
                }
            else:
                return {
                    'error': 'Для whisper-1 нужен response_format="verbose_json" для получения duration'
                }

        # Для gpt-4o моделей - сначала пробуем по токенам
        if hasattr(transcription_result, 'usage') and transcription_result.usage:
            usage = transcription_result.usage
            input_tokens = getattr(usage, 'prompt_tokens', 0)
            output_tokens = getattr(usage, 'completion_tokens', 0)

            input_cost = (input_tokens / 1_000_000) * pricing['input_tokens']
            output_cost = (output_tokens / 1_000_000) * pricing['output_tokens']
            total_cost = input_cost + output_cost

            return {
                'total_cost': round(total_cost, 6),
                'input_cost': round(input_cost, 6),
                'output_cost': round(output_cost, 6),
                'model': audio_model,
                'billing_method': 'per_token',
                'details': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': input_tokens + output_tokens,
                    'input_price_per_1m': pricing['input_tokens'],
                    'output_price_per_1m': pricing['output_tokens']
                }
            }

        # Fallback: расчет по минутам для gpt-4o моделей
        if isinstance(transcription_result, TranscriptionVerbose) and hasattr(transcription_result, 'duration'):
            duration_minutes = transcription_result.duration / 60
            cost = duration_minutes * pricing['per_minute']

            return {
                'total_cost': round(cost, 6),
                'model': audio_model,
                'billing_method': 'per_minute_fallback',
                'details': {
                    'duration_minutes': round(duration_minutes, 4),
                    'duration_seconds': round(transcription_result.duration, 2),
                    'price_per_minute': pricing['per_minute']
                }
            }

        return {
            'error': f'Не удалось рассчитать стоимость для модели {audio_model}',
            'help': 'Используйте response_format="verbose_json" или модель с поддержкой usage'
        }

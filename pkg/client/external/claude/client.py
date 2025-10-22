import re
import json
import ast

import httpx
from anthropic import AsyncAnthropic
from anthropic.types import Message

from opentelemetry.trace import SpanKind

from internal import interface
from pkg.trace_wrapper import traced_method

from .price import *


class AnthropicClient(interface.IAnthropicClient):
    def __init__(
            self,
            tel: interface.ITelemetry,
            api_key: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

        self.client = AsyncAnthropic(
            api_key=api_key,
            http_client=httpx.AsyncClient(proxy="http://user331580:52876b@163.5.189.163:2667")
        )

    @traced_method(SpanKind.CLIENT)
    async def generate_str(
            self,
            history: list,
            system_prompt: str,
            temperature: float = 1.0,
            llm_model: str = "claude-haiku-4-5",
            max_tokens: int = 4096,
            thinking_tokens: int = None,
            enable_caching: bool = True,
            cache_ttl: str = "5m",
            enable_web_search: bool = True,
            max_searches: int = 5,
    ) -> tuple[str, dict]:
        messages = self._prepare_messages(history, enable_caching=enable_caching)

        api_params: dict = {
            "model": llm_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }

        if system_prompt:
            if enable_caching:
                api_params["system"] = [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral", "ttl": cache_ttl}
                    }
                ]
            else:
                api_params["system"] = system_prompt

        if enable_web_search:
            api_params["tools"] = [{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_searches
            }]

        if thinking_tokens is not None and thinking_tokens > 0:
            api_params["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_tokens
            }

        completion_response = await self.client.messages.create(**api_params)

        generate_cost = self._calculate_llm_cost(completion_response, llm_model)

        web_search_info = self._extract_web_search_info(completion_response)
        if web_search_info["used"]:
            self.logger.info("Claude использовал веб-поиск", web_search_info)

        llm_response = ""
        for content_block in completion_response.content:
            if content_block.type == "text":
                llm_response += content_block.text
            elif content_block.type == "thinking":
                self.logger.debug("Extended thinking", {"thinking": content_block.thinking})

        return llm_response, generate_cost

    @traced_method()
    async def generate_json(
            self,
            history: list,
            system_prompt: str,
            temperature: float = 1.0,
            llm_model: str = "claude-haiku-4-5",
            max_tokens: int = 4096,
            thinking_tokens: int = None,
            enable_caching: bool = True,
            cache_ttl: str = "5m",
            enable_web_search: bool = True,
            max_searches: int = 5,
    ) -> tuple[dict, dict]:

        llm_response_str, initial_generate_cost = await self.generate_str(
            history,
            system_prompt,
            temperature,
            llm_model,
            max_tokens,
            thinking_tokens,
            enable_caching,
            cache_ttl
        )

        generate_cost = initial_generate_cost

        try:
            llm_response_json = self._extract_and_parse_json(llm_response_str)
        except Exception:
            llm_response_json, retry_generate_cost = await self._retry_llm_generate(
                history,
                llm_model,
                temperature,
                llm_response_str,
                system_prompt,
                enable_caching
            )
            generate_cost = {
                'total_cost': round(generate_cost["total_cost"] + retry_generate_cost["total_cost"], 6),
                'input_cost': round(generate_cost["input_cost"] + retry_generate_cost["input_cost"], 6),
                'output_cost': round(generate_cost["output_cost"] + retry_generate_cost["output_cost"], 6),
                'cached_tokens_savings': round(
                    generate_cost["cached_tokens_savings"] + retry_generate_cost["cached_tokens_savings"], 6),
                'details': {
                    'model': llm_model,
                    'tokens': {
                        'total_input_tokens': generate_cost["details"]["tokens"]["total_input_tokens"] +
                                              retry_generate_cost["details"]["tokens"]["total_input_tokens"],
                        'regular_input_tokens': generate_cost["details"]["tokens"]["regular_input_tokens"] +
                                                retry_generate_cost["details"]["tokens"]["regular_input_tokens"],
                        'cached_tokens': generate_cost["details"]["tokens"]["cached_tokens"] +
                                         retry_generate_cost["details"]["tokens"]["cached_tokens"],
                        'output_tokens': generate_cost["details"]["tokens"]["output_tokens"] +
                                         retry_generate_cost["details"]["tokens"]["output_tokens"],
                        'total_tokens': generate_cost["details"]["tokens"]["total_tokens"] +
                                        retry_generate_cost["details"]["tokens"]["total_tokens"]
                    },
                    'costs': {
                        'regular_input_cost': round(
                            generate_cost["details"]["costs"]["regular_input_cost"] +
                            retry_generate_cost["details"]["costs"]["regular_input_cost"], 6),
                        'cached_input_cost': round(
                            generate_cost["details"]["costs"]["cached_input_cost"] +
                            retry_generate_cost["details"]["costs"]["cached_input_cost"], 6),
                        'output_cost': round(
                            generate_cost["details"]["costs"]["output_cost"] +
                            retry_generate_cost["details"]["costs"]["output_cost"], 6)
                    },
                    'pricing': generate_cost["details"]["pricing"]
                }
            }

        self.logger.info("Ответ от LLM", {"llm_response": llm_response_json})
        return llm_response_json, generate_cost

    def _prepare_messages(self, history: list, enable_caching: bool = True, cache_ttl: str = "5m") -> list:
        if not history:
            return []

        messages = []

        # Находим индекс последнего сообщения ассистента
        last_assistant_idx = None
        for i in range(len(history) - 1, -1, -1):
            if history[i]["role"] == "assistant":
                last_assistant_idx = i
                break

        for i, message in enumerate(history):
            # Кэшируем последнее сообщение ассистента
            should_cache = (
                    enable_caching
                    and last_assistant_idx is not None
                    and i == last_assistant_idx
            )

            if should_cache:
                messages.append({
                    "role": message["role"],
                    "content": [
                        {
                            "type": "text",
                            "text": message["content"],
                            "cache_control": {"type": "ephemeral", "ttl": cache_ttl}
                        }
                    ]
                })
            else:
                messages.append({
                    "role": message["role"],
                    "content": message["content"]
                })

        return messages

    def _calculate_llm_cost(
            self,
            completion_response: Message,
            llm_model: str
    ) -> dict:
        if llm_model not in CLAUDE_PRICING_TABLE:
            base_model = llm_model.split('-20')[0] if '-20' in llm_model else llm_model
            if base_model not in CLAUDE_PRICING_TABLE:
                return {
                    'error': f'Модель {llm_model} не найдена в таблице цен',
                    'available_models': list(CLAUDE_PRICING_TABLE.keys())
                }
            llm_model = base_model

        pricing = CLAUDE_PRICING_TABLE[llm_model]

        usage = completion_response.usage
        total_input_tokens = usage.input_tokens

        # Claude API предоставляет информацию о кешированных токенах
        cached_tokens = getattr(usage, 'cache_read_input_tokens', 0)
        cache_creation_tokens = getattr(usage, 'cache_creation_input_tokens', 0)
        regular_input_tokens = total_input_tokens - cached_tokens - cache_creation_tokens

        output_tokens = usage.output_tokens

        # Расчет стоимости
        regular_input_cost = (regular_input_tokens / 1_000_000) * pricing.input_price
        cache_creation_cost = (cache_creation_tokens / 1_000_000) * pricing.input_price

        cached_input_cost = 0
        cached_tokens_savings = 0
        if cached_tokens > 0 and pricing.cached_input_price:
            cached_input_cost = (cached_tokens / 1_000_000) * pricing.cached_input_price
            full_price_for_cached = (cached_tokens / 1_000_000) * pricing.input_price
            cached_tokens_savings = full_price_for_cached - cached_input_cost

        web_search_cost = 0
        web_search_requests = 0

        if hasattr(completion_response.usage, 'server_tool_use'):
            server_tool_use = completion_response.usage.server_tool_use
            if hasattr(server_tool_use, 'web_search_requests'):
                web_search_requests = server_tool_use.web_search_requests
                web_search_cost = web_search_requests * 0.01

        total_input_cost = regular_input_cost + cached_input_cost + cache_creation_cost
        output_cost = (output_tokens / 1_000_000) * pricing.output_price
        total_cost = total_input_cost + output_cost + web_search_cost

        result = {
            'total_cost': round(total_cost, 6),
            'input_cost': round(total_input_cost, 6),
            'output_cost': round(output_cost, 6),
            'web_search_cost': round(web_search_cost, 6),
            'cached_tokens_savings': round(cached_tokens_savings, 6),
            'details': {
                'model': llm_model,
                'web_search_requests': web_search_requests,
                'tokens': {
                    'total_input_tokens': total_input_tokens,
                    'regular_input_tokens': regular_input_tokens,
                    'cached_tokens': cached_tokens,
                    'cache_creation_tokens': cache_creation_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': total_input_tokens + output_tokens
                },
                'costs': {
                    'regular_input_cost': round(regular_input_cost, 6),
                    'cached_input_cost': round(cached_input_cost, 6),
                    'cache_creation_cost': round(cache_creation_cost, 6),
                    'output_cost': round(output_cost, 6)
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
            system_prompt: str,
            enable_caching: bool = True
    ) -> tuple[dict, dict]:
        self.logger.warning("LLM потребовался retry", {"llm_response": llm_response_str})

        retry_history = [
            *history,
            {"role": "assistant", "content": llm_response_str},
            {"role": "user",
             "content": "Я же просил JSON формат, как в системном промпте, дай ответ в JSON формате или твой JSON не валидный, проверь его на валидность"},
        ]

        retry_messages = self._prepare_messages(retry_history, enable_caching=enable_caching)

        api_params = {
            "model": llm_model,
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": retry_messages
        }

        if system_prompt:
            if enable_caching:
                api_params["system"] = [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            else:
                api_params["system"] = system_prompt

        completion_response = await self.client.messages.create(**api_params)

        generate_cost = self._calculate_llm_cost(completion_response, llm_model)

        llm_response_str = completion_response.content[0].text
        llm_response_json = self._extract_and_parse_json(llm_response_str)

        return llm_response_json, generate_cost

    def _extract_web_search_info(self, completion_response: Message) -> dict:
        web_search_info = {
            "used": False,
            "total_searches": 0,
            "searches": []
        }

        # Проверяем usage для количества поисков
        if hasattr(completion_response.usage, 'server_tool_use'):
            server_tool_use = completion_response.usage.server_tool_use
            if hasattr(server_tool_use, 'web_search_requests'):
                web_search_info["total_searches"] = server_tool_use.web_search_requests
                web_search_info["used"] = server_tool_use.web_search_requests > 0

        # Извлекаем детали каждого поиска
        for i, content_block in enumerate(completion_response.content):
            # Поисковый запрос
            if content_block.type == "server_tool_use" and content_block.name == "web_search":
                search_query = content_block.input.get("query", "")

                search_info = {
                    "tool_use_id": content_block.id,
                    "query": search_query,
                    "results": []
                }

                # Ищем соответствующие результаты
                for result_block in completion_response.content[i + 1:]:
                    if (result_block.type == "web_search_tool_result" and
                            result_block.tool_use_id == content_block.id):

                        # Извлекаем результаты поиска
                        if hasattr(result_block, 'content') and isinstance(result_block.content, list):
                            for result in result_block.content:
                                if result.type == "web_search_result":
                                    search_info["results"].append({
                                        "title": result.title,
                                        "url": result.url,
                                        "page_age": getattr(result, 'page_age', None)
                                    })
                        break

                web_search_info["searches"].append(search_info)

        return web_search_info

    def _extract_and_parse_json(self, text: str) -> dict:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        json_str = match.group(0)

        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError:
            try:
                data = ast.literal_eval(json_str)
                if isinstance(data, dict):
                    return data
                else:
                    raise ValueError(f"Результат не является словарем: {type(data)}")
            except (ValueError, SyntaxError) as e:
                raise

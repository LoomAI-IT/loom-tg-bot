from functools import wraps
from typing import Any, Callable
from opentelemetry.trace import SpanKind, StatusCode
import inspect


def traced_method(
        span_kind: SpanKind = SpanKind.INTERNAL,
        exclude_params: set[str] = None,
        sensitive_params: set[str] = None
):
    if exclude_params is None:
        exclude_params = {'self', 'cls'}
    if sensitive_params is None:
        sensitive_params = {'password', 'token', 'secret', 'api_key'}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # Получаем имя класса и метода
            class_name = self.__class__.__name__
            method_name = func.__name__
            span_name = f"{class_name}.{method_name}"

            # Собираем все параметры
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()

            # Формируем атрибуты для span'а
            attributes = {}
            for param_name, param_value in bound_args.arguments.items():
                if param_name in exclude_params:
                    continue

                # Маскируем чувствительные данные
                if param_name in sensitive_params:
                    attributes[param_name] = "***REDACTED***"
                else:
                    # Конвертируем значение в строку для атрибутов
                    attributes[param_name] = _serialize_value(param_value)

            # Создаем span
            with self.tracer.start_as_current_span(
                    span_name,
                    kind=span_kind,
                    attributes=attributes
            ) as span:
                try:
                    result = await func(self, *args, **kwargs)
                    span.set_status(StatusCode.OK)
                    return result
                except Exception as e:
                    span.set_status(StatusCode.ERROR, str(e))
                    raise

        @wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            class_name = self.__class__.__name__
            method_name = func.__name__
            span_name = f"{class_name}.{method_name}"

            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()

            attributes = {}
            for param_name, param_value in bound_args.arguments.items():
                if param_name in exclude_params:
                    continue

                if param_name in sensitive_params:
                    attributes[param_name] = "***REDACTED***"
                else:
                    attributes[param_name] = _serialize_value(param_value)

            with self.tracer.start_as_current_span(
                    span_name,
                    kind=span_kind,
                    attributes=attributes
            ) as span:
                try:
                    result = func(self, *args, **kwargs)
                    span.set_status(StatusCode.OK)
                    return result
                except Exception as e:
                    span.set_status(StatusCode.ERROR, str(e))
                    span.record_exception(e)
                    raise

        # Возвращаем нужную обертку в зависимости от типа функции
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _serialize_value(value: Any) -> str:
    """Сериализует значение для атрибутов OpenTelemetry."""
    if value is None:
        return "None"
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, (list, tuple, dict)):
        return f"[{len(value)} items]"
    if isinstance(value, dict):
        return f"{{dict with {len(value)} keys}}"

    return f"<{value.__class__.__name__}>"
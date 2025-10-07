import functools
import traceback
from typing import Callable, Any
import inspect

def auto_log():
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs) -> Any:
            class_name = self.__class__.__name__
            method_name = func.__name__

            logger = getattr(self, 'logger', None)

            if logger:
                logger.info(f"Начало {class_name}.{method_name}")

            try:
                result = await func(self, *args, **kwargs)

                if logger:
                    logger.info(f"Завершение {class_name}.{method_name}")

                return result
            except Exception as e:
                if logger:
                    logger.error(f"Ошибка в {class_name}.{method_name}: {str(e)}", {
                        "traceback": traceback.format_exc(),
                    })
                raise

        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs) -> Any:
            class_name = self.__class__.__name__
            method_name = func.__name__

            logger = getattr(self, 'logger', None)

            if logger:
                logger.info(f"Начало {class_name}.{method_name}")

            try:
                result = func(self, *args, **kwargs)

                if logger:
                    logger.info(f"Завершение {class_name}.{method_name}")

                return result
            except Exception as e:
                if logger:
                    logger.error(f"Ошибка в {class_name}.{method_name}: {str(e)}", {
                        "traceback": traceback.format_exc(),
                    })
                raise

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
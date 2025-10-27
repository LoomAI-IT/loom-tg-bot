from datetime import datetime


class _DateTimeFormatter:
    """Форматирует даты для отображения"""

    @staticmethod
    def format_datetime(dt: str | datetime) -> str:
        """
        Форматирует datetime в читаемый вид
        Возвращает строку в формате "DD.MM.YYYY HH:MM"
        """
        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            # Форматируем в читаемый вид
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            # Если не удалось отформатировать, возвращаем как есть
            return str(dt)

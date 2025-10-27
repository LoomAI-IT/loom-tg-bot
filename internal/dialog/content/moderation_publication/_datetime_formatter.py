from datetime import datetime


class _DateTimeFormatter:
    @staticmethod
    def format_datetime(dt: str | datetime) -> str:
        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:

            return str(dt)

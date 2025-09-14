from datetime import datetime
from dataclasses import dataclass


@dataclass
class State:
    id: int
    tg_chat_id: int

    status: str
    access_token: str
    refresh_token: str

    created_at: datetime
    updated_at: datetime

    @classmethod
    def serialize(cls, rows) -> list:
        return [
            cls(
                id=row.id,
                tg_chat_id=row.tg_chat_id,
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

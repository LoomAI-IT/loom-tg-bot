from datetime import datetime
from dataclasses import dataclass


@dataclass
class UserState:
    id: int
    tg_chat_id: int
    account_id: int
    organization_id: int

    access_token: str
    refresh_token: str

    created_at: datetime

    @classmethod
    def serialize(cls, rows) -> list:
        return [
            cls(
                id=row.id,
                tg_chat_id=row.tg_chat_id,
                account_id=row.account_id,
                organization_id=row.organization_id,
                access_token=row.access_token,
                refresh_token=row.refresh_token,
                created_at=row.created_at,
            )
            for row in rows
        ]

@dataclass
class CachedFile:
    id: int
    filename: str

    file_id: str

    created_at: datetime

    @classmethod
    def serialize(cls, rows) -> list:
        return [
            cls(
                id=row.id,
                filename=row.filename,
                file_id=row.file_id,
                created_at=row.created_at,
            )
            for row in rows
        ]



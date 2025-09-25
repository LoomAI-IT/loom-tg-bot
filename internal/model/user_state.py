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
    tg_username: str
    can_show_alerts: bool
    show_error_recovery: bool

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
                tg_username=row.tg_username,
                can_show_alerts=row.can_show_alerts,
                show_error_recovery=row.show_error_recovery,
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


@dataclass
class VizardVideoCutAlert:
    id: int
    state_id: int
    youtube_video_reference: str
    video_count: int
    created_at: datetime

    @classmethod
    def serialize(cls, rows) -> list:
        return [
            cls(
                id=row.id,
                state_id=row.state_id,
                youtube_video_reference=row.youtube_video_reference,
                video_count=row.video_count,
                created_at=row.created_at,
            )
            for row in rows
        ]


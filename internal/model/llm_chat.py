from dataclasses import dataclass
from datetime import datetime


@dataclass
class LLMChat:
    id: int
    state_id: int
    created_at: datetime

    @classmethod
    def serialize(cls, rows) -> list['LLMChat']:
        return [
            cls(
                id=row.id,
                state_id=row.state_id,
                created_at=row.created_at,
            ) for row in rows
        ]

@dataclass
class LLMMessage:
    id: int
    chat_id: int
    role: str
    text: str

    created_at: datetime

    @classmethod
    def serialize(cls, rows) -> list:
        return [
            cls(
                id=row.id,
                chat_id=row.chat_id,
                role=row.role,
                text=row.text,
                created_at=row.created_at,
            ) for row in rows
        ]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "role": self.role,
            "text": self.text,
            "created_at": self.created_at.isoformat()
        }
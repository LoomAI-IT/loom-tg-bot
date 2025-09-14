from pydantic import BaseModel


class SendMessageWebhookBody(BaseModel):
    tg_chat_id: int
    text: str

class DeleteStateBody(BaseModel):
    tg_chat_id: int
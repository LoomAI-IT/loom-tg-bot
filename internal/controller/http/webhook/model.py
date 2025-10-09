from pydantic import BaseModel


class EmployeeNotificationBody(BaseModel):
    account_id: int
    organization_id: int
    employee_name: str
    role: str
    interserver_secret_key: str

class SetCacheFileBody(BaseModel):
    interserver_secret_key: str
    filename: str
    file_id: str

class NotifyVizardVideoCutGenerated(BaseModel):
    account_id: int
    youtube_video_reference: str
    video_count: int
    interserver_secret_key: str

class NotifyPublicationApprovedBody(BaseModel):
    account_id: int
    publication_id: int
    interserver_secret_key: str


class SendMessageWebhookBody(BaseModel):
    tg_chat_id: int
    text: str


class DeleteStateBody(BaseModel):
    tg_chat_id: int

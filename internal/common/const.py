from enum import Enum


class Role(Enum):
    EMPLOYEE = "employee"
    MODERATOR = "moderator"
    ADMIN = "admin"


TRACE_ID_KEY = "trace_id"
SPAN_ID_KEY = "span_id"
FILE_KEY = "file"
ERROR_KEY = "error"
TRACEBACK_KEY = "traceback"

ORGANIZATION_ID_KEY = "organization.id"
ACCOUNT_ID_KEY = "account.id"

HTTP_METHOD_KEY = "http.request.method"
HTTP_STATUS_KEY = "http.response.status_code"
HTTP_ROUTE_KEY = "http.route"
HTTP_REQUEST_DURATION_KEY = "http.server.request.duration"

TELEGRAM_MESSAGE_DURATION_KEY = "telegram.message.duration"
TELEGRAM_CHAT_ID_KEY = "telegram.chat.id"
TELEGRAM_EVENT_TYPE_KEY = "telegram.event.type"
TELEGRAM_USER_USERNAME_KEY = "telegram.user.username"

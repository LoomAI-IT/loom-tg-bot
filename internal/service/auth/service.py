from aiogram_dialog import DialogManager
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class AuthDialogService(interface.IAuthDialogService):
    """Класс для получения данных для диалога авторизации"""

    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            domain: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.domain = domain

    async def get_agreement_data(self, **kwargs) -> dict:
        with self.tracer.start_as_current_span(
                "AuthDialogGetter.get_agreement_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем ссылки на документы из конфига
                data = {
                    "user_agreement_link": f"https://{self.domain}/agreement",
                    "privacy_policy_link": f"https://{self.domain}/privacy",
                    "data_processing_link": f"https://{self.domain}/data-processing",
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_user_status(
            self,
            dialog_manager: DialogManager,
            user_state: model.UserState,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "AuthDialogGetter.get_user_status",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                user = dialog_manager.event.from_user
                chat_id = dialog_manager.event.chat.id

                data = {
                    "name": user.first_name or "Пользователь",
                    "username": user.username,
                    "chat_id": chat_id,
                    "is_authorized": bool(user_state and user_state.account_id),
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

from aiogram_dialog import DialogManager

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class AuthGetter(interface.IAuthGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            domain: str,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.domain = domain

    async def get_agreement_data(self, **kwargs) -> dict:
        with self.tracer.start_as_current_span(
                "AuthGetter.get_agreement_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало получения данных соглашений")

                # Получаем ссылки на документы из конфига
                data = {
                    "user_agreement_link": f"https://{self.domain}/agreement",
                    "privacy_policy_link": f"https://{self.domain}/privacy",
                    "data_processing_link": f"https://{self.domain}/data-processing",
                }

                self.logger.info("Завершение получения данных соглашений")
                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_user_status(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "AuthGetter.get_user_status",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало получения статуса пользователя")

                user = dialog_manager.event.from_user

                state = await self._get_state(dialog_manager)

                data = {
                    "name": user.first_name or "Пользователь",
                    "username": user.username,
                    "account_id": state.account_id,
                }

                self.logger.info("Завершение получения статуса пользователя")
                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            chat_id = None

        state = (await self.state_repo.state_by_id(chat_id))[0]
        return state
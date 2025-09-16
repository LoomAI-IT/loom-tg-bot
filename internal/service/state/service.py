from opentelemetry.trace import StatusCode, SpanKind

from internal import model, interface


class StateService(interface.IStateService):
    def __init__(self, tel: interface.ITelemetry, state_repo: interface.IStateRepo):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo

    async def create_state(self, tg_chat_id: int) -> int:
        with self.tracer.start_as_current_span(
                "StateService.create_state",
                kind=SpanKind.INTERNAL,
                attributes={
                    "tg_chat_id": tg_chat_id
                }
        ) as span:
            try:
                state_id = await self.state_repo.create_state(tg_chat_id)

                span.set_status(StatusCode.OK)
                return state_id
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def state_by_id(self, tg_chat_id: int) -> list[model.UserState]:
        with self.tracer.start_as_current_span(
                "StateService.state_by_id",
                kind=SpanKind.INTERNAL,
                attributes={
                    "tg_chat_id": tg_chat_id,
                }
        ) as span:
            try:
                state = await self.state_repo.state_by_id(tg_chat_id)

                span.set_status(StatusCode.OK)
                return state
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def change_user_state(
            self,
            state_id: int,
            account_id: int = None,
            organization_id: int = None,
            access_token: str = None,
            refresh_token: str = None,
    ) -> None:
        with self.tracer.start_as_current_span(
                "StateService.change_status",
                kind=SpanKind.INTERNAL,
                attributes={
                    "state_id": state_id
                }
        ) as span:
            try:
                await self.state_repo.change_user_state(
                    state_id,
                    account_id,
                    organization_id,
                    access_token,
                    refresh_token,
                )
                span.set_status(StatusCode.OK)
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def delete_state_by_tg_chat_id(self, tg_chat_id: int) -> None:
        with self.tracer.start_as_current_span(
                "StateService.delete_state_by_tg_chat_id",
                kind=SpanKind.INTERNAL,
                attributes={
                    "tg_chat_id": tg_chat_id
                }
        ) as span:
            try:
                await self.state_repo.delete_state_by_tg_chat_id(tg_chat_id)

                span.set_status(StatusCode.OK)
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

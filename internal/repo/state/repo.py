from opentelemetry.trace import SpanKind, Status, StatusCode

from .query import *
from internal import model
from internal import interface


class StateRepo(interface.IStateRepo):
    def __init__(self, tel: interface.ITelemetry, db: interface.IDB):
        self.db = db
        self.tracer = tel.tracer()

    async def create_state(self, tg_chat_id: int) -> int:
        with self.tracer.start_as_current_span(
                "StateRepo.create_state",
                kind=SpanKind.INTERNAL,
                attributes={
                    "tg_chat_id": tg_chat_id,
                }
        ) as span:
            try:
                args = {
                    'tg_chat_id': tg_chat_id,
                }
                state_id = await self.db.insert(create_state, args)

                span.set_status(StatusCode.OK)
                return state_id
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise err

    async def state_by_id(self, tg_chat_id) -> list[model.UserState]:
        with self.tracer.start_as_current_span(
                "StateRepo.state_by_id",
                kind=SpanKind.INTERNAL,
                attributes={
                    "tg_chat_id": tg_chat_id,
                }
        ) as span:
            try:
                args = {'tg_chat_id': tg_chat_id}
                rows = await self.db.select(state_by_id, args)
                if rows:
                    rows = model.UserState.serialize(rows)

                span.set_status(StatusCode.OK)
                return rows
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def change_user_state(
            self,
            state_id: int,
            account_id: int = None,
            access_token: str = None,
            refresh_token: str = None,
    ) -> None:
        with self.tracer.start_as_current_span(
                "StateRepo.change_status",
                kind=SpanKind.INTERNAL,
                attributes={
                    "state_id": state_id,
                }
        ) as span:
            try:
                # Формируем запрос динамически в зависимости от переданных параметров
                update_fields = []
                args: dict = {'state_id': state_id}

                if account_id is not None:
                    update_fields.append("account_id = :account_id")
                    args['account_id'] = account_id

                if access_token is not None:
                    update_fields.append("access_token = :access_token")
                    args['access_token'] = access_token

                if refresh_token is not None:
                    update_fields.append("refresh_token = :refresh_token")
                    args['refresh_token'] = refresh_token

                if not update_fields:
                    # Если нет полей для обновления, просто возвращаемся
                    span.set_status(Status(StatusCode.OK))
                    return

                # Формируем финальный запрос
                query = f"""
                UPDATE user_states 
                SET {', '.join(update_fields)}
                WHERE id = :state_id;
                """
                span.set_status(StatusCode.OK)
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def delete_state_by_tg_chat_id(self, tg_chat_id: int) -> None:
        with self.tracer.start_as_current_span(
                "StateRepo.delete_state_by_tg_chat_id",
                kind=SpanKind.INTERNAL,
                attributes={
                    "tg_chat_id": tg_chat_id,
                }
        ) as span:
            try:
                args = {
                    'tg_chat_id': tg_chat_id
                }
                await self.db.delete(delete_state_by_tg_chat_id, args)

                span.set_status(StatusCode.OK)
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

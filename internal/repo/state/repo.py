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

    async def state_by_id(self, tg_chat_id) -> list[model.State]:
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
                    rows = model.State.serialize(rows)

                span.set_status(StatusCode.OK)
                return rows
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def change_status(self, state_id: int, status: str) -> None:
        with self.tracer.start_as_current_span(
                "StateRepo.change_status",
                kind=SpanKind.INTERNAL,
                attributes={
                    "state_id": state_id,
                    "status": status
                }
        ) as span:
            try:
                args = {
                    'state_id': state_id,
                    'status': status,
                }
                await self.db.update(update_state_status, args)
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

from opentelemetry.trace import SpanKind, Status, StatusCode

from .query import *
from internal import model
from internal import interface


class StateRepo(interface.IStateRepo):
    def __init__(self, tel: interface.ITelemetry, db: interface.IDB):
        self.db = db
        self.tracer = tel.tracer()

    async def create_state(self, tg_chat_id: int, tg_username: str) -> int:
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
                    'tg_username': tg_username,
                }
                state_id = await self.db.insert(create_state, args)

                span.set_status(StatusCode.OK)
                return state_id
            except Exception as err:
                
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
                
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def state_by_account_id(self, account_id) -> list[model.UserState]:
        with self.tracer.start_as_current_span(
                "StateRepo.state_by_account_id",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id,
                }
        ) as span:
            try:
                args = {'account_id': account_id}
                rows = await self.db.select(state_by_account_id, args)
                if rows:
                    rows = model.UserState.serialize(rows)

                span.set_status(StatusCode.OK)
                return rows
            except Exception as err:
                
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def set_cache_file(self, filename: str, file_id: str):
        with self.tracer.start_as_current_span(
                "StateRepo.set_cache_file",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                args = {'filename': filename, "file_id": file_id}
                _ = await self.db.insert(set_cache_file, args)

                span.set_status(StatusCode.OK)
            except Exception as err:
                
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def get_cache_file(self, filename: str) -> list[model.CachedFile]:
        with self.tracer.start_as_current_span(
                "StateRepo.set_cache_file",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                args = {'filename': filename}
                rows = await self.db.select(get_cache_file, args)
                if rows:
                    rows = model.CachedFile.serialize(rows)
                span.set_status(StatusCode.OK)
                return rows
            except Exception as err:
                
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def change_user_state(
            self,
            state_id: int,
            account_id: int = None,
            organization_id: int = None,
            access_token: str = None,
            refresh_token: str = None,
            can_show_alerts: bool = None,
            show_error_recovery: bool = None,
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

                if organization_id is not None:
                    update_fields.append("organization_id = :organization_id")
                    args['organization_id'] = organization_id

                if access_token is not None:
                    update_fields.append("access_token = :access_token")
                    args['access_token'] = access_token

                if refresh_token is not None:
                    update_fields.append("refresh_token = :refresh_token")
                    args['refresh_token'] = refresh_token

                if can_show_alerts is not None:
                    update_fields.append("can_show_alerts = :can_show_alerts")
                    args['can_show_alerts'] = can_show_alerts

                if show_error_recovery is not None:
                    update_fields.append("show_error_recovery = :show_error_recovery")
                    args['show_error_recovery'] = show_error_recovery

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

                await self.db.update(query, args)
                span.set_status(StatusCode.OK)
            except Exception as err:
                
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
                
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def create_vizard_video_cut_alert(self, state_id: int, youtube_video_reference: str, video_count: int) -> int:
        with self.tracer.start_as_current_span(
                "StateRepo.create_vizard_video_cut_alert",
                kind=SpanKind.INTERNAL,
                attributes={
                    "state_id": state_id,
                    "youtube_video_reference": youtube_video_reference,
                    "video_count": video_count,
                }
        ) as span:
            try:
                args = {
                    'state_id': state_id,
                    'youtube_video_reference': youtube_video_reference,
                    'video_count': video_count,
                }
                alert_id = await self.db.insert(create_vizard_video_cut_alert, args)

                span.set_status(StatusCode.OK)
                return alert_id
            except Exception as err:
                
                span.set_status(StatusCode.ERROR, str(err))
                raise err

    async def get_vizard_video_cut_alert_by_state_id(self, state_id: int) -> list[model.VizardVideoCutAlert]:
        with self.tracer.start_as_current_span(
                "StateRepo.get_vizard_video_cut_alert_by_state_id",
                kind=SpanKind.INTERNAL,
                attributes={
                    "state_id": state_id,
                }
        ) as span:
            try:
                args = {'state_id': state_id}
                rows = await self.db.select(get_vizard_video_cut_alert_by_state_id, args)
                if rows:
                    rows = model.VizardVideoCutAlert.serialize(rows)

                span.set_status(StatusCode.OK)
                return rows
            except Exception as err:
                
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def delete_vizard_video_cut_alert(self, state_id: int) -> None:
        with self.tracer.start_as_current_span(
                "StateRepo.delete_vizard_video_cut_alert",
                kind=SpanKind.INTERNAL,
                attributes={
                    "state_id": state_id,
                }
        ) as span:
            try:
                args = {
                    'state_id': state_id
                }
                await self.db.delete(delete_vizard_video_cut_alert, args)

                span.set_status(StatusCode.OK)
            except Exception as err:
                
                span.set_status(StatusCode.ERROR, str(err))
                raise
from opentelemetry.trace import SpanKind, Status, StatusCode

from pkg.trace_wrapper import traced_method
from .query import *
from internal import model
from internal import interface


class StateRepo(interface.IStateRepo):
    def __init__(self, tel: interface.ITelemetry, db: interface.IDB):
        self.db = db
        self.tracer = tel.tracer()

    @traced_method()
    async def create_state(self, tg_chat_id: int, tg_username: str) -> int:
        args = {
            'tg_chat_id': tg_chat_id,
            'tg_username': tg_username,
        }
        state_id = await self.db.insert(create_state, args)
        return state_id

    @traced_method()
    async def state_by_id(self, tg_chat_id) -> list[model.UserState]:
        args = {'tg_chat_id': tg_chat_id}
        rows = await self.db.select(state_by_id, args)
        if rows:
            rows = model.UserState.serialize(rows)
        return rows

    @traced_method()
    async def state_by_account_id(self, account_id) -> list[model.UserState]:
        args = {'account_id': account_id}
        rows = await self.db.select(state_by_account_id, args)
        if rows:
            rows = model.UserState.serialize(rows)

        return rows

    @traced_method()
    async def set_cache_file(self, filename: str, file_id: str):
        args = {'filename': filename, "file_id": file_id}
        _ = await self.db.insert(set_cache_file, args)

    @traced_method()
    async def get_cache_file(self, filename: str) -> list[model.CachedFile]:
        args = {'filename': filename}
        rows = await self.db.select(get_cache_file, args)
        if rows:
            rows = model.CachedFile.serialize(rows)
        return rows

    @traced_method()
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
            return

        query = f"""
                UPDATE user_states 
                SET {', '.join(update_fields)}
                WHERE id = :state_id;
                """

        await self.db.update(query, args)

    @traced_method()
    async def delete_state_by_tg_chat_id(self, tg_chat_id: int) -> None:
        args = {
            'tg_chat_id': tg_chat_id
        }
        await self.db.delete(delete_state_by_tg_chat_id, args)

    @traced_method()
    async def create_vizard_video_cut_alert(self, state_id: int, youtube_video_reference: str, video_count: int) -> int:
        args = {
            'state_id': state_id,
            'youtube_video_reference': youtube_video_reference,
            'video_count': video_count,
        }
        alert_id = await self.db.insert(create_vizard_video_cut_alert, args)

        return alert_id

    @traced_method()
    async def get_vizard_video_cut_alert_by_state_id(self, state_id: int) -> list[model.VizardVideoCutAlert]:
        args = {'state_id': state_id}
        rows = await self.db.select(get_vizard_video_cut_alert_by_state_id, args)
        if rows:
            rows = model.VizardVideoCutAlert.serialize(rows)

        return rows

    @traced_method()
    async def delete_vizard_video_cut_alert(self, state_id: int) -> None:
        args = {
            'state_id': state_id
        }
        await self.db.delete(delete_vizard_video_cut_alert, args)

    @traced_method()
    async def create_publication_approved_alert(self, state_id: int, publication_id: int) -> int:
        args = {
            'state_id': state_id,
            'publication_id': publication_id,
        }
        alert_id = await self.db.insert(create_publication_approved_alert, args)

        return alert_id

    @traced_method()
    async def get_publication_approved_alert_by_state_id(self, state_id: int) -> list[model.PublicationApprovedAlert]:
        args = {'state_id': state_id}
        rows = await self.db.select(get_publication_approved_alert_by_state_id, args)
        if rows:
            rows = model.PublicationApprovedAlert.serialize(rows)

        return rows

    @traced_method()
    async def delete_publication_approved_alert(self, state_id: int) -> None:
        args = {
            'state_id': state_id
        }
        await self.db.delete(delete_publication_approved_alert, args)

    @traced_method()
    async def create_publication_rejected_alert(self, state_id: int, publication_id: int) -> int:
        args = {
            'state_id': state_id,
            'publication_id': publication_id,
        }
        alert_id = await self.db.insert(create_publication_rejected_alert, args)

        return alert_id

    @traced_method()
    async def get_publication_rejected_alert_by_state_id(self, state_id: int) -> list[model.PublicationRejectedAlert]:
        args = {'state_id': state_id}
        rows = await self.db.select(get_publication_rejected_alert_by_state_id, args)
        if rows:
            rows = model.PublicationRejectedAlert.serialize(rows)

        return rows

    @traced_method()
    async def delete_publication_rejected_alert(self, state_id: int) -> None:
        args = {
            'state_id': state_id
        }
        await self.db.delete(delete_publication_rejected_alert, args)

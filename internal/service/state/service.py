from internal import model, interface
from pkg.trace_wrapper import traced_method


class StateService(interface.IStateService):
    def __init__(self, tel: interface.ITelemetry, state_repo: interface.IStateRepo):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo

    @traced_method()
    async def create_state(self, tg_chat_id: int, tg_username: str) -> int:
        state_id = await self.state_repo.create_state(tg_chat_id, tg_username)
        return state_id

    @traced_method()
    async def state_by_id(self, tg_chat_id: int) -> list[model.UserState]:
        state = await self.state_repo.state_by_id(tg_chat_id)
        return state

    @traced_method()
    async def state_by_account_id(self, account_id: int) -> list[model.UserState]:
        state = await self.state_repo.state_by_account_id(account_id)
        return state

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
        await self.state_repo.change_user_state(
            state_id,
            account_id,
            organization_id,
            access_token,
            refresh_token,
            can_show_alerts,
            show_error_recovery
        )

    @traced_method()
    async def delete_state_by_tg_chat_id(self, tg_chat_id: int) -> None:
        await self.state_repo.delete_state_by_tg_chat_id(tg_chat_id)

    @traced_method()
    async def set_cache_file(self, filename: str, file_id: str) -> None:
        await self.state_repo.set_cache_file(filename, file_id)

    @traced_method()
    async def create_vizard_video_cut_alert(self, state_id: int, youtube_video_reference: str, video_count: int) -> int:
        alert_id = await self.state_repo.create_vizard_video_cut_alert(
            state_id,
            youtube_video_reference,
            video_count
        )
        return alert_id

    @traced_method()
    async def create_publication_approved_alert(self, state_id: int, publication_id: int) -> int:
        alert_id = await self.state_repo.create_publication_approved_alert(
            state_id,
            publication_id
        )
        return alert_id
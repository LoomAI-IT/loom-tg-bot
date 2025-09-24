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

    async def state_by_account_id(self, account_id: int) -> list[model.UserState]:
        with self.tracer.start_as_current_span(
                "StateService.state_by_account_id",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id,
                }
        ) as span:
            try:
                state = await self.state_repo.state_by_account_id(account_id)

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
            can_show_alerts: bool = None,
            show_error_recovery: bool = None,
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
                    can_show_alerts,
                    show_error_recovery
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

    async def set_cache_file(self, filename: str, file_id: str) -> None:
        with self.tracer.start_as_current_span(
                "StateService.set_cache_file",
                kind=SpanKind.INTERNAL,
                attributes={
                    "filename": filename,
                    "file_id": file_id
                }
        ) as span:
            try:
                await self.state_repo.set_cache_file(filename, file_id)
                span.set_status(StatusCode.OK)
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise


    async def create_vizard_video_cut_alert(self, state_id: int, youtube_video_reference: str, video_count: int) -> int:
        with self.tracer.start_as_current_span(
                "StateService.create_vizard_video_cut_alert",
                kind=SpanKind.INTERNAL,
                attributes={
                    "youtube_video_reference": youtube_video_reference,
                    "video_count": video_count
                }
        ) as span:
            try:
                alert_id = await self.state_repo.create_vizard_video_cut_alert(
                    state_id,
                    youtube_video_reference,
                    video_count
                )

                span.set_status(StatusCode.OK)
                return alert_id
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def get_vizard_video_cut_alert_by_state_id(self, state_id: int) -> list[model.VizardVideoCutAlert]:
        with self.tracer.start_as_current_span(
                "StateService.get_vizard_video_cut_alert_by_state_id",
                kind=SpanKind.INTERNAL,
                attributes={
                    "state_id": state_id,
                }
        ) as span:
            try:
                alert = await self.state_repo.get_vizard_video_cut_alert_by_state_id(state_id)

                span.set_status(StatusCode.OK)
                return alert
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise


    async def delete_vizard_video_cut_alert(self, state_id: int) -> None:
        with self.tracer.start_as_current_span(
                "StateService.delete_vizard_video_cut_alert",
                kind=SpanKind.INTERNAL,
                attributes={
                    "state_id": state_id
                }
        ) as span:
            try:
                await self.state_repo.delete_vizard_video_cut_alert(state_id)

                span.set_status(StatusCode.OK)
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

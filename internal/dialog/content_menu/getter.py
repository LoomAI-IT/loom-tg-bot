from aiogram_dialog import DialogManager

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ContentMenuGetter(interface.IContentMenuGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_employee_client: interface.ILoomEmployeeClient,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_employee_client = loom_employee_client
        self.loom_content_client = loom_content_client

    async def get_content_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ContentMenuGetter.get_content_menu_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало получения данных меню контента")

                state = await self._get_state(dialog_manager)

                publications = await self.loom_content_client.get_publications_by_organization(
                    state.organization_id
                )

                video_cuts = await self.loom_content_client.get_video_cuts_by_organization(
                    state.organization_id
                )

                drafts_count = 0
                moderation_count = 0
                approved_count = 0
                total_generations = 0

                video_cut_count = 0
                publication_count = 0

                for pub in publications:
                    total_generations += 1
                    publication_count += 1

                    if pub.moderation_status == "draft":
                        self.logger.info("Обнаружена публикация со статусом черновик")
                        drafts_count += 1
                    elif pub.moderation_status == "moderation":
                        self.logger.info("Обнаружена публикация со статусом модерация")
                        moderation_count += 1
                    elif pub.moderation_status == "approved":
                        self.logger.info("Обнаружена публикация со статусом одобрено")
                        approved_count += 1

                for video in video_cuts:
                    total_generations += 1
                    video_cut_count += 1

                    if video.moderation_status == "draft":
                        self.logger.info("Обнаружена видео-нарезка со статусом черновик")
                        drafts_count += 1
                    elif video.moderation_status == "moderation":
                        self.logger.info("Обнаружена видео-нарезка со статусом модерация")
                        moderation_count += 1
                    elif video.moderation_status == "approved":
                        self.logger.info("Обнаружена видео-нарезка со статусом одобрено")
                        approved_count += 1

                data = {
                    "drafts_count": drafts_count,
                    "moderation_count": moderation_count,
                    "approved_count": approved_count,
                    "total_generations": total_generations,
                    "video_cut_count": video_cut_count,
                    "publication_count": publication_count,
                }

                self.logger.info("Завершение получения данных меню контента")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_drafts_type_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ContentMenuGetter.get_drafts_type_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало получения данных типов черновиков")

                state = await self._get_state(dialog_manager)

                publications = await self.loom_content_client.get_publications_by_organization(
                    state.organization_id
                )

                video_cuts = await self.loom_content_client.get_video_cuts_by_organization(
                    state.organization_id
                )

                publication_drafts_count = sum(1 for pub in publications if pub.moderation_status == "draft"
                                               and pub.creator_id == state.account_id)
                video_drafts_count = sum(1 for video in video_cuts if video.moderation_status == "draft"
                                         and video.creator_id == state.account_id)

                data = {
                    "publication_drafts_count": publication_drafts_count,
                    "video_drafts_count": video_drafts_count,
                }

                self.logger.info("Завершение получения данных типов черновиков")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_moderation_type_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ContentMenuGetter.get_moderation_type_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало получения данных типов модерации")

                state = await self._get_state(dialog_manager)

                publications = await self.loom_content_client.get_publications_by_organization(
                    state.organization_id
                )

                video_cuts = await self.loom_content_client.get_video_cuts_by_organization(
                    state.organization_id
                )

                publication_moderation_count = sum(1 for pub in publications if pub.moderation_status == "moderation")
                video_moderation_count = sum(1 for video in video_cuts if video.moderation_status == "moderation")

                data = {
                    "publication_moderation_count": publication_moderation_count,
                    "video_moderation_count": video_moderation_count,
                }

                self.logger.info("Завершение получения данных типов модерации")

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
            raise ValueError("Cannot extract chat_id from dialog_manager")

        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]

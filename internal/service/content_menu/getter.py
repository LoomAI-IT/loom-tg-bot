from aiogram_dialog import DialogManager

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ContentMenuGetter(interface.IContentMenuGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_content_client: interface.IKonturContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client
        self.kontur_content_client = kontur_content_client

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
                state = await self._get_state(dialog_manager)

                # Получаем данные сотрудника
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                # Получаем статистику публикаций
                publications = await self.kontur_content_client.get_publications_by_organization(
                    employee.organization_id
                )

                # Получаем статистику видео-нарезок
                video_cuts = await self.kontur_content_client.get_video_cuts_by_organization(
                    employee.organization_id
                )

                # Подсчитываем статистику
                drafts_count = 0
                moderation_count = 0
                approved_count = 0
                published_count = 0
                total_generations = 0

                video_cut_count = 0
                publication_count = 0

                # Статистика публикаций
                for pub in publications:
                    total_generations += 1
                    publication_count += 1

                    if pub.moderation_status == "draft":
                        drafts_count += 1
                    elif pub.moderation_status == "moderation":
                        moderation_count += 1
                    elif pub.moderation_status == "approved":
                        approved_count += 1
                    elif pub.moderation_status == "published":
                        published_count += 1

                # Статистика видео-нарезок
                for video in video_cuts:
                    total_generations += 1
                    video_cut_count += 1

                    if video.moderation_status == "draft":
                        drafts_count += 1
                    elif video.moderation_status == "moderation":
                        moderation_count += 1
                    elif video.moderation_status == "approved":
                        approved_count += 1
                    elif video.moderation_status == "published":
                        published_count += 1

                data = {
                    "drafts_count": drafts_count,
                    "moderation_count": moderation_count,
                    "approved_count": approved_count,
                    "published_count": published_count,
                    "total_generations": total_generations,
                    "video_cut_count": video_cut_count,
                    "publication_count": publication_count,
                }

                self.logger.info("Данные меню контента успешно загружены")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                self.logger.error("Ошибка при загрузке данных меню контента")
                raise err

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
                state = await self._get_state(dialog_manager)

                # Получаем данные сотрудника
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                # Получаем публикации организации
                publications = await self.kontur_content_client.get_publications_by_organization(
                    employee.organization_id
                )

                # Получаем видео-нарезки организации
                video_cuts = await self.kontur_content_client.get_video_cuts_by_organization(
                    employee.organization_id
                )

                # Подсчитываем черновики
                publication_drafts_count = sum(1 for pub in publications if pub.moderation_status == "draft")
                video_drafts_count = sum(1 for video in video_cuts if video.moderation_status == "draft")

                data = {
                    "publication_drafts_count": publication_drafts_count,
                    "video_drafts_count": video_drafts_count,
                }

                self.logger.info("Данные типов черновиков успешно загружены")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
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
                state = await self._get_state(dialog_manager)

                # Получаем данные сотрудника
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                # Получаем публикации организации
                publications = await self.kontur_content_client.get_publications_by_organization(
                    employee.organization_id
                )

                # Получаем видео-нарезки организации
                video_cuts = await self.kontur_content_client.get_video_cuts_by_organization(
                    employee.organization_id
                )

                # Подсчитываем элементы на модерации
                publication_moderation_count = sum(1 for pub in publications if pub.moderation_status == "pending")
                video_moderation_count = sum(1 for video in video_cuts if video.moderation_status == "pending")

                data = {
                    "publication_moderation_count": publication_moderation_count,
                    "video_moderation_count": video_moderation_count,
                }

                self.logger.info("Данные типов модерации успешно загружены")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
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

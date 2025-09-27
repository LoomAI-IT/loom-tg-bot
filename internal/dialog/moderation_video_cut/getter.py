from datetime import datetime, timezone

from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram.types import ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class VideoCutModerationGetter(interface.IVideoCutModerationGetter):
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

    async def get_moderation_list_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "VideoCutModerationGetter.get_moderation_list_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Получаем видео-нарезки на модерации для организации
                video_cuts = await self.loom_content_client.get_video_cuts_by_organization(
                    organization_id=state.organization_id
                )

                # Фильтруем только те, что на модерации
                moderation_video_cuts = [
                    video_cut.to_dict() for video_cut in video_cuts
                    if video_cut.moderation_status == "moderation"
                ]

                if not moderation_video_cuts:
                    return {
                        "has_video_cuts": False,
                        "video_cuts_count": 0,
                        "period_text": "",
                    }

                # Сохраняем список для навигации
                dialog_manager.dialog_data["moderation_list"] = moderation_video_cuts

                # Устанавливаем текущий индекс (0 если не был установлен)
                if "current_index" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["current_index"] = 0

                current_index = dialog_manager.dialog_data["current_index"]
                current_video_cut = model.VideoCut(**moderation_video_cuts[current_index])

                # Получаем информацию об авторе
                creator = await self.loom_employee_client.get_employee_by_account_id(
                    current_video_cut.creator_id
                )

                # Форматируем теги
                tags = current_video_cut.tags or []
                tags_text = ", ".join(tags) if tags else ""

                # Рассчитываем время ожидания
                waiting_time = self._calculate_waiting_time_text(current_video_cut.created_at)

                # Подготавливаем медиа для видео
                video_media = await self._get_video_media(current_video_cut)

                # Определяем период
                period_text = self._get_period_text(moderation_video_cuts)

                data = {
                    "has_video_cuts": True,
                    "video_cuts_count": len(moderation_video_cuts),
                    "period_text": period_text,
                    "creator_name": creator.name,
                    "created_at": self._format_datetime(current_video_cut.created_at),
                    "has_waiting_time": bool(waiting_time),
                    "waiting_time": waiting_time,
                    "youtube_reference": current_video_cut.youtube_video_reference or "Не указан",
                    "video_name": current_video_cut.name or "Без названия",
                    "video_description": current_video_cut.description or "Описание отсутствует",
                    "has_tags": bool(tags),
                    "video_tags": tags_text,
                    "has_video": bool(current_video_cut.video_fid),
                    "video_media": video_media,
                    "current_index": current_index + 1,
                    "total_count": len(moderation_video_cuts),
                    "has_prev": current_index > 0,
                    "has_next": current_index < len(moderation_video_cuts) - 1,
                }

                # Сохраняем данные текущего видео для редактирования
                dialog_manager.dialog_data["original_video_cut"] = {
                    "id": current_video_cut.id,
                    "creator_id": current_video_cut.creator_id,
                    "organization_id": current_video_cut.organization_id,
                    "project_id": current_video_cut.project_id,
                    "moderator_id": current_video_cut.moderator_id,
                    "transcript": current_video_cut.transcript,
                    "video_name": current_video_cut.video_name,
                    "original_url": current_video_cut.original_url,
                    "vizard_rub_cost": current_video_cut.vizard_rub_cost,
                    "moderation_comment": current_video_cut.moderation_comment,
                    "publication_at": current_video_cut.publication_at,
                    "name": current_video_cut.name,
                    "description": current_video_cut.description,
                    "tags": current_video_cut.tags or [],
                    "youtube_video_reference": current_video_cut.youtube_video_reference,
                    "video_fid": current_video_cut.video_fid,
                    "moderation_status": current_video_cut.moderation_status,
                    "created_at": current_video_cut.created_at,
                    "youtube_source": current_video_cut.youtube_source,
                    "inst_source": current_video_cut.inst_source,
                }

                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

                if not selected_networks:
                    social_networks = await self.loom_content_client.get_social_networks_by_organization(
                        organization_id=state.organization_id
                    )

                    youtube_connected = self._is_network_connected(social_networks, "youtube")
                    instagram_connected = self._is_network_connected(social_networks, "instagram")

                    if youtube_connected:
                        widget_id = "youtube_checkbox"
                        autoselect = social_networks["youtube"][0].get("autoselect", False)
                        selected_networks[widget_id] = autoselect

                    if instagram_connected:
                        widget_id = "instagram_checkbox"
                        autoselect = social_networks["instagram"][0].get("autoselect", False)
                        selected_networks[widget_id] = autoselect

                    dialog_manager.dialog_data["selected_social_networks"] = selected_networks

                # Копируем в рабочую версию, если ее еще нет
                if "working_video_cut" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["working_video_cut"] = dict(
                        dialog_manager.dialog_data["original_video_cut"])

                self.logger.info("Список модерации видео загружен")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_reject_comment_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "VideoCutModerationGetter.get_reject_comment_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                original_video_cut = dialog_manager.dialog_data.get("original_video_cut", {})

                # Получаем информацию об авторе
                creator = await self.loom_employee_client.get_employee_by_account_id(
                    original_video_cut["creator_id"],
                )

                data = {
                    "video_name": original_video_cut["name"] or "Без названия",
                    "creator_name": creator.name,
                    "has_comment": bool(dialog_manager.dialog_data.get("reject_comment")),
                    "reject_comment": dialog_manager.dialog_data.get("reject_comment", ""),
                    "has_void_reject_comment": dialog_manager.dialog_data.get("has_void_reject_comment", False),
                    "has_small_reject_comment": dialog_manager.dialog_data.get("has_small_reject_comment", False),
                    "has_big_reject_comment": dialog_manager.dialog_data.get("has_big_reject_comment", False),
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_edit_preview_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "VideoCutModerationGetter.get_edit_preview_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Инициализируем рабочую версию если ее нет
                if "working_video_cut" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["working_video_cut"] = dict(
                        dialog_manager.dialog_data["original_video_cut"]
                    )

                working_video_cut = dialog_manager.dialog_data["working_video_cut"]
                original_video_cut = dialog_manager.dialog_data["original_video_cut"]

                # Получаем информацию об авторе
                creator = await self.loom_employee_client.get_employee_by_account_id(
                    working_video_cut["creator_id"]
                )

                # Форматируем теги
                tags = working_video_cut.get("tags", [])
                tags_text = ", ".join(tags) if tags else ""

                # Подготавливаем медиа для видео
                video_media = await self._get_video_media(model.VideoCut(**working_video_cut))

                data = {
                    "video_name": working_video_cut["name"] or "Без названия",
                    "video_description": working_video_cut["description"] or "Описание отсутствует",
                    "video_tags": tags_text,
                    "youtube_reference": working_video_cut["youtube_video_reference"],
                    "has_tags": bool(tags),
                    "creator_name": creator.name,
                    "created_at": self._format_datetime(original_video_cut["created_at"]),
                    "video_media": video_media,
                    "has_changes": self._has_changes(dialog_manager),
                    "has_video": bool(working_video_cut.get("video_fid")),
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "VideoCutModerationGetter.get_social_network_select_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                # Получаем подключенные социальные сети для организации
                social_networks = await self.loom_content_client.get_social_networks_by_organization(
                    organization_id=state.organization_id
                )

                # Проверяем подключенные сети
                youtube_connected = self._is_network_connected(social_networks, "youtube")
                instagram_connected = self._is_network_connected(social_networks, "instagram")

                # Получаем текущие выбранные сети
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

                if youtube_connected:
                    widget_id = "youtube_checkbox"
                    youtube_checkbox: ManagedCheckbox = dialog_manager.find(widget_id)
                    await youtube_checkbox.set_checked(selected_networks[widget_id])

                if instagram_connected:
                    widget_id = "instagram_checkbox"
                    instagram_checkbox: ManagedCheckbox = dialog_manager.find(widget_id)
                    await instagram_checkbox.set_checked(selected_networks[widget_id])

                dialog_manager.dialog_data["selected_social_networks"] = selected_networks

                data = {
                    "youtube_connected": youtube_connected,
                    "instagram_connected": instagram_connected,
                    "no_connected_networks": not youtube_connected and not instagram_connected,
                    "has_available_networks": youtube_connected or instagram_connected,
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_edit_title_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_video_cut = dialog_manager.dialog_data.get("working_video_cut", {})
        return {
            "current_title": working_video_cut.get("name", ""),
            "has_void_title": dialog_manager.dialog_data.get("has_void_title", False),
            "has_small_title": dialog_manager.dialog_data.get("has_small_title", False),
            "has_big_title": dialog_manager.dialog_data.get("has_big_title", False),
        }

    async def get_edit_description_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_video_cut = dialog_manager.dialog_data.get("working_video_cut", {})
        description = working_video_cut.get("description", "")
        return {
            "current_description_length": len(description),
            "has_void_description": dialog_manager.dialog_data.get("has_void_description", False),
            "has_small_description": dialog_manager.dialog_data.get("has_small_description", False),
            "has_big_description": dialog_manager.dialog_data.get("has_big_description", False),
        }

    async def get_edit_tags_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        working_video_cut = dialog_manager.dialog_data.get("working_video_cut", {})
        tags = working_video_cut.get("tags", [])
        return {
            "has_tags": bool(tags),
            "current_tags": ", ".join(tags) if tags else "",
            "has_void_tags": dialog_manager.dialog_data.get("has_void_tags", False),
        }

    # Вспомогательные методы
    def _has_changes(self, dialog_manager: DialogManager) -> bool:
        original = dialog_manager.dialog_data.get("original_video_cut", {})
        working = dialog_manager.dialog_data.get("working_video_cut", {})

        if not original or not working:
            return False

        # Сравниваем основные поля
        fields_to_compare = ["name", "description", "tags"]
        for field in fields_to_compare:
            if original.get(field) != working.get(field):
                return True

        return False

    def _is_network_connected(self, social_networks: dict, network_type: str) -> bool:
        if not social_networks:
            return False
        return network_type in social_networks and len(social_networks[network_type]) > 0

    async def _save_video_cut_changes(self, dialog_manager: DialogManager) -> None:
        working_video_cut = dialog_manager.dialog_data["working_video_cut"]
        video_cut_id = working_video_cut["id"]

        await self.loom_content_client.change_video_cut(
            video_cut_id=video_cut_id,
            name=working_video_cut["name"],
            description=working_video_cut["description"],
            tags=working_video_cut.get("tags", []),
        )

        self.logger.info(
            "Изменения видео-нарезки в модерации сохранены",
            {
                "video_cut_id": video_cut_id,
                "has_changes": self._has_changes(dialog_manager),
            }
        )

    def _format_datetime(self, dt: str) -> str:
        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            # Форматируем в читаемый вид
            return dt.strftime("%d.%m.%Y %H:%M")
        except:
            return str(dt)

    def _calculate_waiting_hours(self, created_at: str) -> int:
        try:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

            now = datetime.now(timezone.utc)
            delta = now - created_at
            return int(delta.total_seconds() / 3600)
        except:
            return 0

    def _calculate_waiting_time_text(self, created_at: str) -> str:
        hours = self._calculate_waiting_hours(created_at)

        if hours == 0:
            return "менее часа"
        elif hours == 1:
            return "1 час"
        elif hours < 24:
            return f"{hours} часов"
        else:
            days = hours // 24
            if days == 1:
                return "1 день"
            else:
                return f"{days} дней"

    def _get_period_text(self, video_cuts: list) -> str:
        if not video_cuts:
            return "Нет данных"

        # Находим самое старое и новое видео
        dates = []
        for video_cut in video_cuts:
            if hasattr(video_cut, 'created_at') and video_cut.created_at:
                dates.append(video_cut.created_at)

        if not dates:
            return "Сегодня"

        # Простое определение периода на основе самого старого видео
        oldest_date = min(dates)
        waiting_hours = self._calculate_waiting_hours(oldest_date)

        if waiting_hours < 24:
            return "За сегодня"
        elif waiting_hours < 48:
            return "За последние 2 дня"
        elif waiting_hours < 168:  # неделя
            return "За неделю"
        else:
            return "За месяц"

    async def _get_video_media(self, video_cut: model.VideoCut) -> MediaAttachment | None:
        video_media = None
        if video_cut.video_fid:
            cached_file = await self.state_repo.get_cache_file(video_cut.video_name)
            if cached_file:
                video_media = MediaAttachment(
                    file_id=MediaId(cached_file[0].file_id),
                    type=ContentType.VIDEO,
                )
        return video_media

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

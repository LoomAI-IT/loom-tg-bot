from datetime import datetime, timezone

from aiogram import Bot
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram.types import ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class VideoCutsDraftGetter(interface.IVideoCutsDraftGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_employee_client: interface.ILoomEmployeeClient,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_employee_client = loom_employee_client
        self.loom_organization_client = loom_organization_client
        self.loom_content_client = loom_content_client

    async def get_video_cut_list_data(
            self,
            dialog_manager: DialogManager,
            bot: Bot,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftGetter.get_video_cut_list_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                employee = await self.loom_employee_client.get_employee_by_account_id(state.account_id)

                video_cuts = await self.loom_content_client.get_video_cuts_by_organization(state.organization_id)
                video_cuts = [
                    video_cut for video_cut in video_cuts if
                    video_cut.video_fid != ""
                    and video_cut.moderation_status == "draft"
                    and video_cut.creator_id == state.account_id
                ]

                if not video_cuts:
                    return {
                        "has_video_cuts": False,
                        "video_cuts_count": 0,
                        "period_text": "",
                    }

                dialog_manager.dialog_data["video_cuts_list"] = [video_cut.to_dict() for video_cut in video_cuts]

                if "current_index" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["current_index"] = 0

                current_index = dialog_manager.dialog_data["current_index"]
                current_video_cut = model.VideoCut(**dialog_manager.dialog_data["video_cuts_list"][current_index])

                # Форматируем теги
                tags = current_video_cut.tags or []
                tags_text = ", ".join(tags) if tags else ""

                # Определяем период
                period_text = self._get_period_text(video_cuts)

                # Подготавливаем медиа для видео
                video_media = await self._get_video_media(current_video_cut)

                # Сохраняем данные текущего черновика для редактирования
                dialog_manager.dialog_data["original_video_cut"] = current_video_cut.to_dict()

                # Копируем в рабочую версию, если ее еще нет
                if "working_video_cut" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["working_video_cut"] = dict(
                        dialog_manager.dialog_data["original_video_cut"])

                data = {
                    "has_video_cuts": True,
                    "period_text": period_text,
                    "video_name": current_video_cut.name or "Без названия",
                    "video_description": current_video_cut.description or "Описание отсутствует",
                    "has_tags": bool(tags),
                    "video_tags": tags_text,
                    "youtube_reference": current_video_cut.youtube_video_reference,
                    "created_at": self._format_datetime(current_video_cut.created_at),
                    "has_video": bool(current_video_cut.video_fid),
                    "video_media": video_media,
                    "current_index": current_index + 1,
                    "video_cuts_count": len(video_cuts),
                    "has_prev": current_index > 0,
                    "has_next": current_index < len(video_cuts) - 1,
                    "can_publish": False if employee.required_moderation else True,
                    "not_can_publish": True if employee.required_moderation else False
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

                self.logger.info("Список черновиков видео загружен")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_edit_preview_data(
            self,
            dialog_manager: DialogManager,
            bot: Bot,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftGetter.get_edit_preview_data",
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

                # Форматируем теги
                tags = working_video_cut.get("tags", [])
                tags_text = ", ".join(tags) if tags else ""

                video_media = await self._get_video_media(model.VideoCut(**working_video_cut))

                data = {
                    "created_at": self._format_datetime(original_video_cut["created_at"]),
                    "youtube_reference": working_video_cut["youtube_video_reference"],
                    "video_name": working_video_cut["name"] or "Без названия",
                    "video_description": working_video_cut["description"] or "Описание отсутствует",
                    "has_tags": bool(tags),
                    "video_tags": tags_text,
                    "has_video": bool(working_video_cut.get("video_fid")),
                    "video_media": video_media,
                    "has_changes": self._has_changes(dialog_manager),
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                
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
            "video_description": description,
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

    async def get_social_network_select_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftGetter.get_social_network_select_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

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

                data = {
                    "youtube_connected": youtube_connected,
                    "instagram_connected": instagram_connected,
                    "has_available_networks": youtube_connected or instagram_connected,
                    "no_connected_networks": not youtube_connected and not instagram_connected,
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    # Вспомогательные методы
    async def _get_video_media(self, current_video_cut: model.VideoCut) -> MediaAttachment | None:
        video_media = None
        if current_video_cut.video_fid:
            cached_file = await self.state_repo.get_cache_file(current_video_cut.video_name)

            video_media = MediaAttachment(
                file_id=MediaId(cached_file[0].file_id),
                type=ContentType.VIDEO,
            )

        return video_media

    def _has_changes(self, dialog_manager: DialogManager) -> bool:
        original = dialog_manager.dialog_data.get("original_video_cut", {})
        working = dialog_manager.dialog_data.get("working_video_cut", {})

        if not original or not working:
            return False

        # Сравниваем основные поля
        fields_to_compare = ["name", "description", "tags", "youtube_source", "inst_source"]
        for field in fields_to_compare:
            if original.get(field) != working.get(field):
                return True

        return False

    def _is_network_connected(self, social_networks: dict, network_type: str) -> bool:
        if not social_networks:
            return False

        return network_type in social_networks and len(social_networks[network_type]) > 0

    def _format_datetime(self, dt: str) -> str:
        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            # Форматируем в читаемый вид
            return dt.strftime("%d.%m.%Y %H:%M")
        except:
            return str(dt)

    def _get_period_text(self, video_cuts: list) -> str:
        if not video_cuts:
            return "Нет данных"

        # Находим самый старый и новый черновик
        dates = []
        for video_cut in video_cuts:
            if hasattr(video_cut, 'created_at') and video_cut.created_at:
                dates.append(video_cut.created_at)

        if not dates:
            return "Сегодня"

        # Простое определение периода на основе самого старого черновика
        oldest_date = min(dates)

        try:
            if isinstance(oldest_date, str):
                oldest_dt = datetime.fromisoformat(oldest_date.replace('Z', '+00:00'))
            else:
                oldest_dt = oldest_date

            now = datetime.now(timezone.utc)
            delta = now - oldest_dt
            hours = delta.total_seconds() / 3600

            if hours < 24:
                return "За сегодня"
            elif hours < 48:
                return "За последние 2 дня"
            elif hours < 168:  # неделя
                return "За неделю"
            else:
                return "За месяц"
        except:
            return "За неделю"

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

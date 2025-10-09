from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class AlertsGetter(interface.IAlertsGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_content_client = loom_content_client

    @auto_log()
    @traced_method()
    async def get_video_alert_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self._get_user_state(dialog_manager)

        alerts = await self.state_repo.get_vizard_video_cut_alert_by_state_id(state.id)

        if not alerts:
            self.logger.info("Алерты не найдены")
            return {}

        alerts_count = len(alerts)
        has_multiple_alerts = alerts_count > 1

        if has_multiple_alerts:
            self.logger.info("Обнаружено несколько алертов")
            alerts_text_parts = []
            for i, alert in enumerate(alerts, 1):
                video_word = self._get_video_word(alert.video_count)
                alerts_text_parts.append(
                    f"📺 <b>{i}.</b> {alert.video_count} {video_word} из видео:\n"
                    f"🔗 <a href='{alert.youtube_video_reference}'>Исходное видео</a>\n"
                )

            alerts_text = "<br/>".join(alerts_text_parts)
            alerts_word = self._get_alerts_word(alerts_count)

            data = {
                "has_multiple_alerts": True,
                "alerts_count": alerts_count,
                "alerts_word": alerts_word,
                "alerts_text": alerts_text,
            }
        else:
            self.logger.info("Обнаружен один алерт")
            alert = alerts[0]
            video_word = self._get_video_word(alert.video_count)

            data = {
                "has_multiple_alerts": False,
                "video_count": alert.video_count,
                "video_word": video_word,
                "youtube_video_reference": alert.youtube_video_reference,
            }

        return data

    @auto_log()
    @traced_method()
    async def get_publication_approved_alert_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self._get_user_state(dialog_manager)

        alerts = await self.state_repo.get_publication_approved_alert_by_state_id(state.id)

        if not alerts:
            self.logger.info("Алерты о публикациях не найдены")
            return {}

        alerts_count = len(alerts)
        has_multiple_alerts = alerts_count > 1

        if has_multiple_alerts:
            self.logger.info(f"Обнаружено {alerts_count} алертов о публикациях")

            publications = []
            for alert in alerts:
                publication = await self.loom_content_client.get_publication_by_id(alert.publication_id)
                publications.append(publication)

            publications_text_parts = []
            for i, pub in enumerate(publications, 1):
                links = []
                if pub.tg_link:
                    links.append(f"<a href='{pub.tg_link}'>📱 Telegram</a>")
                if pub.vk_link:
                    links.append(f"<a href='{pub.vk_link}'>🔵 ВКонтакте</a>")

                links_text = "  •  ".join(links) if links else "Ссылки пока недоступны"

                publications_text_parts.append(f"<b>{i}.</b>  {links_text}")

            publications_text = "<br/>".join(publications_text_parts)

            data = {
                "has_multiple_publication_approved_alerts": True,
                "alerts_count": alerts_count,
                "publications_text": publications_text,
            }
        else:
            self.logger.info("Обнаружен один алерт о публикации")
            alert = alerts[0]

            publication = await self.loom_content_client.get_publication_by_id(alert.publication_id)

            links = []
            if publication.tg_link:
                links.append(f"<a href='{publication.tg_link}'>📱 Telegram</a>")
            if publication.vk_link:
                links.append(f"<a href='{publication.vk_link}'>🔵 ВКонтакте</a>")

            links_text = "  •  ".join(links) if links else ""

            data = {
                "has_multiple_publication_approved_alerts": False,
                "links_text": links_text,
                "has_post_links": bool(publication.tg_link or publication.vk_link),
            }

        return data

    @auto_log()
    @traced_method()
    async def get_publication_rejected_alert_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self._get_user_state(dialog_manager)

        alerts = await self.state_repo.get_publication_rejected_alert_by_state_id(state.id)

        if not alerts:
            self.logger.info("Алерты об отклоненных публикациях не найдены")
            return {}

        alerts_count = len(alerts)
        has_multiple_alerts = alerts_count > 1

        if has_multiple_alerts:
            self.logger.info(f"Обнаружено {alerts_count} алертов об отклоненных публикациях")

            publications = []
            for alert in alerts:
                publication = await self.loom_content_client.get_publication_by_id(alert.publication_id)
                publications.append(publication)

            publications_text_parts = []
            for pub in publications:
                text_preview = self._extract_first_line(pub.text)
                publications_text_parts.append(f"<li>{text_preview}</li>")

            publications_text = f"<ol>{''.join(publications_text_parts)}</ol>"
            publications_word = self._get_publication_word(alerts_count)
            was_word = self._get_was_word(alerts_count)

            data = {
                "has_multiple_publication_rejected_alerts": True,
                "alerts_count": alerts_count,
                "publications_word": publications_word,
                "was_word": was_word,
                "publications_text": publications_text,
            }
        else:
            self.logger.info("Обнаружен один алерт об отклоненной публикации")
            alert = alerts[0]

            publication = await self.loom_content_client.get_publication_by_id(alert.publication_id)
            text_preview = self._extract_first_line(publication.text)

            data = {
                "has_multiple_publication_rejected_alerts": False,
                "publication_id": publication.id,
                "text_preview": text_preview,
                "has_moderation_comment": bool(publication.moderation_comment),
                "moderation_comment": publication.moderation_comment or "",
            }

        return data

    async def _get_user_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'callback_query') and dialog_manager.event.callback_query:
            chat_id = dialog_manager.event.callback_query.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

        state_list = await self.state_repo.state_by_id(chat_id)
        if not state_list:
            raise ValueError(f"State not found for chat_id: {chat_id}")

        return state_list[0]

    def _get_video_word(self, count: int) -> str:
        if count % 10 == 1 and count % 100 != 11:
            return "видео"
        elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
            return "видео"
        else:
            return "видео"

    def _get_alerts_word(self, count: int) -> str:
        if count % 10 == 1 and count % 100 != 11:
            return "видео"
        elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
            return "видео"
        else:
            return "видео"

    def _get_publication_word(self, count: int) -> str:
        if count % 10 == 1 and count % 100 != 11:
            return "публикация"
        elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
            return "публикации"
        else:
            return "публикаций"

    def _get_was_word(self, count: int) -> str:
        if count % 10 == 1 and count % 100 != 11:
            return "была"
        else:
            return "были"

    def _extract_first_line(self, text: str) -> str:
        max_length = 50
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text

import asyncio
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class VideoCutsDraftService(interface.IVideoCutsDraftService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_content_client: interface.IKonturContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_content_client = kontur_content_client

    async def handle_navigate_video_cut(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_navigate_video_cut",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                current_index = dialog_manager.dialog_data.get("current_index", 0)
                video_cuts_list = dialog_manager.dialog_data.get("video_cuts_list", [])

                # Определяем направление навигации
                if button.widget_id == "prev_video_cut":
                    new_index = max(0, current_index - 1)
                else:  # next_video_cut
                    new_index = min(len(video_cuts_list) - 1, current_index + 1)

                if new_index == current_index:
                    await callback.answer()
                    return

                # Обновляем индекс
                dialog_manager.dialog_data["current_index"] = new_index

                # Сбрасываем рабочие данные для нового черновика
                dialog_manager.dialog_data.pop("working_video_cut", None)

                self.logger.info("Навигация по черновикам видео")

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка навигации", show_alert=True)
                raise

    async def handle_delete_video_cut(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_delete_video_cut",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                original_video_cut = dialog_manager.dialog_data["original_video_cut"]
                video_cut_id = original_video_cut["id"]

                await self.kontur_content_client.delete_video_cut(
                    video_cut_id=video_cut_id
                )

                self.logger.info("Черновик видео удален")

                await callback.answer("🗑 Черновик удален", show_alert=True)

                await self._remove_current_video_cut_from_list(dialog_manager)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка удаления", show_alert=True)
                raise

    async def handle_save_changes(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_save_changes",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                if not self._has_changes(dialog_manager):
                    await callback.answer("ℹ️ Нет изменений для сохранения", show_alert=True)
                    return

                await callback.answer()
                loading_message = await callback.message.answer("💾 Сохраняю изменения...")

                # Сохраняем изменения
                await self._save_video_cut_changes(dialog_manager)

                # Обновляем оригинальную версию
                dialog_manager.dialog_data["original_video_cut"] = dict(dialog_manager.dialog_data["working_video_cut"])

                await loading_message.edit_text("✅ Изменения сохранены!")
                await asyncio.sleep(2)
                try:
                    await loading_message.delete()
                except:
                    pass

                await dialog_manager.switch_to(model.VideoCutsDraftStates.video_cut_list)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка сохранения", show_alert=True)
                raise

    async def handle_edit_title_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_edit_title_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                new_title = text.strip()

                if not new_title:
                    await message.answer("❌ Название не может быть пустым")
                    return

                if len(new_title) > 100:  # YouTube Shorts лимит
                    await message.answer("❌ Слишком длинное название (макс. 100 символов для YouTube)")
                    return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_video_cut"]["name"] = new_title

                await message.delete()
                await message.answer("✅ Название обновлено!")
                await dialog_manager.switch_to(model.VideoCutsDraftStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при сохранении названия")
                raise

    async def handle_edit_description_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_edit_description_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                new_description = text.strip()

                if not new_description:
                    await message.answer("❌ Описание не может быть пустым")
                    return

                if len(new_description) > 2200:  # Instagram лимит
                    await message.answer("❌ Слишком длинное описание (макс. 2200 символов для Instagram)")
                    return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_video_cut"]["description"] = new_description

                await message.delete()
                await message.answer("✅ Описание обновлено!")
                await dialog_manager.switch_to(model.VideoCutsDraftStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при сохранении описания")
                raise

    async def handle_edit_tags_save(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_edit_tags_save",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                tags_raw = text.strip()

                if not tags_raw:
                    new_tags = []
                else:
                    # Парсим теги
                    new_tags = [tag.strip() for tag in tags_raw.split(",")]
                    new_tags = [tag for tag in new_tags if tag]

                    if len(new_tags) > 15:  # YouTube лимит
                        await message.answer("❌ Слишком много тегов (макс. 15 для YouTube)")
                        return

                # Обновляем рабочую версию
                dialog_manager.dialog_data["working_video_cut"]["tags"] = new_tags

                await message.delete()
                await message.answer(f"✅ Теги обновлены ({len(new_tags)} шт.)")
                await dialog_manager.switch_to(model.VideoCutsDraftStates.edit_preview)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Ошибка при сохранении тегов")
                raise

    async def handle_back_to_video_cut_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_back_to_video_cut_list",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.switch_to(model.VideoCutsDraftStates.video_cut_list)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_send_to_moderation_with_networks(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_send_to_moderation_with_networks",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Проверяем, что выбрана хотя бы одна соцсеть
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                if not has_selected_networks:
                    await callback.answer(
                        "⚠️ Выберите хотя бы одну социальную сеть для публикации",
                        show_alert=True
                    )
                    return

                # Если есть несохраненные изменения, сохраняем их
                if self._has_changes(dialog_manager):
                    await self._save_video_cut_changes(dialog_manager)

                # Сохраняем выбранные соцсети в видео-нарезку
                await self._save_selected_networks(dialog_manager)

                original_video_cut = dialog_manager.dialog_data["original_video_cut"]
                video_cut_id = original_video_cut["id"]

                # Отправляем на модерацию через API
                await self.kontur_content_client.send_video_cut_to_moderation(
                    video_cut_id=video_cut_id
                )

                # Формируем сообщение о выбранных сетях
                published_networks = []
                if selected_networks.get("youtube_checkbox", False):
                    published_networks.append("📺 YouTube Shorts")
                if selected_networks.get("instagram_checkbox", False):
                    published_networks.append("📸 Instagram Reels")

                networks_text = ", ".join(published_networks)

                self.logger.info("Черновик видео отправлен на модерацию с выбранными соцсетями")

                await callback.answer(f"📤 Отправлено на модерацию!\n\nВыбранные сети: {networks_text}", show_alert=True)

                # Удаляем черновик из списка (он больше не черновик)
                await self._remove_current_video_cut_from_list(dialog_manager)

                await dialog_manager.switch_to(model.VideoCutsDraftStates.video_cut_list)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка отправки", show_alert=True)
                raise

    async def handle_publish_with_selected_networks(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_publish_with_selected_networks",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Проверяем, что выбрана хотя бы одна соцсеть
                selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})
                has_selected_networks = any(selected_networks.values())

                if not has_selected_networks:
                    await callback.answer(
                        "⚠️ Выберите хотя бы одну социальную сеть для публикации",
                        show_alert=True
                    )
                    return

                await callback.answer()
                loading_message = await callback.message.answer("🚀 Публикую видео...")

                # Если есть несохраненные изменения, сохраняем их
                if self._has_changes(dialog_manager):
                    await self._save_video_cut_changes(dialog_manager)

                # Сохраняем выбранные соцсети в видео-нарезку
                await self._save_selected_networks(dialog_manager)

                state = await self._get_state(dialog_manager)
                original_video_cut = dialog_manager.dialog_data["original_video_cut"]
                video_cut_id = original_video_cut["id"]

                # Публикуем немедленно через API
                await self.kontur_content_client.moderate_video_cut(
                    video_cut_id=video_cut_id,
                    moderator_id=state.account_id,
                    moderation_status="approved",
                )

                # Формируем сообщение о публикации
                published_networks = []
                if selected_networks.get("youtube_checkbox", False):
                    published_networks.append("📺 YouTube Shorts")
                if selected_networks.get("instagram_checkbox", False):
                    published_networks.append("📸 Instagram Reels")

                networks_text = ", ".join(published_networks)

                self.logger.info(   "Черновик видео опубликован с выбранными соцсетями")

                await loading_message.edit_text(
                    f"🚀 Видео успешно опубликовано!\n\n"
                    f"📋 Опубликовано в: {networks_text}"
                )

                await asyncio.sleep(3)
                try:
                    await loading_message.delete()
                except:
                    pass

                # Удаляем черновик из списка
                await self._remove_current_video_cut_from_list(dialog_manager)

                # Возвращаемся к списку черновиков
                await dialog_manager.switch_to(model.VideoCutsDraftStates.video_cut_list)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка публикации", show_alert=True)
                raise

    async def handle_toggle_social_network(
            self,
            callback: CallbackQuery,
            checkbox: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_toggle_social_network",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Инициализируем словарь выбранных соцсетей если его нет
                if "selected_social_networks" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["selected_social_networks"] = {}

                network_id = checkbox.widget_id
                is_checked = checkbox.is_checked()

                # Сохраняем состояние чекбокса
                dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

                self.logger.info( "Социальная сеть переключена в черновиках видео")

                await callback.answer()
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_back_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "VideoCutsDraftService.handle_back_to_content_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                if await self._check_alerts(dialog_manager):
                    return

                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    # Вспомогательные методы
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

    async def _save_selected_networks(self, dialog_manager: DialogManager) -> None:
        working_video_cut = dialog_manager.dialog_data["working_video_cut"]
        selected_networks = dialog_manager.dialog_data.get("selected_social_networks", {})

        # Обновляем выбранные платформы
        youtube_selected = selected_networks.get("youtube_checkbox", False)
        instagram_selected = selected_networks.get("instagram_checkbox", False)

        working_video_cut["youtube_source"] = youtube_selected
        working_video_cut["inst_source"] = instagram_selected

        # Сохраняем изменения через API
        await self._save_video_cut_changes(dialog_manager)

    async def _save_video_cut_changes(self, dialog_manager: DialogManager) -> None:
        working_video_cut = dialog_manager.dialog_data["working_video_cut"]
        video_cut_id = working_video_cut["id"]
        youtube_source = working_video_cut.get("youtube_source")
        inst_source = working_video_cut.get("inst_source")

        await self.kontur_content_client.change_video_cut(
            video_cut_id=video_cut_id,
            name=working_video_cut["name"],
            description=working_video_cut["description"],
            tags=working_video_cut.get("tags", []),
            youtube_source=youtube_source,
            inst_source=inst_source
        )

    async def _remove_current_video_cut_from_list(self, dialog_manager: DialogManager) -> None:
        video_cuts_list = dialog_manager.dialog_data.get("video_cuts_list", [])
        current_index = dialog_manager.dialog_data.get("current_index", 0)

        if video_cuts_list and current_index < len(video_cuts_list):
            video_cuts_list.pop(current_index)

            # Корректируем индекс если нужно
            if current_index >= len(video_cuts_list) and video_cuts_list:
                dialog_manager.dialog_data["current_index"] = len(video_cuts_list) - 1
            elif not video_cuts_list:
                dialog_manager.dialog_data["current_index"] = 0

            # Сбрасываем рабочие данные
            dialog_manager.dialog_data.pop("working_video_cut", None)
            dialog_manager.dialog_data.pop("original_video_cut", None)

    async def _check_alerts(self, dialog_manager: DialogManager) -> bool:
        state = await self._get_state(dialog_manager)

        vizard_alerts = await self.state_repo.get_vizard_video_cut_alert_by_state_id(
            state_id=state.id
        )
        if vizard_alerts:
            await dialog_manager.start(
                model.GenerateVideoCutStates.video_generated_alert,
                mode=StartMode.RESET_STACK,
                show_mode=ShowMode.EDIT,
            )
            return True

        return False

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

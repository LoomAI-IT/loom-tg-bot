from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import Button


from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class ContentMenuService(interface.IContentMenuService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            llm_chat_repo: interface.ILLMChatRepo,
            loom_employee_client: interface.ILoomEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.llm_chat_repo = llm_chat_repo
        self.loom_employee_client = loom_employee_client

    @auto_log()
    @traced_method()
    async def handle_go_to_publication_generation(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        state = await self._get_state(dialog_manager=dialog_manager)
        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=False
        )

        await dialog_manager.start(
            state=model.GeneratePublicationStates.select_category,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_video_cut_generation(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        state = await self._get_state(dialog_manager=dialog_manager)
        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=False
        )

        await dialog_manager.start(
            state=model.GenerateVideoCutStates.input_youtube_link,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_publication_drafts(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        state = await self._get_state(dialog_manager=dialog_manager)
        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=False
        )

        await dialog_manager.start(
            state=model.DraftPublicationStates.draft_list,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_video_drafts(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        state = await self._get_state(dialog_manager=dialog_manager)
        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=False
        )

        await dialog_manager.start(
            state=model.VideoCutsDraftStates.video_cut_list,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_publication_moderation(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        state = await self._get_state(dialog_manager=dialog_manager)

        employee = await self.loom_employee_client.get_employee_by_account_id(
            account_id=state.account_id
        )

        can_moderate = employee.role in ["moderator", "admin"]

        if not can_moderate:
            self.logger.info("Отказ в доступе: недостаточно прав для модерации публикаций")
            await callback.answer(
                "У вас нет прав для доступа к модерации публикаций",
                show_alert=True
            )
            return

        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=False
        )

        await dialog_manager.start(
            state=model.ModerationPublicationStates.moderation_list,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_video_moderation(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        state = await self._get_state(dialog_manager=dialog_manager)

        employee = await self.loom_employee_client.get_employee_by_account_id(
            account_id=state.account_id
        )

        can_moderate = employee.role in ["moderator", "admin"]

        if not can_moderate:
            self.logger.info("Отказ в доступе: недостаточно прав для модерации видео-нарезок")
            await callback.answer(
                "У вас нет прав для доступа к модерации видео",
                show_alert=True
            )
            return

        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=False
        )

        await dialog_manager.start(
            state=model.VideoCutModerationStates.moderation_list,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await dialog_manager.start(
            state=model.MainMenuStates.main_menu,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_content_menu(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await dialog_manager.start(
            state=model.ContentMenuStates.content_menu,
            mode=StartMode.RESET_STACK
        )

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

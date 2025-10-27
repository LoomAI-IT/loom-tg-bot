from aiogram_dialog import DialogManager, StartMode

from internal import interface, model


class CategoryManager:
    def __init__(
            self,
            logger,
            loom_content_client: interface.ILoomContentClient,
            loom_employee_client: interface.ILoomEmployeeClient,
            llm_chat_repo: interface.ILLMChatRepo,
    ):
        self.logger = logger
        self.loom_content_client = loom_content_client
        self.loom_employee_client = loom_employee_client
        self.llm_chat_repo = llm_chat_repo

    async def select_category(
            self,
            dialog_manager: DialogManager,
            category_id: int
    ) -> tuple[int, str, str]:
        category = await self.loom_content_client.get_category_by_id(
            category_id=category_id
        )

        dialog_manager.dialog_data["category_id"] = category.id
        dialog_manager.dialog_data["category_name"] = category.name
        dialog_manager.dialog_data["category_hint"] = category.hint

        return category.id, category.name, category.hint

    def has_start_text(self, dialog_manager: DialogManager) -> bool:
        if dialog_manager.start_data:
            return dialog_manager.start_data.get("has_input_text", False)
        return False

    def set_start_text(self, dialog_manager: DialogManager) -> None:
        if dialog_manager.start_data and dialog_manager.start_data.get("has_input_text"):
            self.logger.info("Есть стартовый текст")
            dialog_manager.dialog_data["has_input_text"] = True
            dialog_manager.dialog_data["input_text"] = dialog_manager.start_data["input_text"]

    async def check_category_permission(
            self,
            state: model.UserState
    ) -> bool:
        employee = await self.loom_employee_client.get_employee_by_account_id(
            account_id=state.account_id
        )
        return employee.setting_category_permission

    async def navigate_to_create_category(
            self,
            dialog_manager: DialogManager,
            state: model.UserState
    ) -> bool:
        if await self.check_category_permission(state):
            self.logger.info("Отказано в доступе к созданию категории")
            return False

        # Удаляем существующий чат
        chat = await self.llm_chat_repo.get_chat_by_state_id(state_id=state.id)
        if chat:
            await self.llm_chat_repo.delete_chat(chat_id=chat[0].id)

        await dialog_manager.start(
            state=model.CreateCategoryStates.create_category,
            mode=StartMode.RESET_STACK
        )
        return True

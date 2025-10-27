from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class OrganizationMenuGetter(interface.IOrganizationMenuGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_employee_client: interface.ILoomEmployeeClient,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_organization_client = loom_organization_client
        self.loom_employee_client = loom_employee_client
        self.loom_content_client = loom_content_client

    @auto_log()
    @traced_method()
    async def get_organization_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self.__get_state(dialog_manager)

        organization = await self.loom_organization_client.get_organization_by_id(
            state.organization_id
        )

        categories = await self.loom_content_client.get_categories_by_organization(
            state.organization_id
        )

        if categories:
            self.logger.info("Категории найдены - форматирование списка")
            categories_list = "<br/>".join([f"• {category.name}" for category in categories])
        else:
            self.logger.info("Категории не найдены")
            categories_list = "Нет категорий"

        data = {
            "organization_name": organization.name,
            "balance": organization.rub_balance,
            "categories_list": categories_list,
        }

        return data

    async def __get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            chat_id = None

        state = (await self.state_repo.state_by_id(chat_id))[0]
        return state

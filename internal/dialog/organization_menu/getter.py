from aiogram_dialog import DialogManager

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class OrganizationMenuGetter(interface.IOrganizationMenuGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_organization_client: interface.IKonturOrganizationClient,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_content_client: interface.IKonturContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_organization_client = kontur_organization_client
        self.kontur_employee_client = kontur_employee_client
        self.kontur_content_client = kontur_content_client

    async def get_organization_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "OrganizationMenuDialogService.get_organization_menu_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self.__get_state(dialog_manager)

                # Получаем данные организации
                organization = await self.kontur_organization_client.get_organization_by_id(
                    state.organization_id
                )

                categories = await self.kontur_content_client.get_categories_by_organization(
                    state.organization_id
                )

                # Форматируем список рубрик
                if categories:
                    categories_list = "\n".join([f"• {category.name}" for category in categories])
                else:
                    categories_list = "Нет категорий"

                data = {
                    "organization_name": organization.name,
                    "balance": organization.rub_balance,
                    "categories_list": categories_list,
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def __get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            chat_id = None

        state = (await self.state_repo.state_by_id(chat_id))[0]
        return state

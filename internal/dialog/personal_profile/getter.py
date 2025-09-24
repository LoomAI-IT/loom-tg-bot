from aiogram_dialog import DialogManager
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class PersonalProfileGetter(interface.IPersonalProfileGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_organization_client: interface.IKonturOrganizationClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client
        self.kontur_organization_client = kontur_organization_client

    async def get_personal_profile_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "PersonalProfileDialogService.get_personal_profile_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self.__get_state(dialog_manager)

                # Получаем данные сотрудника
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                # Получаем данные организации
                organization = await self.kontur_organization_client.get_organization_by_id(
                    state.organization_id
                )

                # Формируем список разрешений
                permissions_list = []
                if employee:
                    if not employee.required_moderation:
                        permissions_list.append("✅ Публикации без одобрения")
                    if employee.autoposting_permission:
                        permissions_list.append("✅ Авто-постинг")
                    if employee.add_employee_permission:
                        permissions_list.append("✅ Добавление сотрудников")
                    if employee.edit_employee_perm_permission:
                        permissions_list.append("✅ Изменение разрешений")
                    if employee.top_up_balance_permission:
                        permissions_list.append("✅ Пополнение баланса")
                    if employee.sign_up_social_net_permission:
                        permissions_list.append("✅ Подключение соцсетей")

                if not permissions_list:
                    permissions_list.append("❌ Нет специальных разрешений")

                # Получаем имя пользователя из события
                user = dialog_manager.event.from_user
                name = user.first_name or user.username or "Пользователь"

                data = {
                    "name": name,
                    "organization_name": organization.name if organization else "Неизвестно",
                    "publications_count": 0,  # TODO: Получить реальные данные из API публикаций
                    "generations_count": 0,  # TODO: Получить реальные данные из API публикаций
                    "permissions_list": "\n".join(permissions_list),
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
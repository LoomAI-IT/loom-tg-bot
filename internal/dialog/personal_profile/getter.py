from datetime import datetime

from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.trace_wrapper import traced_method


class PersonalProfileGetter(interface.IPersonalProfileGetter):
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

    @traced_method()
    async def get_personal_profile_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        self.logger.info("Начало получения данных личного профиля")

        state = await self._get_state(dialog_manager)

        employee = await self.loom_employee_client.get_employee_by_account_id(
            state.account_id
        )

        organization = await self.loom_organization_client.get_organization_by_id(
            state.organization_id
        )

        publications = await self.loom_content_client.get_publications_by_organization(
            state.organization_id
        )

        generated_publication_count = 0
        published_publication_count = 0

        rejected_publication_count = 0
        approved_publication_count = 0

        for pub in publications:
            if pub.moderator_id == employee.account_id:
                if pub.moderation_status == "approved":
                    approved_publication_count += 1
                elif pub.moderation_status == "rejected":
                    rejected_publication_count += 1

            if pub.creator_id == employee.account_id:
                generated_publication_count += 1

                if pub.moderation_status == "approved":
                    published_publication_count += 1

        permissions_list = []
        if not employee.required_moderation:
            permissions_list.append("✅ Публикации без модерации")
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

        permissions_text = "<br>".join(permissions_list)

        created_at = employee.created_at
        if isinstance(created_at, str):
            try:
                created_date = datetime.fromisoformat(created_at)
                created_at = created_date.strftime("%d.%m.%Y")
            except:
                self.logger.info("Не удалось отформатировать дату создания")
                created_at = "неизвестно"

        data = {
            "employee_name": employee.name,
            "employee_tg_username": state.tg_username,
            "account_id": employee.account_id,
            "role": employee.role,
            "organization_name": organization.name,
            "role_display": self._get_role_display_name(employee.role),
            "created_at": created_at,
            "permissions_text": permissions_text,
            "generated_publication_count": generated_publication_count,
            "published_publication_count": published_publication_count,
            "rejected_publication_count": rejected_publication_count,
            "approved_publication_count": approved_publication_count,
            "has_moderated_publications": bool(rejected_publication_count or approved_publication_count),
        }

        self.logger.info("Завершение получения данных личного профиля")
        return data

    def _get_role_display_name(self, role: str) -> str:
        role_names = {
            "employee": "Сотрудник",
            "moderator": "Модератор",
            "admin": "Администратор",
            "owner": "Владелец",
        }
        return role_names.get(role, role.capitalize())

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            chat_id = None

        state = (await self.state_repo.state_by_id(chat_id))[0]
        return state

from internal import interface


class _OrganizationManager:
    def __init__(
            self,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_employee_client: interface.ILoomEmployeeClient,
            state_repo: interface.IStateRepo
    ):
        self.loom_organization_client = loom_organization_client
        self.loom_employee_client = loom_employee_client
        self.state_repo = state_repo

    async def create_organization_and_admin(
            self,
            state_id: int,
            account_id: int,
            organization_data: dict,
    ) -> int:
        organization_id = await self.loom_organization_client.create_organization(
            name=organization_data["name"]
        )

        await self.loom_organization_client.update_organization(
            organization_id=organization_id,
            name=organization_data["name"],
            description=organization_data["description"],
            tone_of_voice=organization_data["tone_of_voice"],
            compliance_rules=organization_data["compliance_rules"],
            products=organization_data["products"],
            locale=organization_data["locale"],
            additional_info=organization_data["additional_info"],
        )
        await self.state_repo.change_user_state(
            state_id=state_id,
            organization_id=organization_id,
        )

        await self.loom_employee_client.create_employee(
            organization_id=organization_id,
            invited_from_account_id=0,
            account_id=account_id,
            name="admin",
            role="admin"
        )

        return organization_id


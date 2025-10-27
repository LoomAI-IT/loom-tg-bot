from internal import interface


class _OrganizationManager:
    def __init__(
            self,
            loom_organization_client: interface.ILoomOrganizationClient,
    ):
        self.loom_organization_client = loom_organization_client

    async def update_organization(
            self,
            organization_id: int,
            organization_data: dict,
    ) -> None:
        await self.loom_organization_client.update_organization(
            organization_id=organization_id,
            name=organization_data.get("name"),
            description=organization_data.get("description"),
            tone_of_voice=organization_data.get("tone_of_voice"),
            compliance_rules=organization_data.get("compliance_rules"),
            products=organization_data.get("products"),
            locale=organization_data.get("locale"),
            additional_info=organization_data.get("additional_info"),
        )

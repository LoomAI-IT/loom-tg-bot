from internal import interface, model


class BalanceManager:
    def __init__(self, loom_organization_client: interface.ILoomOrganizationClient):
        self.loom_organization_client = loom_organization_client
        self.avg_generate_text_rub_cost = 3
        self.avg_generate_image_rub_cost = 25
        self.avg_edit_image_rub_cost = 5
        self.avg_transcribe_audio_rub_cost = 1

    def check_balance(
            self,
            organization: model.Organization,
            organization_cost_multiplier: model.CostMultiplier,
            operation: str
    ) -> bool:
        if operation == "generate_text":
            return float(
                organization.rub_balance) < organization_cost_multiplier.generate_text_cost_multiplier * self.avg_generate_text_rub_cost
        elif operation == "generate_image":
            return float(
                organization.rub_balance) < organization_cost_multiplier.generate_image_cost_multiplier * self.avg_generate_image_rub_cost
        elif operation == "edit_image":
            return float(
                organization.rub_balance) < organization_cost_multiplier.generate_image_cost_multiplier * self.avg_edit_image_rub_cost
        elif operation == "transcribe_audio":
            return float(
                organization.rub_balance) < organization_cost_multiplier.transcribe_audio_cost_multiplier * self.avg_transcribe_audio_rub_cost
        return True

    async def check_balance_for_operation(
            self,
            organization_id: int,
            operation: str
    ) -> bool:
        organization = await self.loom_organization_client.get_organization_by_id(organization_id)
        organization_cost_multiplier = await self.loom_organization_client.get_cost_multiplier(organization_id)

        return self.check_balance(organization, organization_cost_multiplier, operation)

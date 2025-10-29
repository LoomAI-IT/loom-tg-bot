from internal import model


class BalanceManager:
    def __init__(self):
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
        """
        Проверяет достаточность баланса для операции.

        Returns:
            True если баланса НЕ хватает, False если хватает
        """
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

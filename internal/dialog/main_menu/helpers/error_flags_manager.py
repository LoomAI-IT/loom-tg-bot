from aiogram_dialog import DialogManager


class ErrorFlagsManager:
    @staticmethod
    def clear(dialog_manager: DialogManager, *flag_names: str) -> None:
        for flag_name in flag_names:
            dialog_manager.dialog_data.pop(flag_name, None)

    @staticmethod
    def clear_input(dialog_manager: DialogManager) -> None:
        ErrorFlagsManager.clear(
            dialog_manager,
            "has_void_input_text",
            "has_small_input_text",
            "has_big_input_text",
            "has_invalid_content_type",
            "has_insufficient_balance"
        )

from aiogram_dialog import DialogManager


class _ErrorFlagsManager:
    @staticmethod
    def clear_error_flags(dialog_manager: DialogManager, *flag_names: str) -> None:
        for flag_name in flag_names:
            dialog_manager.dialog_data.pop(flag_name, None)

    @staticmethod
    def clear_input_error_flags(dialog_manager: DialogManager) -> None:
        _ErrorFlagsManager.clear_error_flags(
            dialog_manager,
            "has_void_input_text",
            "has_small_input_text",
            "has_big_input_text",
            "has_invalid_content_type"
        )

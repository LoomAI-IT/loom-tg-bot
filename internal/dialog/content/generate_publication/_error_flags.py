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

    @staticmethod
    def clear_regenerate_prompt_error_flags(dialog_manager: DialogManager) -> None:
        _ErrorFlagsManager.clear_error_flags(
            dialog_manager,
            "has_void_regenerate_prompt",
            "has_small_regenerate_prompt",
            "has_big_regenerate_prompt",
            "has_invalid_content_type"
        )

    @staticmethod
    def clear_image_prompt_error_flags(dialog_manager: DialogManager) -> None:
        _ErrorFlagsManager.clear_error_flags(
            dialog_manager,
            "has_void_image_prompt",
            "has_small_image_prompt",
            "has_big_image_prompt",
            "has_invalid_content_type",
            "has_empty_voice_text"
        )

    @staticmethod
    def clear_text_edit_error_flags(dialog_manager: DialogManager) -> None:
        _ErrorFlagsManager.clear_error_flags(
            dialog_manager,
            "has_void_text",
            "has_big_text",
            "has_small_text"
        )

    @staticmethod
    def clear_image_upload_error_flags(dialog_manager: DialogManager) -> None:
        _ErrorFlagsManager.clear_error_flags(
            dialog_manager,
            "has_invalid_image_type",
            "has_big_image_size"
        )

    @staticmethod
    def clear_combine_prompt_error_flags(dialog_manager: DialogManager) -> None:
        _ErrorFlagsManager.clear_error_flags(
            dialog_manager,
            "has_small_combine_prompt",
            "has_big_combine_prompt",
            "has_invalid_content_type"
        )

    @staticmethod
    def clear_combine_upload_error_flags(dialog_manager: DialogManager) -> None:
        _ErrorFlagsManager.clear_error_flags(
            dialog_manager,
            "has_invalid_combine_image_type",
            "has_big_combine_image_size",
            "combine_images_limit_reached"
        )

    @staticmethod
    def clear_new_image_confirm_error_flags(dialog_manager: DialogManager) -> None:
        _ErrorFlagsManager.clear_error_flags(
            dialog_manager,
            "has_small_edit_prompt",
            "has_big_edit_prompt",
            "has_invalid_content_type"
        )

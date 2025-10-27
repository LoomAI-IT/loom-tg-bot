from aiogram_dialog import DialogManager


class DialogDataHelper:
    @staticmethod
    def get_working_publication(dialog_manager: DialogManager) -> dict:
        return dialog_manager.dialog_data["working_publication"]

    @staticmethod
    def get_working_publication_safe(dialog_manager: DialogManager) -> dict:
        return dialog_manager.dialog_data.get("working_publication", {})

    @staticmethod
    def get_original_publication(dialog_manager: DialogManager) -> dict:
        return dialog_manager.dialog_data["original_publication"]

    @staticmethod
    def get_original_publication_safe(dialog_manager: DialogManager) -> dict:
        return dialog_manager.dialog_data.get("original_publication", {})

    @staticmethod
    def clear_working_publication(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("working_publication", None)

    @staticmethod
    def update_working_text(dialog_manager: DialogManager, new_text: str) -> None:
        dialog_manager.dialog_data["working_publication"]["text"] = new_text

    @staticmethod
    def update_original_from_working(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data["original_publication"] = dialog_manager.dialog_data["working_publication"]

    @staticmethod
    def set_working_image_has_image(dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["working_publication"]["has_image"] = value

    @staticmethod
    def get_working_image_has_image(dialog_manager: DialogManager) -> bool:
        return dialog_manager.dialog_data["working_publication"].get("has_image", False)

    @staticmethod
    def set_working_image_index(dialog_manager: DialogManager, index: int) -> None:
        dialog_manager.dialog_data["working_publication"]["current_image_index"] = index

    @staticmethod
    def remove_working_image_fields(dialog_manager: DialogManager, *fields: str) -> None:
        for field in fields:
            dialog_manager.dialog_data["working_publication"].pop(field, None)

    @staticmethod
    def set_working_generated_images(dialog_manager: DialogManager, images_url: list[str]) -> None:
        dialog_manager.dialog_data["working_publication"]["generated_images_url"] = images_url

    @staticmethod
    def set_working_custom_image(dialog_manager: DialogManager, file_id: str) -> None:
        dialog_manager.dialog_data["working_publication"]["custom_image_file_id"] = file_id
        dialog_manager.dialog_data["working_publication"]["is_custom_image"] = True

    @staticmethod
    def get_current_index(dialog_manager: DialogManager) -> int:
        return dialog_manager.dialog_data.get("current_index", 0)

    @staticmethod
    def set_current_index(dialog_manager: DialogManager, index: int) -> None:
        dialog_manager.dialog_data["current_index"] = index

    @staticmethod
    def get_moderation_list(dialog_manager: DialogManager) -> list:
        return dialog_manager.dialog_data.get("moderation_list", [])

    @staticmethod
    def clear_working_publication_from_data(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("working_publication", None)

    @staticmethod
    def set_regenerating_text_flag(dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["is_regenerating_text"] = value

    @staticmethod
    def set_generating_image_flag(dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["is_generating_image"] = value

    @staticmethod
    def set_regenerate_prompt(dialog_manager: DialogManager, prompt: str) -> None:
        dialog_manager.dialog_data["regenerate_prompt"] = prompt
        dialog_manager.dialog_data["has_regenerate_prompt"] = True

    @staticmethod
    def clear_regenerate_prompt(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("regenerate_prompt", None)
        dialog_manager.dialog_data["has_regenerate_prompt"] = False

    @staticmethod
    def set_image_prompt(dialog_manager: DialogManager, prompt: str) -> None:
        dialog_manager.dialog_data["image_prompt"] = prompt

    @staticmethod
    def set_reject_comment(dialog_manager: DialogManager, comment: str) -> None:
        dialog_manager.dialog_data["reject_comment"] = comment

    @staticmethod
    def get_reject_comment_data(dialog_manager: DialogManager) -> tuple[dict, int, str]:
        original_pub = dialog_manager.dialog_data["original_publication"]
        publication_id = original_pub["id"]
        reject_comment = dialog_manager.dialog_data.get("reject_comment", "Нет комментария")
        return original_pub, publication_id, reject_comment

    @staticmethod
    def set_expected_length(dialog_manager: DialogManager, length: int) -> None:
        dialog_manager.dialog_data["expected_length"] = length

    @staticmethod
    def get_expected_length(dialog_manager: DialogManager, default: int = 900) -> int:
        return dialog_manager.dialog_data.get("expected_length", default)

    @staticmethod
    def set_previous_text(dialog_manager: DialogManager, text: str) -> None:
        dialog_manager.dialog_data["previous_text"] = text

    @staticmethod
    def get_previous_text(dialog_manager: DialogManager) -> str | None:
        return dialog_manager.dialog_data.get("previous_text")

    @staticmethod
    def set_previous_has_image(dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["previous_has_image"] = value

    @staticmethod
    def get_previous_has_image(dialog_manager: DialogManager) -> bool | None:
        return dialog_manager.dialog_data.get("previous_has_image")

    @staticmethod
    def has_previous_has_image(dialog_manager: DialogManager) -> bool:
        return "previous_has_image" in dialog_manager.dialog_data

    @staticmethod
    def clear_previous_state(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("previous_text", None)
        dialog_manager.dialog_data.pop("previous_has_image", None)

    @staticmethod
    def get_selected_social_networks(dialog_manager: DialogManager) -> dict:
        return dialog_manager.dialog_data.get("selected_social_networks", {})

    @staticmethod
    def set_validation_flag(dialog_manager: DialogManager, flag_name: str, value: bool = True) -> None:
        dialog_manager.dialog_data[flag_name] = value

    @staticmethod
    def clear_error_flags(dialog_manager: DialogManager, *flags: str) -> None:
        for flag in flags:
            dialog_manager.dialog_data.pop(flag, None)

    def clear_reject_comment_error_flags(self, dialog_manager: DialogManager) -> None:
        self.clear_error_flags(
            dialog_manager,
            "has_void_reject_comment",
            "has_small_reject_comment",
            "has_big_reject_comment"
        )

    def clear_regenerate_prompt_error_flags(self, dialog_manager: DialogManager) -> None:
        self.clear_error_flags(
            dialog_manager,
            "has_void_regenerate_prompt",
            "has_small_regenerate_prompt",
            "has_big_regenerate_prompt",
            "has_invalid_content_type"
        )

    def clear_image_prompt_error_flags(self, dialog_manager: DialogManager) -> None:
        self.clear_error_flags(
            dialog_manager,
            "has_void_image_prompt",
            "has_small_image_prompt",
            "has_big_image_prompt",
            "has_invalid_content_type"
        )

    def clear_text_edit_error_flags(self, dialog_manager: DialogManager) -> None:
        self.clear_error_flags(
            dialog_manager,
            "has_void_text",
            "has_big_text",
            "has_small_text"
        )

    def clear_image_upload_error_flags(self, dialog_manager: DialogManager) -> None:
        self.clear_error_flags(
            dialog_manager,
            "has_invalid_image_type",
            "has_big_image_size"
        )

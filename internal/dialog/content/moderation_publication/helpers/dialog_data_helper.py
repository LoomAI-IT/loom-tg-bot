from aiogram_dialog import DialogManager


class DialogDataHelper:
    @staticmethod
    def clear_working_publication(dialog_manager: DialogManager) -> None:
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
    def get_expected_length(dialog_manager: DialogManager, default: int = 900) -> int:
        return dialog_manager.dialog_data.get("expected_length", default)

    @staticmethod
    def get_working_publication(dialog_manager: DialogManager) -> dict:
        return dialog_manager.dialog_data["working_publication"]

    @staticmethod
    def get_original_publication(dialog_manager: DialogManager) -> dict:
        return dialog_manager.dialog_data["original_publication"]

    @staticmethod
    def update_working_text(dialog_manager: DialogManager, new_text: str) -> None:
        dialog_manager.dialog_data["working_publication"]["text"] = new_text

    @staticmethod
    def update_original_from_working(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data["original_publication"] = dialog_manager.dialog_data["working_publication"]

    @staticmethod
    def get_reject_comment_data(dialog_manager: DialogManager) -> tuple[dict, int, str]:
        original_pub = dialog_manager.dialog_data["original_publication"]
        publication_id = original_pub["id"]
        reject_comment = dialog_manager.dialog_data.get("reject_comment", "Нет комментария")
        return original_pub, publication_id, reject_comment

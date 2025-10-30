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
    def get_combine_images_choice_data(dialog_manager: DialogManager) -> dict:
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        has_image = working_pub.get("has_image", False)
        return {
            "has_image": has_image,
        }

    @staticmethod
    def get_combine_images_upload_flags(dialog_manager: DialogManager) -> dict:
        combine_images_list = dialog_manager.dialog_data.get("combine_images_list", [])
        combine_images_count = len(combine_images_list)

        return {
            "has_combine_images": combine_images_count > 0,
            "combine_images_count": combine_images_count,
            "has_multiple_combine_images": combine_images_count > 1,
            "has_enough_combine_images": combine_images_count >= 2,
            # Error flags
            "has_invalid_combine_image_type": dialog_manager.dialog_data.get("has_invalid_combine_image_type", False),
            "has_big_combine_image_size": dialog_manager.dialog_data.get("has_big_combine_image_size", False),
            "combine_images_limit_reached": dialog_manager.dialog_data.get("combine_images_limit_reached", False),
            "not_enough_combine_images": dialog_manager.dialog_data.get("not_enough_combine_images", False),
        }

    @staticmethod
    def get_combine_images_prompt_flags(dialog_manager: DialogManager) -> dict:
        combine_images_list = dialog_manager.dialog_data.get("combine_images_list", [])
        combine_images_count = len(combine_images_list)

        return {
            "is_combining_images": dialog_manager.dialog_data.get("is_combining_images", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            "has_combine_image_prompt": bool(dialog_manager.dialog_data.get("combine_image_prompt")),
            "combine_image_prompt": dialog_manager.dialog_data.get("combine_image_prompt", ""),
            # Image data for navigation
            "has_combine_images": combine_images_count > 0,
            "combine_images_count": combine_images_count,
            "has_multiple_combine_images": combine_images_count > 1,
            # Error flags
            "has_small_combine_image_prompt": dialog_manager.dialog_data.get("has_small_combine_image_prompt", False),
            "has_big_combine_image_prompt": dialog_manager.dialog_data.get("has_big_combine_image_prompt", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
            "has_insufficient_balance": dialog_manager.dialog_data.get("has_insufficient_balance", False),
        }

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
    def set_is_generating_image(dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["is_generating_image"] = value

    @staticmethod
    def set_regenerate_text_prompt(dialog_manager: DialogManager, prompt: str) -> None:
        dialog_manager.dialog_data["regenerate_text_prompt"] = prompt
        dialog_manager.dialog_data["has_regenerate_text_prompt"] = True

    @staticmethod
    def clear_regenerate_text_prompt(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("regenerate_text_prompt", None)
        dialog_manager.dialog_data["has_regenerate_text_prompt"] = False

    @staticmethod
    def set_edit_image_prompt(dialog_manager: DialogManager, prompt: str) -> None:
        dialog_manager.dialog_data["edit_image_prompt"] = prompt

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
        return dialog_manager.dialog_data.get("previous_text", "")

    @staticmethod
    def get_new_image_confirm_flags(dialog_manager: DialogManager) -> dict:
        return {
            "is_applying_edits": dialog_manager.dialog_data.get("is_applying_edits", False),
            "has_edit_image_prompt": dialog_manager.dialog_data.get("has_edit_image_prompt", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            "has_small_edit_image_prompt": dialog_manager.dialog_data.get("has_small_edit_image_prompt", False),
            "has_big_edit_image_prompt": dialog_manager.dialog_data.get("has_big_edit_image_prompt", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
            "has_insufficient_balance": dialog_manager.dialog_data.get("has_insufficient_balance", False),
        }

    @staticmethod
    def set_previous_has_image(dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["previous_has_image"] = value

    @staticmethod
    def get_previous_has_image(dialog_manager: DialogManager) -> bool | None:
        return dialog_manager.dialog_data.get("previous_has_image", False)

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
    def set_has_insufficient_balance(dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["has_insufficient_balance"] = value

    @staticmethod
    def get_has_insufficient_balance(dialog_manager: DialogManager) -> bool:
        return dialog_manager.dialog_data.get("has_insufficient_balance", False)

    @staticmethod
    def clear(dialog_manager: DialogManager, *flags: str) -> None:
        for flag in flags:
            dialog_manager.dialog_data.pop(flag, None)

    def clear_reject_comment_error_flags(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_void_reject_comment",
            "has_small_reject_comment",
            "has_big_reject_comment"
        )

    def clear_regenerate_text_prompt_error_flags(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_void_regenerate_text_prompt",
            "has_small_regenerate_text_prompt",
            "has_big_regenerate_text_prompt",
            "has_invalid_content_type",
            "has_insufficient_balance"
        )

    def clear_edit_image_prompt_error_flags(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_void_edit_image_prompt",
            "has_small_edit_image_prompt",
            "has_big_edit_image_prompt",
            "has_invalid_content_type",
            "has_insufficient_balance"
        )

    def clear_publication_text_edit_error_flags(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_void_publication_text",
            "has_big_publication_text",
            "has_small_publication_text"
        )

    def clear_image_upload_error_flags(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_invalid_image_type",
            "has_big_image_size"
        )

    # ============= ДОПОЛНИТЕЛЬНЫЕ СЕТТЕРЫ =============

    @staticmethod
    def set_moderation_list(dialog_manager: DialogManager, moderation_list: list) -> None:
        dialog_manager.dialog_data["moderation_list"] = moderation_list

    @staticmethod
    def initialize_current_index_if_needed(dialog_manager: DialogManager) -> None:
        if "current_index" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["current_index"] = 0

    @staticmethod
    def set_original_publication(dialog_manager: DialogManager, publication_data: dict) -> None:
        dialog_manager.dialog_data["original_publication"] = publication_data

    @staticmethod
    def initialize_working_from_original(dialog_manager: DialogManager) -> None:
        if "working_publication" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["working_publication"] = dict(
                dialog_manager.dialog_data["original_publication"]
            )

    @staticmethod
    def set_post_links(dialog_manager: DialogManager, post_links: dict) -> None:
        dialog_manager.dialog_data["post_links"] = post_links

    @staticmethod
    def set_selected_social_networks(dialog_manager: DialogManager, networks: dict) -> None:
        dialog_manager.dialog_data["selected_social_networks"] = networks

    @staticmethod
    def toggle_social_network_selection(dialog_manager: DialogManager, network_id: str, is_checked: bool) -> None:
        if "selected_social_networks" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["selected_social_networks"] = {}
        dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

    @staticmethod
    def clear_selected_networks(dialog_manager: DialogManager) -> None:
        """Очистка выбранных социальных сетей"""
        dialog_manager.dialog_data.pop("selected_networks", None)

    # ============= МЕТОДЫ ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ ГЕТТЕРА =============

    @staticmethod
    def get_edit_text_window_data(dialog_manager: DialogManager) -> dict:
        working_pub = dialog_manager.dialog_data["working_publication"]
        return {
            "publication_text": working_pub["text"],
            "has_void_publication_text": dialog_manager.dialog_data.get("has_void_publication_text", False),
            "has_small_publication_text": dialog_manager.dialog_data.get("has_small_publication_text", False),
            "has_big_publication_text": dialog_manager.dialog_data.get("has_big_publication_text", False),
            "is_regenerating_text": dialog_manager.dialog_data.get("is_regenerating_text", False),
            "regenerate_text_prompt": dialog_manager.dialog_data.get("regenerate_text_prompt", ""),
            "has_regenerate_text_prompt": bool(dialog_manager.dialog_data.get("regenerate_text_prompt", "")),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
            "has_void_regenerate_text_prompt": dialog_manager.dialog_data.get("has_void_regenerate_text_prompt", False),
            "has_small_regenerate_text_prompt": dialog_manager.dialog_data.get("has_small_regenerate_text_prompt", False),
            "has_big_regenerate_text_prompt": dialog_manager.dialog_data.get("has_big_regenerate_text_prompt", False),
            "has_insufficient_balance": dialog_manager.dialog_data.get("has_insufficient_balance", False),
        }

    @staticmethod
    def get_image_menu_window_data(dialog_manager: DialogManager) -> dict:
        """Возвращает данные для меню редактирования изображения"""
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        return {
            "has_void_edit_image_prompt": dialog_manager.dialog_data.get("has_void_edit_image_prompt", False),
            "has_small_edit_image_prompt": dialog_manager.dialog_data.get("has_small_edit_image_prompt", False),
            "has_big_edit_image_prompt": dialog_manager.dialog_data.get("has_big_edit_image_prompt", False),
            "is_generating_image": dialog_manager.dialog_data.get("is_generating_image", False),
            "has_image": working_pub.get("has_image", False),
            "is_custom_image": working_pub.get("is_custom_image", False),
            "edit_image_prompt": dialog_manager.dialog_data.get("edit_image_prompt", ""),
            "has_edit_image_prompt": dialog_manager.dialog_data.get("edit_image_prompt", "") != "",
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
            "has_insufficient_balance": dialog_manager.dialog_data.get("has_insufficient_balance", False),
        }

    @staticmethod
    def get_upload_image_window_data(dialog_manager: DialogManager) -> dict:
        """Возвращает данные для окна загрузки изображения"""
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        return {
            "has_invalid_image_type": dialog_manager.dialog_data.get("has_invalid_image_type", False),
            "has_big_image_size": dialog_manager.dialog_data.get("has_big_image_size", False),
            "has_image_processing_error": dialog_manager.dialog_data.get("has_image_processing_error", False),
            "has_image": working_pub.get("has_image", False),
            "is_custom_image": working_pub.get("is_custom_image", False),
        }

    @staticmethod
    def get_reject_comment_window_data(dialog_manager: DialogManager) -> dict:
        """Возвращает данные для окна комментария отклонения"""
        return {
            "has_comment": bool(dialog_manager.dialog_data.get("reject_comment")),
            "reject_comment": dialog_manager.dialog_data.get("reject_comment", ""),
        }

    @staticmethod
    def get_text_too_long_alert_window_data(dialog_manager: DialogManager) -> dict:
        """Возвращает данные для предупреждения о длинном тексте"""
        working_pub = dialog_manager.dialog_data.get("working_publication", {})
        publication_text = working_pub.get("text", "")
        current_text_length = len(publication_text)
        max_length_with_image = 1024

        return {
            "current_text_length": current_text_length,
            "max_length_with_image": max_length_with_image,
            "publication_text": publication_text,
            "has_previous_text": bool(dialog_manager.dialog_data.get("previous_text")),
        }

    @staticmethod
    def get_publication_success_window_data(dialog_manager: DialogManager) -> dict:
        """Возвращает данные для окна успешной публикации"""
        post_links = dialog_manager.dialog_data.get("post_links", {})
        telegram_link = post_links.get("telegram")
        vkontakte_link = post_links.get("vkontakte")

        return {
            "has_post_links": bool(post_links),
            "has_telegram_link": bool(telegram_link),
            "has_vkontakte_link": bool(vkontakte_link),
            "telegram_link": telegram_link or "",
            "vkontakte_link": vkontakte_link or "",
        }

    # ============= МЕТОДЫ ДЛЯ COMBINE IMAGES =============

    @staticmethod
    def get_combine_images_list(dialog_manager: DialogManager) -> list[str]:
        return dialog_manager.dialog_data.get("combine_images_list", [])

    @staticmethod
    def get_combine_current_index(dialog_manager: DialogManager) -> int:
        return dialog_manager.dialog_data.get("combine_current_index", 0)

    @staticmethod
    def get_combine_image_prompt(dialog_manager: DialogManager) -> str:
        return dialog_manager.dialog_data.get("combine_image_prompt", "")

    @staticmethod
    def get_combined_image_result_url(dialog_manager: DialogManager) -> str | None:
        return dialog_manager.dialog_data.get("combined_image_result_url")

    @staticmethod
    def set_combine_images_list(dialog_manager: DialogManager, images: list[str], index: int = 0) -> None:
        dialog_manager.dialog_data["combine_images_list"] = images
        dialog_manager.dialog_data["combine_current_index"] = index

    @staticmethod
    def set_combine_current_index(dialog_manager: DialogManager, index: int) -> None:
        dialog_manager.dialog_data["combine_current_index"] = index

    @staticmethod
    def set_combine_image_prompt(dialog_manager: DialogManager, prompt: str) -> None:
        dialog_manager.dialog_data["combine_image_prompt"] = prompt

    @staticmethod
    def set_combined_image_result_url(dialog_manager: DialogManager, url: str) -> None:
        dialog_manager.dialog_data["combined_image_result_url"] = url

    @staticmethod
    def set_is_combining_images(dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["is_combining_images"] = value

    @staticmethod
    def get_is_combining_images(dialog_manager: DialogManager) -> bool:
        return dialog_manager.dialog_data.get("is_combining_images", False)

    @staticmethod
    def clear_combine_image_prompt_error_flags(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("has_small_combine_image_prompt", None)
        dialog_manager.dialog_data.pop("has_big_combine_image_prompt", None)
        dialog_manager.dialog_data.pop("has_invalid_content_type", None)
        dialog_manager.dialog_data.pop("has_insufficient_balance", None)

    @staticmethod
    def clear_combine_image_upload_error_flags(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("has_invalid_combine_image_type", None)
        dialog_manager.dialog_data.pop("has_big_combine_image_size", None)
        dialog_manager.dialog_data.pop("combine_images_limit_reached", None)

    @staticmethod
    def clear_combine_data(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("combine_images_list", None)
        dialog_manager.dialog_data.pop("combine_current_index", None)
        dialog_manager.dialog_data.pop("combine_image_prompt", None)
        dialog_manager.dialog_data.pop("combined_image_result_url", None)

    # ============= МЕТОДЫ ДЛЯ NEW IMAGE CONFIRM =============

    @staticmethod
    def get_generated_images_url(dialog_manager: DialogManager) -> list[str] | None:
        return dialog_manager.dialog_data.get("generated_images_url")

    @staticmethod
    def set_generated_images_url(dialog_manager: DialogManager, urls: list[str]) -> None:
        dialog_manager.dialog_data["generated_images_url"] = urls

    @staticmethod
    def get_original_image_backup(dialog_manager: DialogManager) -> dict | None:
        return dialog_manager.dialog_data.get("original_image_backup")

    @staticmethod
    def get_previous_generation_backup(dialog_manager: DialogManager) -> dict | None:
        return dialog_manager.dialog_data.get("previous_generation_backup")

    @staticmethod
    def set_original_image_backup(dialog_manager: DialogManager, backup_dict: dict | None) -> None:
        if backup_dict is None:
            dialog_manager.dialog_data.pop("original_image_backup", None)
        else:
            dialog_manager.dialog_data["original_image_backup"] = backup_dict

    @staticmethod
    def set_previous_generation_backup(dialog_manager: DialogManager, backup_dict: dict | None) -> None:
        if backup_dict is None:
            dialog_manager.dialog_data.pop("previous_generation_backup", None)
        else:
            dialog_manager.dialog_data["previous_generation_backup"] = backup_dict

    @staticmethod
    def get_showing_old_image(dialog_manager: DialogManager) -> bool:
        return dialog_manager.dialog_data.get("showing_old_image", False)

    @staticmethod
    def set_showing_old_image(dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["showing_old_image"] = value

    @staticmethod
    def get_edit_image_prompt(dialog_manager: DialogManager) -> str:
        return dialog_manager.dialog_data.get("edit_image_prompt", "")

    @staticmethod
    def get_is_applying_edits(dialog_manager: DialogManager) -> bool:
        return dialog_manager.dialog_data.get("is_applying_edits", False)

    @staticmethod
    def set_is_applying_edits(dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["is_applying_edits"] = value

    @staticmethod
    def clear_new_image_confirm_error_flags(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("has_small_edit_image_prompt", None)
        dialog_manager.dialog_data.pop("has_big_edit_image_prompt", None)
        dialog_manager.dialog_data.pop("has_invalid_content_type", None)
        dialog_manager.dialog_data.pop("has_insufficient_balance", None)

    @staticmethod
    def clear_new_image_confirm_data(dialog_manager: DialogManager) -> None:
        """Очищает данные текущей итерации генерации, но сохраняет original_image_backup"""
        dialog_manager.dialog_data.pop("generated_images_url", None)
        dialog_manager.dialog_data.pop("combined_image_result_url", None)
        dialog_manager.dialog_data.pop("previous_generation_backup", None)
        dialog_manager.dialog_data.pop("edit_image_prompt", None)
        dialog_manager.dialog_data.pop("combine_images_list", None)
        dialog_manager.dialog_data.pop("combine_current_index", None)
        dialog_manager.dialog_data.pop("combine_image_prompt", None)
        dialog_manager.dialog_data.pop("showing_old_image", None)

    @staticmethod
    def clear_temporary_image_data(dialog_manager: DialogManager) -> None:
        """Полная очистка всех временных данных изображений, включая original_image_backup"""
        dialog_manager.dialog_data.pop("generated_images_url", None)
        dialog_manager.dialog_data.pop("combined_image_result_url", None)
        dialog_manager.dialog_data.pop("previous_generation_backup", None)
        dialog_manager.dialog_data.pop("original_image_backup", None)
        dialog_manager.dialog_data.pop("edit_image_prompt", None)
        dialog_manager.dialog_data.pop("combine_images_list", None)
        dialog_manager.dialog_data.pop("combine_current_index", None)
        dialog_manager.dialog_data.pop("combine_image_prompt", None)
        dialog_manager.dialog_data.pop("showing_old_image", None)

    # ============= МЕТОДЫ ДЛЯ РЕФЕРЕНСНОЙ ГЕНЕРАЦИИ =============

    @staticmethod
    def get_reference_generation_image_file_id(dialog_manager: DialogManager) -> str | None:
        return dialog_manager.dialog_data.get("reference_generation_image_file_id")

    @staticmethod
    def set_reference_generation_image_file_id(dialog_manager: DialogManager, file_id: str) -> None:
        dialog_manager.dialog_data["reference_generation_image_file_id"] = file_id

    @staticmethod
    def get_has_reference_generation_image(dialog_manager: DialogManager) -> bool:
        return bool(dialog_manager.dialog_data.get("reference_generation_image_file_id"))

    @staticmethod
    def get_reference_generation_image_prompt(dialog_manager: DialogManager) -> str:
        return dialog_manager.dialog_data.get("reference_generation_image_prompt", "")

    @staticmethod
    def set_reference_generation_image_prompt(dialog_manager: DialogManager, prompt: str) -> None:
        dialog_manager.dialog_data["reference_generation_image_prompt"] = prompt

    @staticmethod
    def remove_reference_generation_image(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("reference_generation_image_file_id", None)

    @staticmethod
    def clear_reference_generation_image_data(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("reference_generation_image_file_id", None)
        dialog_manager.dialog_data.pop("reference_generation_image_prompt", None)

    @staticmethod
    def clear_reference_generation_image_errors(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("has_invalid_reference_generation_image_type", None)
        dialog_manager.dialog_data.pop("has_big_reference_generation_image_size", None)

    @staticmethod
    def clear_reference_generation_image_prompt_errors(dialog_manager: DialogManager) -> None:
        dialog_manager.dialog_data.pop("has_void_reference_generation_image_prompt", None)
        dialog_manager.dialog_data.pop("has_small_reference_generation_image_prompt", None)
        dialog_manager.dialog_data.pop("has_big_reference_generation_image_prompt", None)
        dialog_manager.dialog_data.pop("has_invalid_content_type", None)
        dialog_manager.dialog_data.pop("has_insufficient_balance", None)

    @staticmethod
    def get_reference_generation_image_window_data(dialog_manager: DialogManager) -> dict:
        """Возвращает данные для окна референсной генерации изображения"""
        return {
            "is_generating_image": dialog_manager.dialog_data.get("is_generating_image", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            "has_void_reference_generation_image_prompt": dialog_manager.dialog_data.get(
                "has_void_reference_generation_image_prompt", False),
            "has_small_reference_generation_image_prompt": dialog_manager.dialog_data.get(
                "has_small_reference_generation_image_prompt", False),
            "has_big_reference_generation_image_prompt": dialog_manager.dialog_data.get(
                "has_big_reference_generation_image_prompt", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
            "has_invalid_reference_generation_image_type": dialog_manager.dialog_data.get(
                "has_invalid_reference_generation_image_type", False),
            "has_big_reference_generation_image_size": dialog_manager.dialog_data.get(
                "has_big_reference_generation_image_size", False),
            "has_insufficient_balance": dialog_manager.dialog_data.get("has_insufficient_balance", False),
        }

    @staticmethod
    def get_reference_generation_image_upload_window_data(dialog_manager: DialogManager) -> dict:
        """Возвращает данные для окна загрузки референсного изображения"""
        return {
            "has_invalid_reference_generation_image_type": dialog_manager.dialog_data.get(
                "has_invalid_reference_generation_image_type", False),
            "has_big_reference_generation_image_size": dialog_manager.dialog_data.get(
                "has_big_reference_generation_image_size", False),
        }

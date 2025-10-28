from aiogram_dialog import DialogManager


class DialogDataHelper:
    def __init__(self, logger):
        self.logger = logger

    def get_generate_text_prompt_input_data(self, dialog_manager: DialogManager) -> dict:
        return {
            "category_name": dialog_manager.dialog_data.get("category_name", ""),
            "category_hint": dialog_manager.dialog_data.get("category_hint", ""),
            "generate_text_prompt": dialog_manager.dialog_data.get("generate_text_prompt", ""),
            "has_generate_text_prompt": dialog_manager.dialog_data.get("has_generate_text_prompt", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            # text_prompt input error flags
            "has_void_generate_text_prompt": dialog_manager.dialog_data.get("has_void_generate_text_prompt", False),
            "has_small_generate_text_prompt": dialog_manager.dialog_data.get("has_small_generate_text_prompt", False),
            "has_big_generate_text_prompt": dialog_manager.dialog_data.get("has_big_generate_text_prompt", False),
            # Voice input error flags
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
            "has_long_voice_duration": dialog_manager.dialog_data.get("has_long_voice_duration", False),
        }

    def get_edit_publication_text_data(self, dialog_manager: DialogManager) -> dict:
        return {
            "publication_text": dialog_manager.dialog_data.get("publication_text", ""),
            "regenerate_text_prompt": dialog_manager.dialog_data.get("regenerate_text_prompt", ""),
            "has_regenerate_text_prompt": bool(dialog_manager.dialog_data.get("has_regenerate_text_prompt", "")),
            "is_regenerating_text": dialog_manager.dialog_data.get("is_regenerating_text", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            # Error flags for text editing
            "has_void_publication_text": dialog_manager.dialog_data.get("has_void_publication_text", False),
            "has_small_publication_text": dialog_manager.dialog_data.get("has_small_publication_text", False),
            "has_big_publication_text": dialog_manager.dialog_data.get("has_big_publication_text", False),
            # Error flags for regenerate prompt
            "has_void_regenerate_text_prompt": dialog_manager.dialog_data.get("has_void_regenerate_text_prompt", False),
            "has_small_regenerate_text_prompt": dialog_manager.dialog_data.get("has_small_regenerate_text_prompt", False),
            "has_big_regenerate_text_prompt": dialog_manager.dialog_data.get("has_big_regenerate_text_prompt", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
        }

    def get_image_menu_flags(self, dialog_manager: DialogManager) -> dict:
        return {
            "is_custom_image": dialog_manager.dialog_data.get("is_custom_image", False),
            "is_generating_image": dialog_manager.dialog_data.get("is_generating_image", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            # Error flags
            "has_void_edit_image_prompt": dialog_manager.dialog_data.get("has_void_edit_image_prompt", False),
            "has_small_edit_image_prompt": dialog_manager.dialog_data.get("has_small_edit_image_prompt", False),
            "has_big_edit_image_prompt": dialog_manager.dialog_data.get("has_big_edit_image_prompt", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
        }

    def get_upload_imagedialog_data_helper(self, dialog_manager: DialogManager) -> dict:
        return {
            "has_invalid_image_type": dialog_manager.dialog_data.get("has_invalid_image_type", False),
            "has_big_image_size": dialog_manager.dialog_data.get("has_big_image_size", False),
            "has_image_processing_error": dialog_manager.dialog_data.get("has_image_processing_error", False),
        }

    def get_text_too_long_alert_data(self, dialog_manager: DialogManager) -> dict:
        publication_text = dialog_manager.dialog_data.get("publication_text", "")
        current_text_length = len(publication_text)
        max_length_with_image = 1024

        return {
            "current_text_length": current_text_length,
            "max_length_with_image": max_length_with_image,
            "publication_text": publication_text,
        }

    def get_publication_success_data(self, dialog_manager: DialogManager) -> dict:
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

    def get_combine_images_choice_data(self, dialog_manager: DialogManager) -> dict:
        has_image = dialog_manager.dialog_data.get("has_image", False)
        return {
            "has_image": has_image,
        }

    def get_combine_images_upload_flags(self, dialog_manager: DialogManager) -> dict:
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

    def get_combine_images_prompt_flags(self, dialog_manager: DialogManager) -> dict:
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
        }

    def get_new_image_confirm_flags(self, dialog_manager: DialogManager) -> dict:
        return {
            "is_applying_edits": dialog_manager.dialog_data.get("is_applying_edits", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            "has_image_edit_prompt": bool(dialog_manager.dialog_data.get("edit_image_prompt")),
            "edit_image_prompt": dialog_manager.dialog_data.get("edit_image_prompt", ""),
            # Error flags
            "has_small_edit_prompt": dialog_manager.dialog_data.get("has_small_edit_prompt", False),
            "has_big_edit_prompt": dialog_manager.dialog_data.get("has_big_edit_prompt", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
        }

    # ============= ГЕТТЕРЫ ДЛЯ ЧТЕНИЯ ДАННЫХ =============

    # Основные данные
    def get_category_id(self, dialog_manager: DialogManager) -> int | None:
        return dialog_manager.dialog_data.get("category_id")

    def get_category_name(self, dialog_manager: DialogManager) -> str:
        return dialog_manager.dialog_data.get("category_name", "")

    def get_generate_text_prompt(self, dialog_manager: DialogManager) -> str:
        return dialog_manager.dialog_data.get("generate_text_prompt", "")

    def get_publication_text(self, dialog_manager: DialogManager) -> str:
        return dialog_manager.dialog_data.get("publication_text", "")

    # Данные об изображениях
    def get_has_image(self, dialog_manager: DialogManager) -> bool:
        return dialog_manager.dialog_data.get("has_image", False)

    def get_is_custom_image(self, dialog_manager: DialogManager) -> bool:
        return dialog_manager.dialog_data.get("is_custom_image", False)

    def get_custom_image_file_id(self, dialog_manager: DialogManager) -> str | None:
        return dialog_manager.dialog_data.get("custom_image_file_id")

    def get_publication_images_url(self, dialog_manager: DialogManager) -> list[str]:
        return dialog_manager.dialog_data.get("publication_images_url", [])

    def get_current_image_index(self, dialog_manager: DialogManager) -> int:
        return dialog_manager.dialog_data.get("current_image_index", 0)

    def get_generated_images_url(self, dialog_manager: DialogManager) -> list[str] | None:
        return dialog_manager.dialog_data.get("generated_images_url")

    def get_combined_image_url(self, dialog_manager: DialogManager) -> str | None:
        return dialog_manager.dialog_data.get("combined_image_url")

    # Данные для combine
    def get_combine_images_list(self, dialog_manager: DialogManager) -> list[str]:
        return dialog_manager.dialog_data.get("combine_images_list", [])

    def get_combine_current_index(self, dialog_manager: DialogManager) -> int:
        return dialog_manager.dialog_data.get("combine_current_index", 0)

    # Резервные копии
    def get_old_image_backup(self, dialog_manager: DialogManager) -> dict | None:
        return dialog_manager.dialog_data.get("old_image_backup")

    def get_old_generated_image_backup(self, dialog_manager: DialogManager) -> dict | None:
        return dialog_manager.dialog_data.get("old_generated_image_backup")

    def get_showing_old_image(self, dialog_manager: DialogManager) -> bool:
        return dialog_manager.dialog_data.get("showing_old_image", False)

    # Соцсети и публикация
    def get_selected_social_networks(self, dialog_manager: DialogManager) -> dict:
        return dialog_manager.dialog_data.get("selected_social_networks", {})

    def get_expected_length(self, dialog_manager: DialogManager) -> int | None:
        return dialog_manager.dialog_data.get("expected_length")

    # ============= СЕТТЕРЫ ДЛЯ ЗАПИСИ ДАННЫХ =============

    # Категория
    def set_category_data(
            self,
            dialog_manager: DialogManager,
            category_id: int,
            category_name: str,
            category_hint: str
    ) -> None:
        dialog_manager.dialog_data["category_id"] = category_id
        dialog_manager.dialog_data["category_name"] = category_name
        dialog_manager.dialog_data["category_hint"] = category_hint

    # Текст и промпты
    def set_generate_text_prompt(self, dialog_manager: DialogManager, text: str, has_text_prompt: bool = True) -> None:
        dialog_manager.dialog_data["generate_text_prompt"] = text
        dialog_manager.dialog_data["has_generate_text_prompt"] = has_text_prompt

    def set_publication_text(self, dialog_manager: DialogManager, text: str) -> None:
        dialog_manager.dialog_data["publication_text"] = text

    def set_regenerate_text_prompt(self, dialog_manager: DialogManager, prompt: str, has_prompt: bool = True) -> None:
        dialog_manager.dialog_data["regenerate_text_prompt"] = prompt
        dialog_manager.dialog_data["has_regenerate_text_prompt"] = has_prompt

    def set_edit_image_prompt(self, dialog_manager: DialogManager, prompt: str) -> None:
        dialog_manager.dialog_data["edit_image_prompt"] = prompt

    def set_combine_image_prompt(self, dialog_manager: DialogManager, prompt: str) -> None:
        dialog_manager.dialog_data["combine_image_prompt"] = prompt

    # Изображения - основные
    def set_has_image(self, dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["has_image"] = value

    def set_is_custom_image(self, dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["is_custom_image"] = value

    def set_custom_image_file_id(self, dialog_manager: DialogManager, file_id: str) -> None:
        dialog_manager.dialog_data["custom_image_file_id"] = file_id

    def set_publication_images_url(self, dialog_manager: DialogManager, urls: list[str], index: int = 0) -> None:
        dialog_manager.dialog_data["publication_images_url"] = urls
        dialog_manager.dialog_data["current_image_index"] = index

    def set_new_publication_image(self, dialog_manager: DialogManager, urls: list[str], index: int = 0) -> None:
        self.set_publication_images_url(dialog_manager, urls, 0)
        self.set_has_image(dialog_manager, True)
        self.set_is_custom_image(dialog_manager, False)

    def set_new_custom_image(self, dialog_manager: DialogManager, file_id: str) -> None:
        self.set_custom_image_file_id(dialog_manager, file_id)
        self.set_has_image(dialog_manager, True)
        self.set_is_custom_image(dialog_manager, True)

        self.remove_field(dialog_manager, "publication_images_url")
        self.remove_field(dialog_manager, "current_image_index")

    def set_current_image_index(self, dialog_manager: DialogManager, index: int) -> None:
        dialog_manager.dialog_data["current_image_index"] = index

    # Изображения - генерация и комбинирование
    def set_generated_images_url(self, dialog_manager: DialogManager, urls: list[str]) -> None:
        dialog_manager.dialog_data["generated_images_url"] = urls

    def set_combine_image_url(self, dialog_manager: DialogManager, url: str) -> None:
        dialog_manager.dialog_data["combined_image_url"] = url

    def set_combine_images_list(self, dialog_manager: DialogManager, images: list[str], index: int = 0) -> None:
        dialog_manager.dialog_data["combine_images_list"] = images
        dialog_manager.dialog_data["combine_current_index"] = index

    def set_combine_current_index(self, dialog_manager: DialogManager, index: int) -> None:
        dialog_manager.dialog_data["combine_current_index"] = index

    def set_is_generating_image(self, dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["is_generating_image"] = value

    def set_is_regenerating_text(self, dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["is_regenerating_text"] = value

    def set_is_combining_images(self, dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["is_combining_images"] = value

    def set_is_applying_edits(self, dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["is_applying_edits"] = value

    # Резервные копии
    def set_old_image_backup(self, dialog_manager: DialogManager, backup_dict: dict | None) -> None:
        if backup_dict is None:
            dialog_manager.dialog_data.pop("old_image_backup", None)
        else:
            dialog_manager.dialog_data["old_image_backup"] = backup_dict

    def set_old_generated_image_backup(self, dialog_manager: DialogManager, backup_dict: dict | None) -> None:
        if backup_dict is None:
            dialog_manager.dialog_data.pop("old_generated_image_backup", None)
        else:
            dialog_manager.dialog_data["old_generated_image_backup"] = backup_dict

    def set_showing_old_image(self, dialog_manager: DialogManager, value: bool) -> None:
        dialog_manager.dialog_data["showing_old_image"] = value

    # Соцсети и публикация
    def set_selected_social_networks(self, dialog_manager: DialogManager, networks: dict) -> None:
        dialog_manager.dialog_data["selected_social_networks"] = networks

    def set_post_links(self, dialog_manager: DialogManager, links: dict) -> None:
        dialog_manager.dialog_data["post_links"] = links

    def set_expected_length(self, dialog_manager: DialogManager, length: int) -> None:
        dialog_manager.dialog_data["expected_length"] = length

    def toggle_social_network(self, dialog_manager: DialogManager, network_id: str, is_checked: bool) -> None:
        if "selected_social_networks" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["selected_social_networks"] = {}
        dialog_manager.dialog_data["selected_social_networks"][network_id] = is_checked

    # ============= МЕТОДЫ ОЧИСТКИ ДАННЫХ =============

    # ============= МЕТОДЫ ДЛЯ УСТАНОВКИ ФЛАГОВ ОШИБОК =============
    def clear(self, dialog_manager: DialogManager, *flag_names: str) -> None:
        for flag_name in flag_names:
            dialog_manager.dialog_data.pop(flag_name, None)

    def clear_generate_text_prompt_input(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_void_generate_text_prompt",
            "has_small_generate_text_prompt",
            "has_big_generate_text_prompt",
            "has_invalid_content_type"
        )

    def clear_regenerate_text_prompt(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_void_regenerate_text_prompt",
            "has_small_regenerate_text_prompt",
            "has_big_regenerate_text_prompt",
            "has_invalid_content_type"
        )

    def clear_edit_image_prompt(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_void_edit_image_prompt",
            "has_small_edit_image_prompt",
            "has_big_edit_image_prompt",
            "has_invalid_content_type",
            "has_empty_voice_text"
        )

    def clear_text_edit(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_void_publication_text",
            "has_big_publication_text",
            "has_small_publication_text"
        )

    def clear_image_upload(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_invalid_image_type",
            "has_big_image_size"
        )

    def clear_combine_image_prompt_error_flags(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_small_combine_image_prompt",
            "has_big_combine_image_prompt",
            "has_invalid_content_type"
        )

    def clear_combine_image_upload(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_invalid_combine_image_type",
            "has_big_combine_image_size",
            "combine_images_limit_reached"
        )

    def clear_new_image_confirm(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_small_edit_image_prompt",
            "has_big_edit_image_prompt",
            "has_invalid_content_type"
        )

    def set_error_flag(self, dialog_manager: DialogManager, flag_name: str, value: bool = True) -> None:
        """Универсальный метод для установки флага ошибки"""
        dialog_manager.dialog_data[flag_name] = value

    def remove_field(self, dialog_manager: DialogManager, field_name: str) -> None:
        """Удаление конкретного поля из dialog_data"""
        dialog_manager.dialog_data.pop(field_name, None)

    def clear_all_image_data(self, dialog_manager: DialogManager) -> None:
        """Очистка всех данных об изображениях"""
        self.clear(
            dialog_manager,
            "has_image",
            "publication_images_url",
            "custom_image_file_id",
            "is_custom_image",
            "current_image_index"
        )

    def clear_edit_image_prompt_error_flags(self, dialog_manager: DialogManager):
        self.clear(
            dialog_manager,
            "has_small_edit_image_prompt",
            "has_big_edit_image_prompt",
            "has_invalid_content_type"
        )

    def clear_temporary_image_data(self, dialog_manager: DialogManager) -> None:
        """Очистка временных данных об изображениях"""
        self.clear(
            dialog_manager,
            "generated_images_url",
            "combined_image_url",
            "old_generated_image_backup",
            "old_image_backup",
            "edit_image_prompt",
            "combine_images_list",
            "combine_current_index",
            "combine_image_prompt",
            "showing_old_image"
        )

    def clear_combine_image_data(self, dialog_manager: DialogManager) -> None:
        """Очистка данных комбинирования изображений"""
        self.clear(
            dialog_manager,
            "combine_images_list",
            "combine_image_current_index",
            "combine_image_prompt"
        )

    def clear_reference_generation_image_data(self, dialog_manager: DialogManager) -> None:
        """Очистка данных кастомной генерации изображений"""
        self.clear(
            dialog_manager,
            "reference_generation_image_prompt",
            "reference_generation_image_file_id",
            "has_reference_generation_image",
            "has_reference_generation_image_prompt",
            "has_void_reference_generation_image_prompt",
            "has_small_reference_generation_image_prompt",
            "has_big_reference_generation_image_prompt",
            "has_invalid_reference_generation_image_type",
            "has_big_reference_generation_image_size",
            "is_generating_image"
        )

    def get_reference_generation_image_file_id(self, dialog_manager: DialogManager) -> str | None:
        return dialog_manager.dialog_data.get("reference_generation_image_file_id")

    def get_has_reference_generation_image(self, dialog_manager: DialogManager) -> bool:
        return dialog_manager.dialog_data.get("has_reference_generation_image", False)

    def set_reference_generation_image_prompt(self, dialog_manager: DialogManager, prompt: str) -> None:
        dialog_manager.dialog_data["reference_generation_image_prompt"] = prompt

    def set_reference_generation_image_file_id(self, dialog_manager: DialogManager, file_id: str) -> None:
        dialog_manager.dialog_data["reference_generation_image_file_id"] = file_id
        dialog_manager.dialog_data["has_reference_generation_image"] = True

    def remove_reference_generation_image(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "reference_generation_image_file_id",
            "has_reference_generation_image"
        )

    def clear_reference_generation_image_prompt_errors(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_void_reference_generation_image_prompt",
            "has_small_reference_generation_image_prompt",
            "has_big_reference_generation_image_prompt",
            "has_invalid_content_type",
            "voice_transcribe"
        )

    def clear_reference_generation_image_errors(self, dialog_manager: DialogManager) -> None:
        self.clear(
            dialog_manager,
            "has_invalid_reference_generation_image_type",
            "has_big_reference_generation_image_size"
        )

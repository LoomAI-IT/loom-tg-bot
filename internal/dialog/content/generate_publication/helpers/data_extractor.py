from aiogram_dialog import DialogManager


class DataExtractor:
    def __init__(self, logger):
        self.logger = logger

    def get_input_text_data(self, dialog_manager: DialogManager) -> dict:
        return {
            "category_name": dialog_manager.dialog_data.get("category_name", ""),
            "category_hint": dialog_manager.dialog_data.get("category_hint", ""),
            "input_text": dialog_manager.dialog_data.get("input_text", ""),
            "has_input_text": dialog_manager.dialog_data.get("has_input_text", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            # Text input error flags
            "has_void_input_text": dialog_manager.dialog_data.get("has_void_input_text", False),
            "has_small_input_text": dialog_manager.dialog_data.get("has_small_input_text", False),
            "has_big_input_text": dialog_manager.dialog_data.get("has_big_input_text", False),
            # Voice input error flags
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
            "has_long_voice_duration": dialog_manager.dialog_data.get("has_long_voice_duration", False),
        }

    def get_edit_text_data(self, dialog_manager: DialogManager) -> dict:
        return {
            "publication_text": dialog_manager.dialog_data.get("publication_text", ""),
            "regenerate_prompt": dialog_manager.dialog_data.get("regenerate_prompt", ""),
            "has_regenerate_prompt": bool(dialog_manager.dialog_data.get("regenerate_prompt", "")),
            "is_regenerating_text": dialog_manager.dialog_data.get("is_regenerating_text", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            # Error flags for text editing
            "has_void_text": dialog_manager.dialog_data.get("has_void_text", False),
            "has_small_text": dialog_manager.dialog_data.get("has_small_text", False),
            "has_big_text": dialog_manager.dialog_data.get("has_big_text", False),
            # Error flags for regenerate prompt
            "has_void_regenerate_prompt": dialog_manager.dialog_data.get("has_void_regenerate_prompt", False),
            "has_small_regenerate_prompt": dialog_manager.dialog_data.get("has_small_regenerate_prompt", False),
            "has_big_regenerate_prompt": dialog_manager.dialog_data.get("has_big_regenerate_prompt", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
        }

    def get_image_menu_flags(self, dialog_manager: DialogManager) -> dict:
        return {
            "is_custom_image": dialog_manager.dialog_data.get("is_custom_image", False),
            "has_image_prompt": dialog_manager.dialog_data.get("image_prompt", "") != "",
            "image_prompt": dialog_manager.dialog_data.get("image_prompt", ""),
            "is_generating_image": dialog_manager.dialog_data.get("is_generating_image", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            # Error flags
            "has_void_image_prompt": dialog_manager.dialog_data.get("has_void_image_prompt", False),
            "has_small_image_prompt": dialog_manager.dialog_data.get("has_small_image_prompt", False),
            "has_big_image_prompt": dialog_manager.dialog_data.get("has_big_image_prompt", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
        }

    def get_upload_image_error_flags(self, dialog_manager: DialogManager) -> dict:
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
        has_current_image = dialog_manager.dialog_data.get("has_image", False)
        return {
            "has_current_image": has_current_image,
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
            "has_combine_prompt": bool(dialog_manager.dialog_data.get("combine_prompt")),
            "combine_prompt": dialog_manager.dialog_data.get("combine_prompt", ""),
            # Image data for navigation
            "has_combine_images": combine_images_count > 0,
            "combine_images_count": combine_images_count,
            "has_multiple_combine_images": combine_images_count > 1,
            # Error flags
            "has_small_combine_prompt": dialog_manager.dialog_data.get("has_small_combine_prompt", False),
            "has_big_combine_prompt": dialog_manager.dialog_data.get("has_big_combine_prompt", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
        }

    def get_new_image_confirm_flags(self, dialog_manager: DialogManager) -> dict:
        return {
            "is_applying_edits": dialog_manager.dialog_data.get("is_applying_edits", False),
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),
            "has_image_edit_prompt": bool(dialog_manager.dialog_data.get("image_edit_prompt")),
            "image_edit_prompt": dialog_manager.dialog_data.get("image_edit_prompt", ""),
            # Error flags
            "has_small_edit_prompt": dialog_manager.dialog_data.get("has_small_edit_prompt", False),
            "has_big_edit_prompt": dialog_manager.dialog_data.get("has_big_edit_prompt", False),
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
        }

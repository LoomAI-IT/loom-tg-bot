from aiogram_dialog import DialogManager


class _ErrorFlagsManager:
    """Управление флагами ошибок в dialog_data"""

    @staticmethod
    def clear_error_flags(dialog_manager: DialogManager, *flags: str) -> None:
        """Очищает указанные флаги ошибок из dialog_data"""
        for flag in flags:
            dialog_manager.dialog_data.pop(flag, None)

    def clear_reject_comment_error_flags(self, dialog_manager: DialogManager) -> None:
        """Очищает флаги ошибок для комментария отклонения"""
        self.clear_error_flags(
            dialog_manager,
            "has_void_reject_comment",
            "has_small_reject_comment",
            "has_big_reject_comment"
        )

    def clear_regenerate_prompt_error_flags(self, dialog_manager: DialogManager) -> None:
        """Очищает флаги ошибок для промпта регенерации"""
        self.clear_error_flags(
            dialog_manager,
            "has_void_regenerate_prompt",
            "has_small_regenerate_prompt",
            "has_big_regenerate_prompt",
            "has_invalid_content_type"
        )

    def clear_image_prompt_error_flags(self, dialog_manager: DialogManager) -> None:
        """Очищает флаги ошибок для промпта изображения"""
        self.clear_error_flags(
            dialog_manager,
            "has_void_image_prompt",
            "has_small_image_prompt",
            "has_big_image_prompt",
            "has_invalid_content_type"
        )

    def clear_text_edit_error_flags(self, dialog_manager: DialogManager) -> None:
        """Очищает флаги ошибок для редактирования текста"""
        self.clear_error_flags(
            dialog_manager,
            "has_void_text",
            "has_big_text",
            "has_small_text"
        )

    def clear_image_upload_error_flags(self, dialog_manager: DialogManager) -> None:
        """Очищает флаги ошибок для загрузки изображения"""
        self.clear_error_flags(
            dialog_manager,
            "has_invalid_image_type",
            "has_big_image_size"
        )

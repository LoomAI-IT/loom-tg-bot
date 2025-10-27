from aiogram_dialog import DialogManager


class _StateRestorer:
    def __init__(self, logger, image_manager):
        self.logger = logger
        self._image_manager = image_manager

    def restore_previous_state(self, dialog_manager: DialogManager) -> None:
        # Восстанавливаем предыдущий текст
        previous_text = dialog_manager.dialog_data.get("previous_text")
        if previous_text:
            dialog_manager.dialog_data["working_publication"]["text"] = previous_text
            self.logger.info("Текст восстановлен из предыдущего состояния")

        # Восстанавливаем состояние изображения если оно было изменено
        if "previous_has_image" in dialog_manager.dialog_data:
            prev_has_image = dialog_manager.dialog_data["previous_has_image"]
            current_has_image = dialog_manager.dialog_data["working_publication"].get("has_image", False)

            # Если изображение было добавлено (и его не было раньше), удаляем его
            if not prev_has_image and current_has_image:
                self.logger.info("Удаление добавленного изображения")
                self._image_manager.clear_image_data(dialog_manager=dialog_manager)

        # Очищаем сохраненные данные
        dialog_manager.dialog_data.pop("previous_text", None)
        dialog_manager.dialog_data.pop("previous_has_image", None)

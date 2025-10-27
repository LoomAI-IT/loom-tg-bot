from aiogram_dialog import DialogManager


class StateRestorer:
    def __init__(self, logger, image_manager):
        self.logger = logger
        self._image_manager = image_manager

    def save_state_before_modification(
            self,
            dialog_manager: DialogManager,
            include_image: bool = True
    ) -> None:
        """
        Сохраняет текущее состояние перед модификацией.
        Сохраняет previous_text и опционально previous_has_image.
        """
        working_pub = dialog_manager.dialog_data.get("working_publication", {})

        # Сохраняем текущий текст
        current_text = working_pub.get("text")
        if current_text:
            dialog_manager.dialog_data["previous_text"] = current_text
            self.logger.info("Сохранено предыдущее состояние текста")

        # Сохраняем состояние изображения если требуется
        if include_image:
            has_image = working_pub.get("has_image", False)
            dialog_manager.dialog_data["previous_has_image"] = has_image
            self.logger.info(f"Сохранено предыдущее состояние изображения: {has_image}")

    def restore_previous_state(self, dialog_manager: DialogManager) -> None:
        """Восстанавливает сохраненное состояние"""
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

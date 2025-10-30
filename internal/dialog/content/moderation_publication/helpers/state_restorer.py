from aiogram_dialog import DialogManager

from internal.dialog.content.moderation_publication.helpers.dialog_data_helper import DialogDataHelper


class StateRestorer:
    def __init__(self, logger, image_manager):
        self.logger = logger
        self.image_manager = image_manager
        self.dialog_data_helper = DialogDataHelper()

    def save_state_before_modification(
            self,
            dialog_manager: DialogManager,
            include_image: bool = True
    ) -> None:
        working_pub = self.dialog_data_helper.get_working_publication_safe(dialog_manager)

        # Сохраняем текущий текст
        current_text = working_pub.get("text")
        if current_text:
            self.dialog_data_helper.set_previous_text(dialog_manager, current_text)
            self.logger.info("Сохранено предыдущее состояние текста")

        # Сохраняем состояние изображения если требуется
        if include_image:
            has_image = self.dialog_data_helper.get_working_image_has_image(dialog_manager)
            self.dialog_data_helper.set_previous_has_image(dialog_manager, has_image)
            self.logger.info(f"Сохранено предыдущее состояние изображения: {has_image}")

    def restore_previous_state(self, dialog_manager: DialogManager) -> None:
        # Восстанавливаем предыдущий текст
        previous_text = self.dialog_data_helper.get_previous_text(dialog_manager)
        if previous_text:
            self.dialog_data_helper.update_working_text(dialog_manager, previous_text)
            self.logger.info("Текст восстановлен из предыдущего состояния")

        # Восстанавливаем состояние изображения если оно было изменено
        if self.dialog_data_helper.has_previous_has_image(dialog_manager):
            prev_has_image = self.dialog_data_helper.get_previous_has_image(dialog_manager)
            current_has_image = self.dialog_data_helper.get_working_image_has_image(dialog_manager)

            # Если изображение было добавлено (и его не было раньше), удаляем его
            if not prev_has_image and current_has_image:
                self.logger.info("Удаление добавленного изображения")
                self.image_manager.clear_image_data(dialog_manager=dialog_manager)

        # Очищаем сохраненные данные
        self.dialog_data_helper.clear_previous_state(dialog_manager)

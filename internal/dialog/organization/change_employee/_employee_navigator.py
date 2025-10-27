from aiogram_dialog import DialogManager


class _EmployeeNavigator:
    def __init__(self, logger):
        self.logger = logger

    def navigate_employee(
            self,
            dialog_manager: DialogManager,
            button_id: str
    ) -> bool:
        all_employee_ids = dialog_manager.dialog_data.get("all_employee_ids", [])
        current_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

        if not all_employee_ids or current_account_id not in all_employee_ids:
            self.logger.info("Проверка навигации не пройдена")
            return False

        current_index = all_employee_ids.index(current_account_id)

        if button_id == "prev_employee" and current_index > 0:
            self.logger.info("Переход к предыдущему сотруднику")
            new_account_id = all_employee_ids[current_index - 1]
        elif button_id == "next_employee" and current_index < len(all_employee_ids) - 1:
            self.logger.info("Переход к следующему сотруднику")
            new_account_id = all_employee_ids[current_index + 1]
        else:
            return False

        dialog_manager.dialog_data["selected_account_id"] = new_account_id

        # Очищаем временные данные прав при переходе
        dialog_manager.dialog_data.pop("temp_permissions", None)
        dialog_manager.dialog_data.pop("original_permissions", None)

        return True

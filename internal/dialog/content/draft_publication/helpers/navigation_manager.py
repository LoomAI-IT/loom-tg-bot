from aiogram_dialog import DialogManager

from internal.dialog.content.draft_publication.helpers.dialog_data_helper import DialogDataHelper


class NavigationManager:
    def __init__(self, logger):
        self.logger = logger
        self.dialog_data_helper = DialogDataHelper()

    def navigate_publications(
            self,
            dialog_manager: DialogManager,
            direction: str
    ) -> tuple[int, bool]:
        current_index = self.dialog_data_helper.get_current_index(dialog_manager)
        draft_list = self.dialog_data_helper.get_draft_list(dialog_manager)

        if direction == "prev":
            self.logger.info("Переход к предыдущей публикации")
            new_index = max(0, current_index - 1)
        else:  # next
            self.logger.info("Переход к следующей публикации")
            new_index = min(len(draft_list) - 1, current_index + 1)

        at_edge = new_index == current_index

        if not at_edge:
            self.dialog_data_helper.set_current_index(dialog_manager, new_index)
            self.dialog_data_helper.clear_working_publication_from_data(dialog_manager)
        else:
            self.logger.info("Достигнут край списка")

        return new_index, at_edge

    def get_navigation_context(self, dialog_manager: DialogManager) -> dict:
        current_index = self.dialog_data_helper.get_current_index(dialog_manager)
        draft_list = self.dialog_data_helper.get_draft_list(dialog_manager)

        return {
            "current_index": current_index,
            "moderation_list": draft_list,
            "total_count": len(draft_list),
            "has_prev": current_index > 0,
            "has_next": current_index < len(draft_list) - 1
        }

    def can_navigate(self, dialog_manager: DialogManager, direction: str) -> bool:
        context = self.get_navigation_context(dialog_manager)

        if direction == "prev":
            return context["has_prev"]
        else:  # next
            return context["has_next"]

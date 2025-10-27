from aiogram_dialog import DialogManager


class NavigationManager:
    def __init__(self, logger):
        self.logger = logger

    def navigate_publications(
            self,
            dialog_manager: DialogManager,
            direction: str
    ) -> tuple[int, bool]:
        current_index = dialog_manager.dialog_data.get("current_index", 0)
        moderation_list = dialog_manager.dialog_data.get("moderation_list", [])

        if direction == "prev":
            self.logger.info("Переход к предыдущей публикации")
            new_index = max(0, current_index - 1)
        else:  # next
            self.logger.info("Переход к следующей публикации")
            new_index = min(len(moderation_list) - 1, current_index + 1)

        at_edge = new_index == current_index

        if not at_edge:
            dialog_manager.dialog_data["current_index"] = new_index
            dialog_manager.dialog_data.pop("working_publication", None)
        else:
            self.logger.info("Достигнут край списка")

        return new_index, at_edge

    @staticmethod
    def get_navigation_context(dialog_manager: DialogManager) -> dict:
        current_index = dialog_manager.dialog_data.get("current_index", 0)
        moderation_list = dialog_manager.dialog_data.get("moderation_list", [])

        return {
            "current_index": current_index,
            "moderation_list": moderation_list,
            "total_count": len(moderation_list),
            "has_prev": current_index > 0,
            "has_next": current_index < len(moderation_list) - 1
        }

    @staticmethod
    def can_navigate(dialog_manager: DialogManager, direction: str) -> bool:
        context = NavigationManager.get_navigation_context(dialog_manager)

        if direction == "prev":
            return context["has_prev"]
        else:  # next
            return context["has_next"]

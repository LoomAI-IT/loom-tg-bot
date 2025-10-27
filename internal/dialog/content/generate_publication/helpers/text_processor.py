from aiogram_dialog import DialogManager

from internal import model
from internal.dialog.content.generate_publication.helpers import DialogDataHelper, ValidationService


class TextProcessor:

    def __init__(
            self,
            logger,
    ):
        self.logger = logger
        self.validation = ValidationService(
            logger=self.logger
        )
        self.dialog_data_helper = DialogDataHelper(self.logger)

    async def check_text_length_with_image(
            self,
            dialog_manager: DialogManager
    ) -> bool:
        publication_text = self.dialog_data_helper.get_publication_text(dialog_manager)
        has_image = self.dialog_data_helper.get_has_image(dialog_manager)

        is_valid, expected_length = self.validation.validate_publication_text_length(
            text=publication_text,
            has_image=has_image,
            dialog_manager=dialog_manager
        )

        if not is_valid:
            self.dialog_data_helper.set_expected_length(dialog_manager, expected_length)
            await dialog_manager.switch_to(state=model.GeneratePublicationStates.text_too_long_alert)
            return True

        return False

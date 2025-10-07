from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode, ShowMode

from internal import interface, model
from pkg.trace_wrapper import traced_method


class PersonalProfileService(interface.IPersonalProfileService):
    def __init__(
            self,
            tel: interface.ITelemetry,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

    @traced_method()
    async def handle_go_faq(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.logger.info("Начало обработки перехода в FAQ")

        dialog_manager.show_mode = ShowMode.EDIT

        await dialog_manager.switch_to(model.PersonalProfileStates.faq)

        await callback.answer("FAQ открыт")

        self.logger.info("Завершение обработки перехода в FAQ")

    @traced_method()
    async def handle_go_to_support(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.logger.info("Начало обработки перехода в поддержку")

        dialog_manager.show_mode = ShowMode.EDIT

        await dialog_manager.switch_to(model.PersonalProfileStates.support)

        await callback.answer("Техподдержка открыта")

        self.logger.info("Завершение обработки перехода в поддержку")

    @traced_method()
    async def handle_back_to_profile(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.logger.info("Начало обработки возврата в личный профиль")

        dialog_manager.show_mode = ShowMode.EDIT

        await dialog_manager.switch_to(model.PersonalProfileStates.personal_profile)

        await callback.answer("Возврат в профиль")

        self.logger.info("Завершение обработки возврата в личный профиль")

    @traced_method()
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.logger.info("Начало обработки перехода в главное меню")

        dialog_manager.show_mode = ShowMode.EDIT

        await dialog_manager.start(
            model.MainMenuStates.main_menu,
            mode=StartMode.RESET_STACK
        )

        await callback.answer("Главное меню открыто")

        self.logger.info("Завершение обработки перехода в главное меню")

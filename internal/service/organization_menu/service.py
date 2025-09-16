# internal/service/organization_menu/service.py
from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class OrganizationMenuDialogService(interface.IOrganizationMenuDialogService):
    """Сервис для работы с диалогом меню организации"""

    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_organization_client: interface.IKonturOrganizationClient,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_publication_client: interface.IKonturPublicationClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_organization_client = kontur_organization_client
        self.kontur_employee_client = kontur_employee_client
        self.kontur_publication_client = kontur_publication_client

    async def get_organization_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "OrganizationMenuDialogService.get_organization_menu_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
                    chat_id = dialog_manager.event.message.chat.id
                elif hasattr(dialog_manager.event, 'chat'):
                    chat_id = dialog_manager.event.chat.id
                else:
                    chat_id = None

                state = (await self.state_repo.state_by_id(chat_id))[0]

                employee = await self.kontur_employee_client.get_employee_by_account_id(state.account_id)

                # Получаем данные организации
                organization = await self.kontur_organization_client.get_organization_by_id(
                    employee.organization_id
                )

                # Получаем категории организации
                categories = await self.kontur_publication_client.get_categories_by_organization(
                    organization.id
                )

                # Форматируем список платформ (пока заглушка)
                platforms_list = "• Telegram\n• Instagram\n• VKontakte\n• YouTube (короткие видео)"

                # Форматируем список рубрик
                if categories:
                    categories_list = "\n".join([f"• Название" for cat in categories])
                else:
                    categories_list = "• Краткое описание"

                # Рассчитываем доступный контент (примерная формула)
                content_available = organization.rub_balance // 50  # Примерно 50 руб за генерацию

                data = {
                    "organization_name": organization.name,
                    "balance": organization.rub_balance,
                    "content_available": content_available,
                    "platforms_list": platforms_list,
                    "categories_list": categories_list,
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def handle_go_to_user_settings(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Перейти к настройкам пользователей (изменение сотрудников)"""
        with self.tracer.start_as_current_span(
                "OrganizationMenuDialogService.handle_go_to_user_settings",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Запускаем диалог изменения сотрудников
                await dialog_manager.start(
                    model.ChangeEmployeeStates.employee_list,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info(
                    "Переход к настройкам пользователей",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Ошибка при переходе к настройкам", show_alert=True)
                raise

    async def handle_go_to_add_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Перейти к добавлению сотрудника"""
        with self.tracer.start_as_current_span(
                "OrganizationMenuDialogService.handle_go_to_add_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # TODO: Запустить диалог добавления сотрудника
                await callback.answer("Функция в разработке", show_alert=True)

                self.logger.info(
                    "Попытка перехода к добавлению сотрудника",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_top_up_balance(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Перейти к пополнению баланса"""
        with self.tracer.start_as_current_span(
                "OrganizationMenuDialogService.handle_go_to_top_up_balance",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # TODO: Запустить диалог пополнения баланса
                await callback.answer("Функция в разработке", show_alert=True)

                self.logger.info(
                    "Попытка перехода к пополнению баланса",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_social_networks(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Перейти к управлению социальными сетями"""
        with self.tracer.start_as_current_span(
                "OrganizationMenuDialogService.handle_go_to_social_networks",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # TODO: Запустить диалог управления социальными сетями
                await callback.answer("Функция в разработке", show_alert=True)

                self.logger.info(
                    "Попытка перехода к социальным сетям",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise
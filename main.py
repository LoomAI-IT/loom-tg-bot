import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from infrastructure.pg.pg import PG
from infrastructure.telemetry.telemetry import Telemetry, AlertManager

from pkg.client.internal.kontur_account.client import KonturAccountClient
from pkg.client.internal.kontur_authorization.client import KonturAuthorizationClient
from pkg.client.internal.kontur_employee.client import KonturEmployeeClient
from pkg.client.internal.kontur_organization.client import KonturOrganizationClient
from pkg.client.internal.kontur_publication.client import KonturPublicationClient

from internal.controller.http.middlerware.middleware import HttpMiddleware
from internal.controller.tg.middleware.middleware import TgMiddleware

from internal.controller.tg.command.handler import CommandController
from internal.controller.http.webhook.handler import TelegramWebhookController

from internal.controller.tg.dialog.auth.dialog import AuthDialog
from internal.controller.tg.dialog.main_menu.dialog import MainMenuDialog
from internal.controller.tg.dialog.personal_profile.dialog import PersonalProfileDialog
from internal.controller.tg.dialog.organization_menu.dialog import OrganizationMenuDialog
from internal.controller.tg.dialog.change_employee.dialog import ChangeEmployeeDialog
from internal.controller.tg.dialog.add_employee.dialog import AddEmployeeDialog

from internal.service.state.service import StateService
from internal.service.auth.service import AuthDialogService
from internal.service.main_menu.service import MainMenuDialogService
from internal.service.personal_profile.service import PersonalProfileDialogService
from internal.service.organization_menu.service import OrganizationMenuDialogService
from internal.service.change_employee.service import ChangeEmployeeDialogService
from internal.service.add_employee.service import AddEmployeeDialogService

from internal.repo.state.repo import StateRepo

from internal.app.tg.app import NewTg

from internal.config.config import Config

cfg = Config()

# Инициализация мониторинга
alert_manager = AlertManager(
    cfg.alert_tg_bot_token,
    cfg.service_name,
    cfg.alert_tg_chat_id,
    cfg.alert_tg_chat_thread_id,
    cfg.grafana_url,
    cfg.monitoring_redis_host,
    cfg.monitoring_redis_port,
    cfg.monitoring_redis_db,
    cfg.monitoring_redis_password,
    cfg.openai_api_key
)

tel = Telemetry(
    cfg.log_level,
    cfg.root_path,
    cfg.environment,
    cfg.service_name,
    cfg.service_version,
    cfg.otlp_host,
    cfg.otlp_port,
    alert_manager
)

bot = Bot(cfg.tg_bot_token)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация клиентов
db = PG(tel, cfg.db_user, cfg.db_pass, cfg.db_host, cfg.db_port, cfg.db_name)
kontur_account_client = KonturAccountClient(tel, cfg.kontur_account_host, cfg.kontur_account_port)
kontur_authorization_client = KonturAuthorizationClient(tel, cfg.kontur_authorization_host,
                                                        cfg.kontur_authorization_port)
kontur_employee_client = KonturEmployeeClient(tel, cfg.kontur_employee_host, cfg.kontur_employee_port)
kontur_organization_client = KonturOrganizationClient(tel, cfg.kontur_organization_host, cfg.kontur_organization_port)
kontur_publication_client = KonturPublicationClient(tel, cfg.kontur_publication_host, cfg.kontur_publication_port)

state_repo = StateRepo(tel, db)

state_service = StateService(tel, state_repo)
auth_dialog_service = AuthDialogService(
    tel,
    state_repo,
    cfg.domain,
    kontur_account_client,
    kontur_organization_client,
    kontur_employee_client,
)
main_menu_service = MainMenuDialogService(
    tel,
    state_repo,
    kontur_employee_client,
    kontur_organization_client
)
personal_profile_service = PersonalProfileDialogService(
    tel,
    state_repo,
    kontur_employee_client,
    kontur_organization_client
)
organization_menu_service = OrganizationMenuDialogService(
    tel,
    state_repo,
    kontur_organization_client,
    kontur_employee_client,
    kontur_publication_client,
)
change_employee_service = ChangeEmployeeDialogService(
    tel,
    kontur_employee_client,
    kontur_organization_client
)

add_employee_service = AddEmployeeDialogService(
    tel,
    bot,
    state_repo,
    kontur_employee_client,
)

auth_dialog = AuthDialog(
    tel,
    auth_dialog_service,
)
main_menu_dialog = MainMenuDialog(
    tel,
    main_menu_service
)
personal_profile_dialog = PersonalProfileDialog(
    tel,
    personal_profile_service
)
organization_menu_dialog = OrganizationMenuDialog(
    tel,
    organization_menu_service
)
change_employee_dialog = ChangeEmployeeDialog(
    tel,
    change_employee_service
)

add_employee_dialog = AddEmployeeDialog(
    tel,
    add_employee_service
)

# Инициализация middleware
tg_middleware = TgMiddleware(
    tel,
    state_service,
    bot,
)
http_middleware = HttpMiddleware(
    tel,
    cfg.prefix,
)
tg_webhook_controller = TelegramWebhookController(
    tel,
    dp,
    bot,
    cfg.domain,
    cfg.prefix,
)

command_controller = CommandController(tel, state_service)

if __name__ == "__main__":
    app = NewTg(
        db,
        dp,
        http_middleware,
        tg_middleware,
        tg_webhook_controller,
        command_controller,
        auth_dialog,
        main_menu_dialog,
        personal_profile_dialog,
        organization_menu_dialog,
        change_employee_dialog,
        add_employee_dialog,
        cfg.prefix,
    )
    uvicorn.run(app, host="0.0.0.0", port=int(cfg.http_port), access_log=False)

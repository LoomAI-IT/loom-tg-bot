import uvicorn
from aiogram import Bot, Dispatcher

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
from internal.controller.tg.dialog.auth.handler import AuthDialogController
from internal.controller.http.webhook.handler import TelegramWebhookController

from internal.controller.tg.dialog.auth.dialog import AuthDialog

from internal.service.auth.service import AuthDialogService
from internal.service.state.service import StateService

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
dp = Dispatcher()

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
)
auth_dialog_controller = AuthDialogController(
    tel,
    state_service,
    kontur_account_client,
    kontur_organization_client,
)
auth_dialog = AuthDialog(
    tel,
    auth_dialog_controller,
    auth_dialog_service,
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
        cfg.prefix
    )
    uvicorn.run(app, host="0.0.0.0", port=int(cfg.http_port), access_log=False)

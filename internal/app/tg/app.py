from fastapi import FastAPI

from aiogram.filters import Command
from aiogram_dialog import setup_dialogs
from aiogram import Dispatcher, Router

from internal import model, interface


def NewTg(
        db: interface.IDB,
        dp: Dispatcher,
        http_middleware: interface.IHttpMiddleware,
        tg_middleware: interface.ITelegramMiddleware,
        tg_webhook_controller: interface.ITelegramWebhookController,
        command_controller: interface.ICommandController,
        auth_dialog: interface.IAuthDialog,
        prefix: str
):
    app = FastAPI(
        openapi_url=prefix + "/openapi.json",
        docs_url=prefix + "/docs",
        redoc_url=prefix + "/redoc",
    )
    include_tg_middleware(dp, tg_middleware)
    include_http_middleware(app, http_middleware)

    include_db_handler(app, db, prefix)
    include_tg_webhook(app, tg_webhook_controller, prefix)
    include_command_handlers(
        dp,
        command_controller
    )
    include_dialogs(
        dp,
        auth_dialog
    )

    return app


def include_http_middleware(
        app: FastAPI,
        http_middleware: interface.IHttpMiddleware
):
    http_middleware.logger_middleware03(app)
    http_middleware.metrics_middleware02(app)
    http_middleware.trace_middleware01(app)


def include_tg_middleware(
        dp: Dispatcher,
        tg_middleware: interface.ITelegramMiddleware,
):
    dp.update.middleware(tg_middleware.trace_middleware01)
    dp.update.middleware(tg_middleware.metric_middleware02)
    dp.update.middleware(tg_middleware.logger_middleware03)
    dp.update.middleware(tg_middleware.get_state_middleware04)


def include_tg_webhook(
        app: FastAPI,
        tg_webhook_controller: interface.ITelegramWebhookController,
        prefix: str
):
    app.add_api_route(
        prefix + "/update",
        tg_webhook_controller.bot_webhook,
        methods=["POST"]
    )
    app.add_api_route(
        prefix + "/webhook/set",
        tg_webhook_controller.bot_set_webhook,
        methods=["POST"]
    )


def include_command_handlers(
        dp: Dispatcher,
        command_controller: interface.ICommandController,
):
    dp.message.register(
        command_controller.start_handler,
        Command("start")
    )


def include_dialogs(
        dp: Dispatcher,
        auth_dialog: interface.IAuthDialog,
):
    dialog_router = Router()
    dialog_router.include_routers(
        auth_dialog.get_dialog()
    )

    dp.include_routers(dialog_router)

    setup_dialogs(dp)


def include_message_handler(
        dp: Dispatcher,
        message_controller: interface.IMessageController
):
    dp.message.register(
        message_controller.message_handler,
    )


def include_db_handler(app: FastAPI, db: interface.IDB, prefix):
    app.add_api_route(prefix + "/table/create", create_table_handler(db), methods=["GET"])
    app.add_api_route(prefix + "/table/drop", drop_table_handler(db), methods=["GET"])


def create_table_handler(db: interface.IDB):
    async def create_table():
        try:
            await db.multi_query(model.create_queries)
        except Exception as err:
            raise err

    return create_table


def drop_table_handler(db: interface.IDB):
    async def delete_table():
        try:
            await db.multi_query(model.drop_queries)
        except Exception as err:
            raise err

    return delete_table

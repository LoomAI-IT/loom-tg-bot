from fastapi import FastAPI

from internal import model, interface


def NewServer(
        db: interface.IDB,
        http_middleware: interface.IHttpMiddleware,
        tg_webhook_controller: interface.ITelegramWebhookController,
        prefix: str
):
    app = FastAPI(
        openapi_url=prefix + "/openapi.json",
        docs_url=prefix + "/docs",
        redoc_url=prefix + "/redoc",
    )
    include_http_middleware(app, http_middleware)

    include_db_handler(app, db, prefix)
    include_tg_webhook(app, tg_webhook_controller, prefix)

    return app


def include_http_middleware(
        app: FastAPI,
        http_middleware: interface.IHttpMiddleware
):
    http_middleware.logger_middleware02(app)
    http_middleware.trace_middleware01(app)


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

    app.add_api_route(
        prefix + "/employee/notify/added",
        tg_webhook_controller.notify_employee_added,
        methods=["POST"]
    )

    app.add_api_route(
        prefix + "/employee/notify/deleted",
        tg_webhook_controller.notify_employee_deleted,
        methods=["POST"]
    )

    app.add_api_route(
        prefix + "/video-cut/vizard/notify/generated",
        tg_webhook_controller.notify_vizard_video_cut_generated,
        methods=["POST"]
    )

    app.add_api_route(
        prefix + "/notify/publication/approved",
        tg_webhook_controller.notify_publication_approved_alert,
        methods=["POST"]
    )

    app.add_api_route(
        prefix + "/notify/publication/rejected",
        tg_webhook_controller.notify_publication_rejected_alert,
        methods=["POST"]
    )

    app.add_api_route(
        prefix + "/file/cache",
        tg_webhook_controller.set_cache_file,
        methods=["POST"]
    )


def include_db_handler(app: FastAPI, db: interface.IDB, prefix):
    app.add_api_route(prefix + "/table/create", create_table_handler(db), methods=["GET"])
    app.add_api_route(prefix + "/table/drop", drop_table_handler(db), methods=["GET"])
    app.add_api_route(prefix + "/health", heath_check_handler(), methods=["GET"])


def create_table_handler(db: interface.IDB):
    async def create_table():
        try:
            await db.multi_query(model.create_queries)
        except Exception as err:
            raise err

    return create_table


def heath_check_handler():
    async def heath_check():
        return "ok"

    return heath_check


def drop_table_handler(db: interface.IDB):
    async def delete_table():
        try:
            await db.multi_query(model.drop_queries)
        except Exception as err:
            raise err

    return delete_table

import os

class Config:
    db_pass: str = os.environ.get('WEWALL_ADMIN_TG_BOT_POSTGRES_PASSWORD')
    db_user: str = os.environ.get('WEWALL_ADMIN_TG_BOT_POSTGRES_USER')
    db_name: str = os.environ.get('WEWALL_ADMIN_TG_BOT_POSTGRES_DB_NAME')
    db_host: str = os.environ.get('WEWALL_ADMIN_TG_BOT_POSTGRES_CONTAINER_NAME')
    db_port: str = "5432"

    domain: str = os.environ.get("WEWALL_DOMAIN")
    bot_link: str = os.environ.get('WEWALL_AI_BOT_LINK')

    wewall_tg_bot_host: str = os.environ.get('WEWALL_TG_BOT_CONTAINER_NAME')
    wewall_tg_bot_port: int = int(os.environ.get("WEWALL_TG_BOT_PORT"))

    tg_bot_token: str = os.environ.get('WEWALL_ADMIN_TG_BOT_TOKEN')

    environment = os.environ.get('ENVIRONMENT')
    log_level = os.environ.get('LOG_LEVEL')
    http_port: int = int(os.environ.get("WEWALL_ADMIN_TG_BOT_PORT"))
    service_name = "wewall-admin-tg-bot"
    root_path = "/app"
    service_version = "0.0.1"
    prefix = os.environ.get("WEWALL_ADMIN_TG_BOT_PREFIX")

    otlp_host: str = os.environ.get("WEWALL_OTEL_COLLECTOR_CONTAINER_NAME")
    otlp_port: int = int(os.environ.get("WEWALL_OTEL_COLLECTOR_GRPC_PORT"))

    alert_tg_bot_token: str = os.environ.get('WEWALL_ALERT_TG_BOT_TOKEN')
    alert_tg_chat_id: int = int(os.environ.get('WEWALL_ALERT_TG_CHAT_ID'))
    alert_tg_chat_thread_id: int = int(os.environ.get('WEWALL_ALERT_TG_CHAT_THREAD_ID'))
    grafana_url: str = os.environ.get('WEWALL_GRAFANA_URL')

    monitoring_redis_host: str = os.environ.get('WEWALL_MONITORING_REDIS_CONTAINER_NAME')
    monitoring_redis_port: int = int(os.environ.get('WEWALL_MONITORING_REDIS_PORT'))
    monitoring_redis_db: int = int(os.environ.get('WEWALL_MONITORING_DEDUPLICATE_ERROR_ALERT_REDIS_DB'))
    monitoring_redis_password: str = os.environ.get('WEWALL_MONITORING_REDIS_PASSWORD')

    weed_master_host: str = os.environ.get('WEWALL_WEED_MASTER_CONTAINER_NAME')
    weed_master_port: int = int(os.environ.get('WEWALL_WEED_MASTER_PORT'))


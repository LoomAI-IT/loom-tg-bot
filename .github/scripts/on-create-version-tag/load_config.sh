#!/bin/bash

# ============================================
# Утилиты логирования
# ============================================

log_info() {
    local title=$1
    local message=$2
    echo "ℹ️  $message"
}

log_success() {
    local title=$1
    local message=$2
    echo "✅ $message"
}

log_error() {
    local title=$1
    local message=$2
    echo "❌ $message"
}

log_warning() {
    local title=$1
    local message=$2
    echo "⚠️  $message"
}

# ============================================
# Валидация конфигурации
# ============================================

validate_env_var() {
    local var_name=$1
    local var_value=$2
    local error_message=$3

    if [ -z "$var_value" ]; then
        log_error "Ошибка конфигурации" "$error_message"
        log_info "Требуемая переменная" "Отсутствует: $var_name"
        exit 1
    fi
}

export_to_github_env() {
    local var_name=$1
    local var_value=$2
    echo "$var_name=$var_value" >> $GITHUB_ENV
}

# ============================================
# Основной загрузчик конфигурации
# ============================================

load_server_config() {
    log_info "Конфигурация" "Загрузка конфигурации сервера..."

    local config_file="/root/.env.runner"

    # Проверка существования файла конфигурации
    if [ ! -f "$config_file" ]; then
        log_error "Ошибка конфигурации" "Файл конфигурации сервера не найден: $config_file"
        exit 1
    fi

    # Загрузка переменных окружения из файла конфигурации
    set -a
    source "$config_file"
    set +a

    log_success "Конфигурация" "Переменные окружения загружены из $config_file"

    # Валидация требуемой конфигурации API
    validate_env_var "STAGE_DOMAIN" "$STAGE_DOMAIN" "STAGE_DOMAIN не настроен в .env.runner"
    validate_env_var "PROD_DOMAIN" "$PROD_DOMAIN" "PROD_DOMAIN не настроен в .env.runner"

    # Валидация конфигурации stage-сервера
    validate_env_var "STAGE_HOST" "$STAGE_HOST" "STAGE_HOST не настроен в .env.runner"
    validate_env_var "STAGE_PASSWORD" "$STAGE_PASSWORD" "STAGE_PASSWORD не настроен в .env.runner"

    log_success "Валидация" "Все требуемые переменные конфигурации присутствуют"

    # Извлечение и построение префикса сервиса
    SERVICE_PREFIX=$(echo "$SERVICE_NAME" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
    SERVICE_PREFIX_VAR_NAME="${SERVICE_PREFIX}_PREFIX"
    SERVICE_PREFIX="${!SERVICE_PREFIX_VAR_NAME}"

    log_info "Сервис" "Префикс сервиса определён: $SERVICE_PREFIX"

    # Экспорт основной конфигурации в окружение GitHub
    export_to_github_env "SERVICE_PREFIX" "$SERVICE_PREFIX"
    export_to_github_env "STAGE_HOST" "$STAGE_HOST"
    export_to_github_env "STAGE_PASSWORD" "$STAGE_PASSWORD"
    export_to_github_env "STAGE_DOMAIN" "$STAGE_DOMAIN"
    export_to_github_env "PROD_DOMAIN" "$PROD_DOMAIN"

    # Экспорт префиксов для конкретных сервисов
    export_to_github_env "LOOM_TG_BOT_PREFIX" "$LOOM_TG_BOT_PREFIX"
    export_to_github_env "LOOM_ACCOUNT_PREFIX" "$LOOM_ACCOUNT_PREFIX"
    export_to_github_env "LOOM_AUTHORIZATION_PREFIX" "$LOOM_AUTHORIZATION_PREFIX"
    export_to_github_env "LOOM_EMPLOYEE_PREFIX" "$LOOM_EMPLOYEE_PREFIX"
    export_to_github_env "LOOM_ORGANIZATION_PREFIX" "$LOOM_ORGANIZATION_PREFIX"
    export_to_github_env "LOOM_CONTENT_PREFIX" "$LOOM_CONTENT_PREFIX"
    export_to_github_env "LOOM_RELEASE_TG_BOT_PREFIX" "$LOOM_RELEASE_TG_BOT_PREFIX"
    export_to_github_env "LOOM_INTERSERVER_SECRET_KEY" "$LOOM_INTERSERVER_SECRET_KEY"

    log_success "Конфигурация" "Все переменные экспортированы в окружение GitHub"
    log_info "Детали" "Сервис: $SERVICE_NAME | Префикс: $SERVICE_PREFIX"
    log_info "Детали" "Stage хост: $STAGE_HOST | Stage домен: $STAGE_DOMAIN"
    log_info "Детали" "Production домен: $PROD_DOMAIN"
}
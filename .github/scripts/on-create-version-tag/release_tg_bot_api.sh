#!/bin/bash

# ============================================
# Утилиты для работы с API
# ============================================

api_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_code=$4

    log_info "API запрос" "Метод: $method | Endpoint: $endpoint"
    log_debug "Данные запроса" "$data"

    local response=$(curl -s -w "\n%{http_code}" -X "$method" \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)

    log_debug "HTTP код ответа" "$http_code"
    log_debug "Тело ответа" "$body"

    if [ "$http_code" -ne "$expected_code" ]; then
        log_error "Ошибка API запроса" "Получен HTTP $http_code, ожидался $expected_code"
        log_error "Endpoint" "$endpoint"
        log_error "Метод" "$method"
        log_error "Тело ответа" "$body"
        return 1
    fi

    log_success "API запрос выполнен" "HTTP $http_code | Endpoint: $endpoint"
    echo "$body"
    return 0
}

extract_json_value() {
    local json=$1
    local key=$2

    log_debug "Извлечение JSON" "Ключ: $key" >&2

    local value=$(echo "$json" | grep -o "\"$key\":[0-9]*" | sed "s/\"$key\"://")

    if [ -z "$value" ]; then
        log_warning "Извлечение JSON" "Ключ '$key' не найден в ответе" >&2
        log_debug "JSON" "$json" >&2
    else
        log_debug "Извлечено значение" "$key = $value" >&2
    fi

    # Только значение в stdout
    echo "$value"
}

# ============================================
# Управление записями релизов
# ============================================

create_release_record() {
    log_info "=== Создание записи релиза ===" ""
    log_info "Сервис" "$SERVICE_NAME"
    log_info "Тег релиза" "$TAG_NAME"
    log_info "Инициатор" "$GITHUB_ACTOR"
    log_info "GitHub Run ID" "$GITHUB_RUN_ID"
    log_info "GitHub Ref" "$GITHUB_REF"

    local payload=$(cat <<EOF
{
    "service_name": "$SERVICE_NAME",
    "release_tag": "$TAG_NAME",
    "status": "initiated",
    "initiated_by": "$GITHUB_ACTOR",
    "github_run_id": "$GITHUB_RUN_ID",
    "github_action_link": "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID",
    "github_ref": "$GITHUB_REF"
}
EOF
)

    log_debug "JSON payload" "$payload"

    local endpoint="${PROD_DOMAIN}${LOOM_RELEASE_TG_BOT_PREFIX}/release"
    log_info "Отправка запроса" "$endpoint"

    local response=$(api_request "POST" "$endpoint" "$payload" 201)
    local api_result=$?

    if [ $api_result -ne 0 ]; then
        log_error "Создание записи релиза" "API запрос завершился с ошибкой"
        log_error "Критическая ошибка" "Невозможно продолжить без ID релиза"
        exit 1
    fi

    log_debug "Разбор ответа API" "Извлечение release_id"

    # Извлечение ID релиза из ответа (логи идут в stderr, только значение в stdout)
    local release_id=$(extract_json_value "$response" "release_id")

    if [ -z "$release_id" ]; then
        log_error "Парсинг ответа" "Не удалось извлечь release_id"
        log_error "Полный ответ API" "$response"
        log_error "Критическая ошибка" "Невозможно продолжить без ID релиза"
        exit 1
    fi

    log_info "Извлечён Release ID" "$release_id"

    # Экспорт ID релиза в окружение GitHub
    echo "RELEASE_ID=$release_id" >> $GITHUB_ENV
    log_debug "GitHub Environment" "RELEASE_ID=$release_id экспортирован"

    log_success "=== Запись релиза создана ===" ""
    log_success "Release ID" "$release_id"
    log_success "Начальный статус" "initiated"
    log_info "Ссылка на GitHub Action" "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
}

update_release_status() {
    local new_status=$1

    log_info "=== Обновление статуса релиза ===" ""

    if [ -z "$RELEASE_ID" ]; then
        log_warning "Обновление статуса" "RELEASE_ID не установлен в окружении"
        log_warning "Действие" "Пропуск обновления статуса"
        return 0
    fi

    log_info "Release ID" "$RELEASE_ID"
    log_info "Новый статус" "$new_status"

    local payload=$(cat <<EOF
{
    "release_id": $RELEASE_ID,
    "status": "$new_status"
}
EOF
)

    log_debug "JSON payload" "$payload"

    local endpoint="${PROD_DOMAIN}${LOOM_RELEASE_TG_BOT_PREFIX}/release"
    log_info "Отправка PATCH запроса" "$endpoint"

    local response=$(curl -s -w "\n%{http_code}" -X PATCH \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)

    log_debug "HTTP код ответа" "$http_code"
    log_debug "Тело ответа" "$body"

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 204 ]; then
        log_success "=== Статус обновлён ===" ""
        log_success "Release ID" "$RELEASE_ID"
        log_success "Статус" "$new_status"
    else
        log_warning "Обновление статуса" "Получен неожиданный HTTP код: $http_code"
        log_warning "Endpoint" "$endpoint"
        log_warning "Тело ответа" "$body"
        log_info "Примечание" "Релиз продолжится, несмотря на ошибку обновления статуса"
    fi
}
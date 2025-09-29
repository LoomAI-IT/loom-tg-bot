#!/bin/bash

# ============================================
# Утилиты для работы с API
# ============================================

api_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_code=$4

    log_info "API запрос" "Метод: $method | Endpoint: $endpoint" >&2
    log_debug "Данные запроса" "$data" >&2

    local response=$(curl -s -w "\n%{http_code}" -X "$method" \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)

    log_debug "HTTP код ответа" "$http_code" >&2
    log_debug "Тело ответа" "$body" >&2

    if [ "$http_code" -ne "$expected_code" ]; then
        log_error "Ошибка API запроса" "Получен HTTP $http_code, ожидался $expected_code" >&2
        log_error "Endpoint" "$endpoint" >&2
        log_error "Метод" "$method" >&2
        log_error "Тело ответа" "$body" >&2
        return 1
    fi

    log_success "API запрос выполнен" "HTTP $http_code | Endpoint: $endpoint" >&2

    # Только тело ответа в stdout
    echo "$body"
    return 0
}

extract_json_value() {
    local json=$1
    local key=$2

    local value=$(echo "$json" | grep -o "\"$key\":[0-9]*" | sed "s/\"$key\"://")

    if [ -z "$value" ]; then
        log_warning "Извлечение JSON" "Ключ '$key' не найден в ответе"
        log_debug "JSON" "$json"
    fi

    echo "$value"
}

# ============================================
# Управление записями релизов
# ============================================

create_release_record() {
    log_info "=== Создание записи релиза ===" "" >&2
    log_info "Сервис" "$SERVICE_NAME" >&2
    log_info "Тег релиза" "$TAG_NAME" >&2
    log_info "Инициатор" "$GITHUB_ACTOR" >&2
    log_info "GitHub Run ID" "$GITHUB_RUN_ID" >&2
    log_info "GitHub Ref" "$GITHUB_REF" >&2

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

    log_debug "JSON payload" "$payload" >&2

    local endpoint="${PROD_DOMAIN}${LOOM_RELEASE_TG_BOT_PREFIX}/release"
    log_info "Отправка запроса" "$endpoint" >&2

    local response=$(api_request "POST" "$endpoint" "$payload" 201)
    local api_result=$?

    if [ $api_result -ne 0 ]; then
        log_error "Создание записи релиза" "API запрос завершился с ошибкой" >&2
        log_error "Критическая ошибка" "Невозможно продолжить без ID релиза" >&2
        exit 1
    fi

    log_debug "Разбор ответа API" "Извлечение release_id" >&2

    # Извлечение ID релиза из ответа (только значение в stdout)
    local release_id=$(echo "$response" | grep -o '"release_id":[0-9]*' | sed 's/"release_id"://')

    if [ -z "$release_id" ]; then
        log_error "Парсинг ответа" "Не удалось извлечь release_id" >&2
        log_error "Полный ответ API" "$response" >&2
        log_error "Критическая ошибка" "Невозможно продолжить без ID релиза" >&2
        exit 1
    fi

    log_info "Извлечён Release ID" "$release_id" >&2

    # Экспорт ID релиза в окружение GitHub
    echo "RELEASE_ID=$release_id" >> $GITHUB_ENV
    log_debug "GitHub Environment" "RELEASE_ID=$release_id экспортирован" >&2

    log_success "=== Запись релиза создана ===" "" >&2
    log_success "Release ID" "$release_id" >&2
    log_success "Начальный статус" "initiated" >&2
    log_info "Ссылка на GitHub Action" "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID" >&2
}

update_release_status() {
    local new_status=$1

    log_info "=== Обновление статуса релиза ===" "" >&2

    if [ -z "$RELEASE_ID" ]; then
        log_warning "Обновление статуса" "RELEASE_ID не установлен в окружении" >&2
        log_warning "Действие" "Пропуск обновления статуса" >&2
        return 0
    fi

    log_info "Release ID" "$RELEASE_ID" >&2
    log_info "Новый статус" "$new_status" >&2

    local payload=$(cat <<EOF
{
    "release_id": $RELEASE_ID,
    "status": "$new_status"
}
EOF
)

    log_debug "JSON payload" "$payload" >&2

    local endpoint="${PROD_DOMAIN}${LOOM_RELEASE_TG_BOT_PREFIX}/release"
    log_info "Отправка PATCH запроса" "$endpoint" >&2

    local response=$(curl -s -w "\n%{http_code}" -X PATCH \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)

    log_debug "HTTP код ответа" "$http_code" >&2
    log_debug "Тело ответа" "$body" >&2

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 204 ]; then
        log_success "=== Статус обновлён ===" "" >&2
        log_success "Release ID" "$RELEASE_ID" >&2
        log_success "Статус" "$new_status" >&2
    else
        log_warning "Обновление статуса" "Получен неожиданный HTTP код: $http_code" >&2
        log_warning "Endpoint" "$endpoint" >&2
        log_warning "Тело ответа" "$body" >&2
        log_info "Примечание" "Релиз продолжится, несмотря на ошибку обновления статуса" >&2
    fi
}
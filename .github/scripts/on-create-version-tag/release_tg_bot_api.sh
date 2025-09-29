#!/bin/bash

source .github/scripts/load_config.sh

# ============================================
# Утилиты для работы с API
# ============================================

api_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_code=$4

    log_info "API запрос" "Выполнение $method запроса к $endpoint"

    local response=$(curl -s -w "\n%{http_code}" -X "$method" \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)

    if [ "$http_code" -ne "$expected_code" ]; then
        log_error "Ошибка API" "Запрос завершился с HTTP $http_code (ожидался $expected_code)"
        log_info "Тело ответа" "$body"
        return 1
    fi

    log_success "API запрос" "Запрос выполнен успешно (HTTP $http_code)"
    echo "$body"
    return 0
}

extract_json_value() {
    local json=$1
    local key=$2
    echo "$json" | grep -o "\"$key\":[0-9]*" | sed "s/\"$key\"://"
}

# ============================================
# Управление записями релизов
# ============================================

create_release_record() {
    log_info "Запись релиза" "Создание записи релиза для $SERVICE_NAME:$TAG_NAME"
    log_info "Детали" "Инициатор: $GITHUB_ACTOR | ID запуска: $GITHUB_RUN_ID"

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

    local endpoint="${PROD_DOMAIN}${LOOM_RELEASE_TG_BOT_PREFIX}/release"
    local response=$(api_request "POST" "$endpoint" "$payload" 201)

    if [ $? -ne 0 ]; then
        log_error "Запись релиза" "Не удалось создать запись релиза"
        exit 1
    fi

    # Извлечение ID релиза из ответа
    local release_id=$(extract_json_value "$response" "release_id")

    if [ -z "$release_id" ]; then
        log_error "Запись релиза" "Не удалось извлечь ID релиза из ответа"
        log_info "Ответ" "$response"
        exit 1
    fi

    # Экспорт ID релиза в окружение GitHub
    echo "RELEASE_ID=$release_id" >> $GITHUB_ENV

    log_success "Запись релиза" "Создана запись релиза с ID: $release_id"
    log_info "Статус" "Начальный статус: initiated"
}

update_release_status() {
    local new_status=$1

    if [ -z "$RELEASE_ID" ]; then
        log_warning "Статус релиза" "RELEASE_ID не установлен, пропуск обновления статуса"
        return 0
    fi

    log_info "Статус релиза" "Обновление статуса релиза #$RELEASE_ID: $new_status"

    local payload=$(cat <<EOF
{
    "release_id": $RELEASE_ID,
    "status": "$new_status"
}
EOF
)

    local endpoint="${PROD_DOMAIN}${LOOM_RELEASE_TG_BOT_PREFIX}/release"

    local response=$(curl -s -w "\n%{http_code}" -X PATCH \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 204 ]; then
        log_success "Статус релиза" "Статус успешно обновлён на: $new_status"
    else
        log_warning "Статус релиза" "Не удалось обновить статус (HTTP $http_code)"
        log_info "Ответ" "$(echo "$response" | head -n -1)"
    fi
}
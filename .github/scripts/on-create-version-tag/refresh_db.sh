#!/bin/bash

# ============================================
# Операции с таблицами базы данных
# ============================================

refresh_database_table() {
    local service_prefix=$1
    local service_name=$2

    log_info "База данных" "Обновление таблиц базы данных $service_name..."
    log_info "URL" "Drop URL: ${STAGE_DOMAIN}${service_prefix}/table/drop"  # Добавьте эту строку
    log_info "URL" "Create URL: ${STAGE_DOMAIN}${service_prefix}/table/create"  # И эту

    local drop_url="${STAGE_DOMAIN}${service_prefix}/table/drop"
    local create_url="${STAGE_DOMAIN}${service_prefix}/table/create"

    # Удаление существующих таблиц
    log_info "База данных" "Удаление таблиц $service_name..."
    local drop_response=$(curl -s -w "\n%{http_code}" -X GET "$drop_url")
    local drop_code=$(echo "$drop_response" | tail -n1)
    local drop_body=$(echo "$drop_response" | head -n -1)

    log_info "Ответ drop" "HTTP код: $drop_code, Тело: $drop_body"  # Добавьте эту строку

    if [ "$drop_code" -ne 200 ]; then
        log_warning "База данных" "Не удалось удалить таблицы $service_name (HTTP $drop_code)"
        log_info "Ответ" "$drop_body"
    else
        log_success "База данных" "Таблицы $service_name удалены"
    fi

    # Создание новых таблиц
    log_info "База данных" "Создание таблиц $service_name..."
    local create_response=$(curl -s -w "\n%{http_code}" -X GET "$create_url")
    local create_code=$(echo "$create_response" | tail -n1)
    local create_body=$(echo "$create_response" | head -n -1)

    log_info "Ответ create" "HTTP код: $create_code, Тело: $create_body"  # Добавьте эту строку

    if [ "$create_code" -ne 200 ]; then
        log_error "База данных" "Не удалось создать таблицы $service_name (HTTP $create_code)"
        log_info "Ответ" "$create_body"
        log_error "Детали" "URL: $create_url"  # Добавьте эту строку
        return 1
    fi

    log_success "База данных" "Таблицы $service_name успешно созданы"
    return 0
}

# ============================================
# Массовое обновление баз данных
# ============================================

refresh_all_databases() {
    log_info "Обновление БД" "Запуск обновления баз данных для всех сервисов..."
    log_info "Цель" "Stage домен: $STAGE_DOMAIN"

    # Определение всех сервисов для обновления
    local services=(
        "$LOOM_TG_BOT_PREFIX:TG Bot"
        "$LOOM_ACCOUNT_PREFIX:Account"
        "$LOOM_AUTHORIZATION_PREFIX:Authorization"
        "$LOOM_EMPLOYEE_PREFIX:Employee"
        "$LOOM_ORGANIZATION_PREFIX:Organization"
        "$LOOM_CONTENT_PREFIX:Content"
    )

    local total=${#services[@]}
    local failed=0
    local success=0

    log_info "Прогресс" "Обработка баз данных $total сервисов..."

    # ИСПРАВЛЕНИЕ: отключаем set -e для цикла
    set +e

    for service_info in "${services[@]}"; do
        log_info "DEBUG" "Обработка: '$service_info'"

        IFS=':' read -r prefix name <<< "$service_info"

        log_info "DEBUG" "Префикс: '$prefix', Имя: '$name'"

        # Проверка на пустой префикс
        if [ -z "$prefix" ] || [ "$prefix" = ":" ]; then
            log_warning "Конфигурация" "Пропуск сервиса с пустым префиксом: $name"
            ((failed++))
            continue
        fi

        # Вызов функции с явной обработкой результата
        if refresh_database_table "$prefix" "$name"; then
            ((success++))
        else
            ((failed++))
        fi

        echo "" # Пустая строка для читаемости
    done

    # ИСПРАВЛЕНИЕ: включаем обратно set -e
    set -e

    # Итоги
    log_info "Итоги" "Завершено: $success успешно, $failed с ошибками из $total всего"

    if [ $failed -gt 0 ]; then
        log_error "Обновление БД" "Не удалось обновить $failed сервис(ов)"
        return 1  # ИЗМЕНЕНО: используем return вместо exit
    fi

    log_success "Обновление БД" "Все $total баз данных успешно обновлены"
    return 0  # ДОБАВЛЕНО: явный успешный возврат
}
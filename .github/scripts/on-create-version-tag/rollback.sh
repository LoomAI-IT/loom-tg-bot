#!/bin/bash

# ============================================
# Основная функция отката
# ============================================

execute_rollback() {
    local target_tag=$1

    log_info "Откат" "Запуск отката к версии $target_tag на $STAGE_HOST"
    log_info "Подключение" "Подключение через SSH к root@$STAGE_HOST:22"

    SSH_OUTPUT=$(sshpass -p "$STAGE_PASSWORD" ssh -o StrictHostKeyChecking=no root@$STAGE_HOST -p 22 \
        SERVICE_NAME="$SERVICE_NAME" \
        TARGET_TAG="$PREVIOUS_TAG" \
        SYSTEM_REPO="$SYSTEM_REPO" \
        SERVICE_PREFIX="$SERVICE_PREFIX" \
        STAGE_DOMAIN="$STAGE_DOMAIN" \
        bash << 'EOFMAIN'
set -e

# ============================================
# Настройка логирования на удаленном сервере
# ============================================

LOG_DIR="/var/log/deployments/rollback/$SERVICE_NAME"
LOG_FILE="$LOG_DIR/$TARGET_TAG-rollback.log"

init_logging() {
    mkdir -p "$LOG_DIR"
    echo "========================================" >> "$LOG_FILE"
    echo "Откат начат: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    echo "Сервис: $SERVICE_NAME" >> "$LOG_FILE"
    echo "Целевой тег: $TARGET_TAG" >> "$LOG_FILE"
    echo "========================================" >> "$LOG_FILE"
}

log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local prefix=""

    case $level in
        "INFO") prefix="ℹ️" ;;
        "SUCCESS") prefix="✅" ;;
        "ERROR") prefix="❌" ;;
        "WARNING") prefix="⚠️" ;;
    esac

    echo "[$timestamp] [$level] $prefix $message" | tee -a "$LOG_FILE"
}

# ============================================
# Сохранение текущего состояния
# ============================================

save_current_state() {
    log_message "INFO" "Сохранение текущего состояния перед откатом"

    cd loom/$SERVICE_NAME

    local current_ref=$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
    log_message "INFO" "Текущее состояние: $current_ref"

    # Сохраняем для возможного восстановления
    echo "$current_ref" > /tmp/${SERVICE_NAME}_rollback_previous.txt

    log_message "SUCCESS" "Текущее состояние сохранено: $current_ref"
}

# ============================================
# Операции с Git для отката
# ============================================

update_repository_for_rollback() {
    log_message "INFO" "Обновление репозитория для отката на $TARGET_TAG"

    cd loom/$SERVICE_NAME

    # Удаление локального тега, если существует
    if git tag -l | grep -q "^$TARGET_TAG$"; then
        log_message "INFO" "Удаление существующего локального тега $TARGET_TAG"
        git tag -d $TARGET_TAG >> "$LOG_FILE" 2>&1
    fi

    # Получение обновлений с удаленного репозитория
    log_message "INFO" "Получение обновлений из origin"
    git fetch origin >> "$LOG_FILE" 2>&1

    log_message "INFO" "Принудительное обновление тегов с удаленного репозитория"
    git fetch origin --tags --force >> "$LOG_FILE" 2>&1

    # Проверка доступности тега
    if ! git tag -l | grep -q "^$TARGET_TAG$"; then
        log_message "ERROR" "Тег $TARGET_TAG не найден после получения"
        log_message "INFO" "Доступные теги (последние 10):"
        git tag -l | tail -10 | tee -a "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Тег $TARGET_TAG доступен для отката"
}

checkout_rollback_tag() {
    log_message "INFO" "Переключение на тег отката $TARGET_TAG"

    git checkout $TARGET_TAG >> "$LOG_FILE" 2>&1

    if [ $? -ne 0 ]; then
        log_message "ERROR" "Не удалось переключиться на тег $TARGET_TAG"
        tail -20 "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Успешно переключено на тег отката $TARGET_TAG"
}

cleanup_branches() {
    log_message "INFO" "Очистка старых локальных веток"

    git for-each-ref --format='%(refname:short)' refs/heads | \
        grep -v -E "^(main|master)$" | \
        xargs -r git branch -D >> "$LOG_FILE" 2>&1

    log_message "INFO" "Очистка отслеживаемых веток удаленного репозитория"
    git remote prune origin >> "$LOG_FILE" 2>&1

    log_message "SUCCESS" "Очистка git завершена"
}

# ============================================
# Откат миграций базы данных
# ============================================

rollback_migrations() {
    log_message "INFO" "Откат миграций базы данных к версии $TARGET_TAG"

    docker run --rm \
        --network net \
        -v ./:/app \
        -w /app \
        -e PREVIOUS_TAG="$TARGET_TAG" \
        --env-file ../$SYSTEM_REPO/env/.env.app \
        --env-file ../$SYSTEM_REPO/env/.env.db \
        --env-file ../$SYSTEM_REPO/env/.env.monitoring \
        python:3.11-slim \
        bash -c '
            echo "📦 Установка зависимостей для отката миграции..."
            cd .github && pip install -r requirements.txt > /dev/null 2>&1 && cd ..
            echo "✅ Зависимости установлены"
            echo "🔄 Откат миграций..."
            python internal/migration/run.py stage --command down --version $PREVIOUS_TAG
        ' >> "$LOG_FILE" 2>&1

    local migration_exit_code=$?

    if [ $migration_exit_code -ne 0 ]; then
        log_message "ERROR" "Откат миграций завершился с кодом ошибки $migration_exit_code"
        log_message "INFO" "Логи отката миграции (последние 50 строк):"
        tail -50 "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Откат миграций базы данных успешно завершен"
}

# ============================================
# Операции с Docker контейнерами
# ============================================

rebuild_container_for_rollback() {
    log_message "INFO" "Пересборка Docker контейнера для версии отката"

    cd ../$SYSTEM_REPO

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    log_message "INFO" "Запуск docker compose build для $SERVICE_NAME (версия отката)"
    docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME >> "$LOG_FILE" 2>&1

    if [ $? -ne 0 ]; then
        log_message "ERROR" "Не удалось собрать/запустить Docker контейнер при откате"
        log_message "INFO" "Логи Docker (последние 50 строк):"
        tail -50 "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Контейнер успешно пересобран с версией отката"
}

check_health() {
    local url="$STAGE_DOMAIN$SERVICE_PREFIX/health"
    local http_code=$(curl -f -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)

    if [ "$http_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

wait_for_health_after_rollback() {
    log_message "INFO" "Ожидание готовности сервиса после отката"

    sleep 10

    local max_attempts=5
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log_message "INFO" "Попытка проверки работоспособности $attempt/$max_attempts"

        if check_health; then
            log_message "SUCCESS" "Проверка работоспособности пройдена - сервис работает после отката"
            return 0
        else
            log_message "WARNING" "Проверка работоспособности не пройдена, ожидание 20 секунд..."
            sleep 20
        fi

        ((attempt++))
    done

    log_message "ERROR" "Проверка работоспособности не пройдена после $max_attempts попыток"
    log_message "INFO" "Логи контейнера (последние 50 строк):"
    docker logs --tail 50 $SERVICE_NAME | tee -a "$LOG_FILE"
    exit 1
}

# ============================================
# Применение миграций после отката (для текущей версии)
# ============================================

reapply_current_migrations() {
    log_message "INFO" "Повторное применение миграций для текущей версии"

    docker run --rm \
        --network net \
        -v ./:/app \
        -w /app \
        --env-file ../$SYSTEM_REPO/env/.env.app \
        --env-file ../$SYSTEM_REPO/env/.env.db \
        --env-file ../$SYSTEM_REPO/env/.env.monitoring \
        python:3.11-slim \
        bash -c '
            echo "📦 Установка зависимостей..."
            cd .github && pip install -r requirements.txt > /dev/null 2>&1 && cd ..
            echo "✅ Зависимости установлены"
            echo "🚀 Запуск миграций..."
            python internal/migration/run.py stage
        ' >> "$LOG_FILE" 2>&1

    local migration_exit_code=$?

    if [ $migration_exit_code -ne 0 ]; then
        log_message "WARNING" "Повторное применение миграций завершилось с предупреждениями"
    else
        log_message "SUCCESS" "Миграции успешно применены для текущей версии"
    fi
}

# ============================================
# Восстановление к исходной версии
# ============================================

restore_to_original() {
    log_message "INFO" "Восстановление к исходной версии после теста отката"

    cd loom/$SERVICE_NAME

    local previous_ref=$(cat /tmp/${SERVICE_NAME}_rollback_previous.txt 2>/dev/null || echo "")

    if [ -z "$previous_ref" ]; then
        log_message "WARNING" "Не найдено сохраненное состояние для восстановления"
        return 1
    fi

    log_message "INFO" "Восстановление к: $previous_ref"

    git checkout "$previous_ref" >> "$LOG_FILE" 2>&1

    if [ $? -ne 0 ]; then
        log_message "ERROR" "Не удалось восстановить предыдущее состояние: $previous_ref"
        return 1
    fi

    log_message "SUCCESS" "Восстановлено предыдущее состояние: $previous_ref"

    # Повторное применение миграций
    reapply_current_migrations

    # Пересборка контейнера
    cd ../$SYSTEM_REPO
    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    log_message "INFO" "Пересборка контейнера с исходной версией"
    docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME >> "$LOG_FILE" 2>&1

    log_message "SUCCESS" "Исходная версия полностью восстановлена"

    # Удаляем временный файл
    rm -f /tmp/${SERVICE_NAME}_rollback_previous.txt

    return 0
}

# ============================================
# Основной процесс отката
# ============================================

main() {
    init_logging
    log_message "INFO" "🔄 Начало теста отката к версии $TARGET_TAG"

    save_current_state
    update_repository_for_rollback
    checkout_rollback_tag
    cleanup_branches
    rollback_migrations
    rebuild_container_for_rollback
    wait_for_health_after_rollback

    log_message "SUCCESS" "🎉 Тест отката успешно завершён!"
    log_message "INFO" "Версия отката: $TARGET_TAG проверена"
    log_message "INFO" "Начинается восстановление исходной версии..."

    restore_to_original

    log_message "SUCCESS" "🎉 Цикл теста отката полностью завершён!"
    log_message "INFO" "Файл логов: $LOG_FILE"

    echo ""
    echo "========================================="
    echo "📋 Итоги отката (последние 30 строк):"
    echo "========================================="
    tail -30 "$LOG_FILE"
}

main
EOFMAIN
)

    local ssh_exit_code=$?

    if [ $ssh_exit_code -ne 0 ]; then
        log_error "Откат" "SSH откат завершился с кодом ошибки $ssh_exit_code"
        echo "$SSH_OUTPUT"
        exit 1
    fi

    log_success "Откат" "Тест отката успешно завершён на $STAGE_HOST"
}

# ============================================
# Обработчики после отката
# ============================================

verify_rollback_success() {
    log_success "Проверка" "Тест отката к $1 успешно завершен"
    log_info "Сервер" "$STAGE_HOST"
    log_info "Версия отката" "$1"
    log_info "Статус" "Откат протестирован, исходная версия восстановлена"
    log_info "Файл логов" "/var/log/deployments/rollback/$SERVICE_NAME/$1-rollback.log"
}

handle_rollback_failure() {
    log_error "Ошибка отката" "Тест отката к $1 завершился с ошибкой"
    log_info "Сервер" "$STAGE_HOST"
    log_info "Целевая версия" "$1"
    log_warning "Требуется действие" "Проверьте логи выше для получения детальной информации об ошибке"
    log_info "Файл логов" "/var/log/deployments/rollback/$SERVICE_NAME/$1-rollback.log"
}

# ============================================
# Высокоуровневая обёртка отката
# ============================================

rollback_with_status_tracking() {
    local target_tag=$1

    log_info "Откат" "Начало процесса тестирования отката с отслеживанием статуса"
    log_info "Целевая версия" "$target_tag"

    # Обновление статуса на начало отката
    update_release_status "stage_test_rollback"

    # Выполнение отката
    execute_rollback "$target_tag"

    if [ $? -eq 0 ]; then
        update_release_status "manual_testing"
        verify_rollback_success "$target_tag"
    else
        update_release_status "stage_rollback_test_failed"
        handle_rollback_failure "$target_tag"
        exit 1
    fi
}
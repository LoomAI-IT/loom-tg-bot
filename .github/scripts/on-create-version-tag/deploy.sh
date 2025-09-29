#!/bin/bash

source .github/scripts/load_config.sh

# ============================================
# Основная функция развертывания
# ============================================

deploy_to_server() {
    log_info "Развертывание" "Запуск развертывания $TAG_NAME на $STAGE_HOST"
    log_info "Подключение" "Подключение через SSH к root@$STAGE_HOST:22"

    SSH_OUTPUT=$(sshpass -p "$STAGE_PASSWORD" ssh -o StrictHostKeyChecking=no root@$STAGE_HOST -p 22 << 'EOFMAIN'
set -e

# ============================================
# Настройка логирования на удаленном сервере
# ============================================

LOG_DIR="/var/log/deployments/${{ env.SERVICE_NAME }}"
LOG_FILE="$LOG_DIR/${{ env.TAG_NAME }}.log"

init_logging() {
    mkdir -p "$LOG_DIR"
    echo "========================================" >> "$LOG_FILE"
    echo "Развертывание начато: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    echo "Сервис: ${{ env.SERVICE_NAME }}" >> "$LOG_FILE"
    echo "Тег: ${{ env.TAG_NAME }}" >> "$LOG_FILE"
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
# Операции с Git
# ============================================

update_repository() {
    log_message "INFO" "Обновление репозитория и получение тегов"

    cd loom/${{ env.SERVICE_NAME }}

    local current_ref=$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
    log_message "INFO" "Текущее состояние git: $current_ref"

    # Удаление локального тега, если существует
    if git tag -l | grep -q "^${{ env.TAG_NAME }}$"; then
        log_message "INFO" "Удаление существующего локального тега ${{ env.TAG_NAME }}"
        git tag -d ${{ env.TAG_NAME }} >> "$LOG_FILE" 2>&1
    fi

    # Получение обновлений с удаленного репозитория
    log_message "INFO" "Получение обновлений из origin"
    git fetch origin >> "$LOG_FILE" 2>&1

    log_message "INFO" "Принудительное обновление тегов с удаленного репозитория"
    git fetch origin --tags --force >> "$LOG_FILE" 2>&1

    # Проверка доступности тега
    if ! git tag -l | grep -q "^${{ env.TAG_NAME }}$"; then
        log_message "ERROR" "Тег ${{ env.TAG_NAME }} не найден после получения"
        log_message "INFO" "Доступные теги (последние 10):"
        git tag -l | tail -10 | tee -a "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Тег ${{ env.TAG_NAME }} доступен"
}

checkout_tag() {
    log_message "INFO" "Переключение на тег ${{ env.TAG_NAME }}"

    git checkout ${{ env.TAG_NAME }} >> "$LOG_FILE" 2>&1

    if [ $? -ne 0 ]; then
        log_message "ERROR" "Не удалось переключиться на тег ${{ env.TAG_NAME }}"
        tail -20 "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Успешно переключено на тег ${{ env.TAG_NAME }}"
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
# Миграции базы данных
# ============================================

run_migrations() {
    log_message "INFO" "Запуск миграций базы данных для stage окружения"

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    docker run --rm \
        --network net \
        -v ./:/app \
        -w /app \
        --env-file ../${{ env.SYSTEM_REPO }}/env/.env.app \
        --env-file ../${{ env.SYSTEM_REPO }}/env/.env.db \
        --env-file ../${{ env.SYSTEM_REPO }}/env/.env.monitoring \
        python:3.11-slim \
        bash -c '
            echo "📦 Установка зависимостей для миграции..."
            cd .github && pip install -r requirements.txt > /dev/null 2>&1 && cd ..
            echo "✅ Зависимости установлены"
            echo "🚀 Запуск миграций..."
            python internal/migration/run.py stage
        ' >> "$LOG_FILE" 2>&1

    local migration_exit_code=$?

    if [ $migration_exit_code -ne 0 ]; then
        log_message "ERROR" "Миграции завершились с кодом ошибки $migration_exit_code"
        log_message "INFO" "Логи миграции (последние 50 строк):"
        tail -50 "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Миграции базы данных успешно завершены"
}

# ============================================
# Операции с Docker контейнерами
# ============================================

build_container() {
    log_message "INFO" "Сборка и запуск Docker контейнера"

    cd ../${{ env.SYSTEM_REPO }}

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    log_message "INFO" "Запуск docker compose build для ${{ env.SERVICE_NAME }}"
    docker compose -f ./docker-compose/app.yaml up -d --build ${{ env.SERVICE_NAME }} >> "$LOG_FILE" 2>&1

    if [ $? -ne 0 ]; then
        log_message "ERROR" "Не удалось собрать/запустить Docker контейнер"
        log_message "INFO" "Логи Docker (последние 50 строк):"
        tail -50 "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Контейнер успешно собран и запущен"
}

check_health() {
    local url="${{ env.STAGE_DOMAIN }}${{ env.SERVICE_PREFIX }}/health"
    local http_code=$(curl -f -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)

    if [ "$http_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

wait_for_health() {
    log_message "INFO" "Ожидание готовности сервиса"

    sleep 10

    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log_message "INFO" "Попытка проверки работоспособности $attempt/$max_attempts"

        if check_health; then
            log_message "SUCCESS" "Проверка работоспособности пройдена - сервис работает"
            return 0
        else
            log_message "WARNING" "Проверка работоспособности не пройдена, ожидание 15 секунд..."
            sleep 15
        fi

        ((attempt++))
    done

    log_message "ERROR" "Проверка работоспособности не пройдена после $max_attempts попыток"
    log_message "INFO" "Логи контейнера (последние 50 строк):"
    docker logs --tail 50 ${{ env.SERVICE_NAME }} | tee -a "$LOG_FILE"
    exit 1
}

# ============================================
# Основной процесс развертывания
# ============================================

main() {
    init_logging
    log_message "INFO" "🚀 Начало развертывания тега ${{ env.TAG_NAME }}"

    update_repository
    checkout_tag
    cleanup_branches
    run_migrations
    build_container
    wait_for_health

    log_message "SUCCESS" "🎉 Развертывание успешно завершено!"
    log_message "INFO" "📁 Полный лог развертывания: $LOG_FILE"

    echo ""
    echo "========================================="
    echo "📋 Итоги развертывания (последние 20 строк):"
    echo "========================================="
    tail -20 "$LOG_FILE"
}

main
EOFMAIN
)

    local ssh_exit_code=$?

    if [ $ssh_exit_code -ne 0 ]; then
        log_error "Развертывание" "SSH развертывание завершилось с кодом ошибки $ssh_exit_code"
        echo "$SSH_OUTPUT"
        exit 1
    fi

    log_success "Развертывание" "Развертывание успешно завершено на $STAGE_HOST"
}

# ============================================
# Обработчики после развертывания
# ============================================

verify_deployment_success() {
    log_success "Проверка" "Развертывание $TAG_NAME успешно завершено"
    log_info "Сервер" "$STAGE_HOST"
    log_info "Версия" "$TAG_NAME"
    log_info "Статус" "Готово к ручному тестированию"
    log_info "Файл логов" "/var/log/deployments/$SERVICE_NAME/$TAG_NAME.log"
}

handle_deployment_failure() {
    log_error "Ошибка развертывания" "Развертывание $TAG_NAME завершилось с ошибкой"
    log_info "Сервер" "$STAGE_HOST"
    log_info "Версия" "$TAG_NAME"
    log_warning "Требуется действие" "Проверьте логи выше для получения детальной информации об ошибке"
    log_info "Файл логов" "/var/log/deployments/$SERVICE_NAME/$TAG_NAME.log"
}
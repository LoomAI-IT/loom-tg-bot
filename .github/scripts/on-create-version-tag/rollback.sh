#!/bin/bash



# ============================================
# Выполнение отката
# ============================================

execute_rollback() {
    local release_id=$1
    local service_name=$2
    local target_tag=$3
    local system_repo=$4

    log_info "Откат" "Начало отката $service_name к версии $target_tag"
    log_info "Подключение" "Подключение через SSH к root@$STAGE_HOST:22"

    SSH_OUTPUT=$(sshpass -p "$STAGE_PASSWORD" ssh -o StrictHostKeyChecking=no root@$STAGE_HOST -p 22 << EOFMAIN
set -e

# ============================================
# Настройка логирования отката на удаленном сервере
# ============================================

ROLLBACK_LOG_DIR="/var/log/deployments/rollback/$service_name"
ROLLBACK_LOG_FILE="\$ROLLBACK_LOG_DIR/${target_tag}-rollback.log"

init_rollback_logging() {
    mkdir -p "\$ROLLBACK_LOG_DIR"
    echo "========================================" >> "\$ROLLBACK_LOG_FILE"
    echo "Откат начат: \$(date '+%Y-%m-%d %H:%M:%S')" >> "\$ROLLBACK_LOG_FILE"
    echo "Сервис: $service_name" >> "\$ROLLBACK_LOG_FILE"
    echo "Целевой тег: $target_tag" >> "\$ROLLBACK_LOG_FILE"
    echo "ID релиза: $release_id" >> "\$ROLLBACK_LOG_FILE"
    echo "========================================" >> "\$ROLLBACK_LOG_FILE"
}

log_message() {
    local level=\$1
    local message=\$2
    local timestamp=\$(date '+%Y-%m-%d %H:%M:%S')
    local prefix=""

    case \$level in
        "INFO") prefix="ℹ️" ;;
        "SUCCESS") prefix="✅" ;;
        "ERROR") prefix="❌" ;;
        "WARNING") prefix="⚠️" ;;
    esac

    echo "[\$timestamp] [\$level] \$prefix \$message" | tee -a "\$ROLLBACK_LOG_FILE"
}

# ============================================
# Обновление статуса релиза (через удаленный API)
# ============================================

update_rollback_status_remote() {
    local status=\$1
    local release_tg_bot_url="${STAGE_DOMAIN}${LOOM_RELEASE_TG_BOT_PREFIX}"

    curl -s -X PATCH \
        -H "Content-Type: application/json" \
        -d "{
            \"release_id\": $release_id,
            \"status\": \"\$status\"
        }" \
        "\${release_tg_bot_url}/release" > /dev/null

    log_message "INFO" "Статус релиза обновлён на: \$status"
}

# ============================================
# Операции Git для отката
# ============================================

save_current_state() {
    cd loom/$service_name

    local current_ref=\$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
    log_message "INFO" "Текущее состояние до отката: \$current_ref"
    echo "\$current_ref" > /tmp/rollback_previous_ref.txt
}

fetch_target_tag() {
    log_message "INFO" "Получение целевого тега $target_tag для отката"

    # Удаление локального тега, если существует
    if git tag -l | grep -q "^${target_tag}\$"; then
        log_message "INFO" "Удаление существующего локального тега $target_tag"
        git tag -d $target_tag >> "\$ROLLBACK_LOG_FILE" 2>&1
    fi

    # Получение обновлений
    log_message "INFO" "Получение обновлений из удаленного репозитория"
    git fetch origin >> "\$ROLLBACK_LOG_FILE" 2>&1
    git fetch origin --tags --force >> "\$ROLLBACK_LOG_FILE" 2>&1

    # Проверка существования тега
    if ! git tag -l | grep -q "^${target_tag}\$"; then
        log_message "ERROR" "Тег $target_tag не найден в репозитории"
        log_message "INFO" "Доступные теги (последние 10):"
        git tag -l | tail -10 | tee -a "\$ROLLBACK_LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Тег $target_tag готов для отката"
}

checkout_rollback_tag() {
    log_message "INFO" "Переключение на тег $target_tag для отката"

    git checkout $target_tag >> "\$ROLLBACK_LOG_FILE" 2>&1

    if [ \$? -ne 0 ]; then
        log_message "ERROR" "Не удалось переключиться на тег $target_tag"
        exit 1
    fi

    log_message "SUCCESS" "Успешно переключено на тег $target_tag"

    # Очистка веток
    log_message "INFO" "Очистка веток"
    git for-each-ref --format='%(refname:short)' refs/heads | \
        grep -v -E "^(main|master)\$" | \
        xargs -r git branch -D >> "\$ROLLBACK_LOG_FILE" 2>&1
    git remote prune origin >> "\$ROLLBACK_LOG_FILE" 2>&1

    log_message "SUCCESS" "Очистка веток завершена"
}

# ============================================
# Откат базы данных
# ============================================

rollback_migrations() {
    log_message "INFO" "Откат миграций базы данных к версии $target_tag"

    docker run --rm \
        --network net \
        -v ./:/app \
        -w /app \
        -e PREVIOUS_TAG=$target_tag \
        --env-file ../$system_repo/env/.env.app \
        --env-file ../$system_repo/env/.env.db \
        --env-file ../$system_repo/env/.env.monitoring \
        python:3.11-slim \
        bash -c '
            echo "📦 Установка зависимостей..."
            cd .github && pip install -r requirements.txt > /dev/null 2>&1 && cd ..
            echo "✅ Зависимости установлены"
            echo "🚀 Откат миграций..."
            python internal/migration/run.py stage --command down --version '\$PREVIOUS_TAG'
        ' >> "\$ROLLBACK_LOG_FILE" 2>&1

    local migration_exit_code=\$?

    if [ \$migration_exit_code -ne 0 ]; then
        log_message "ERROR" "Откат миграций завершился с кодом ошибки \$migration_exit_code"
        tail -50 "\$ROLLBACK_LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Откат миграций завершён"
}

# ============================================
# Пересборка контейнера для отката
# ============================================

rebuild_container_for_rollback() {
    log_message "INFO" "Пересборка контейнера с версией отката $target_tag"

    cd ../$system_repo

    export \$(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    docker compose -f ./docker-compose/app.yaml up -d --build $service_name >> "\$ROLLBACK_LOG_FILE" 2>&1

    if [ \$? -ne 0 ]; then
        log_message "ERROR" "Не удалось пересобрать контейнер во время отката"
        tail -50 "\$ROLLBACK_LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Контейнер пересобран с версией отката"
    log_message "INFO" "Docker образы после отката:"
    docker images | grep $service_name | tee -a "\$ROLLBACK_LOG_FILE"
}

# ============================================
# Проверка работоспособности после отката
# ============================================

check_health_after_rollback() {
    local url="${STAGE_DOMAIN}${SERVICE_PREFIX}/health"
    local http_code=\$(curl -f -s -o /dev/null -w "%{http_code}" "\$url" 2>/dev/null)

    if [ "\$http_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

wait_for_health_after_rollback() {
    log_message "INFO" "Ожидание готовности сервиса после отката"

    sleep 15

    local max_attempts=5
    local attempt=1

    while [ \$attempt -le \$max_attempts ]; do
        log_message "INFO" "Попытка проверки работоспособности \$attempt/\$max_attempts после отката"

        if check_health_after_rollback; then
            log_message "SUCCESS" "Проверка работоспособности пройдена после отката"
            return 0
        else
            log_message "WARNING" "Проверка работоспособности не пройдена, ожидание 20 секунд..."
            sleep 20
        fi

        ((attempt++))
    done

    log_message "ERROR" "Проверка работоспособности не пройдена после \$max_attempts попыток"
    log_message "INFO" "Логи контейнера (последние 100 строк):"
    docker logs --tail 100 $service_name | tee -a "\$ROLLBACK_LOG_FILE"

    update_rollback_status_remote "stage_rollback_test_failed"
    exit 1
}

# ============================================
# Восстановление к текущей версии (после теста)
# ============================================

restore_to_current() {
    log_message "INFO" "Восстановление к текущей версии после теста отката"

    cd loom/$service_name

    local previous_ref=\$(cat /tmp/rollback_previous_ref.txt)
    log_message "INFO" "Восстановление к: \$previous_ref"

    git checkout "\$previous_ref" >> "\$ROLLBACK_LOG_FILE" 2>&1

    if [ \$? -ne 0 ]; then
        log_message "WARNING" "Не удалось восстановить предыдущее состояние: \$previous_ref"
    else
        log_message "SUCCESS" "Восстановлено предыдущее состояние: \$previous_ref"
    fi

    # Повторное выполнение миграций для текущей версии
    log_message "INFO" "Повторное применение миграций для текущей версии"

    docker run --rm \
        --network net \
        -v ./:/app \
        -w /app \
        --env-file ../$system_repo/env/.env.app \
        --env-file ../$system_repo/env/.env.db \
        --env-file ../$system_repo/env/.env.monitoring \
        python:3.11-slim \
        bash -c '
            echo "📦 Установка зависимостей..."
            cd .github && pip install -r requirements.txt > /dev/null 2>&1 && cd ..
            echo "✅ Зависимости установлены"
            echo "🚀 Запуск миграций..."
            python internal/migration/run.py stage
        ' >> "\$ROLLBACK_LOG_FILE" 2>&1

    log_message "SUCCESS" "Текущая версия восстановлена"

    rm -f /tmp/rollback_previous_ref.txt
}

# ============================================
# Основной процесс отката
# ============================================

main() {
    init_rollback_logging
    log_message "INFO" "🔄 Начало теста отката для $service_name к версии $target_tag"

    update_rollback_status_remote "stage_rollback"

    save_current_state
    fetch_target_tag
    checkout_rollback_tag
    rollback_migrations
    rebuild_container_for_rollback
    wait_for_health_after_rollback

    update_rollback_status_remote "manual_testing"

    log_message "SUCCESS" "🎉 Тест отката успешно завершён!"
    log_message "INFO" "Сервис: $service_name"
    log_message "INFO" "Версия отката: $target_tag"
    log_message "INFO" "Статус: Откат выполнен успешно"
    log_message "INFO" "Файл логов: \$ROLLBACK_LOG_FILE"

    restore_to_current

    log_message "SUCCESS" "Цикл теста отката завершён"

    echo ""
    echo "========================================="
    echo "📋 Итоги отката (последние 30 строк):"
    echo "========================================="
    tail -30 "\$ROLLBACK_LOG_FILE"
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

    log_success "Откат" "Тест отката успешно завершён для $service_name"
}

# ============================================
# Высокоуровневая обёртка отката (использует release_api)
# ============================================

rollback_with_status_tracking() {
    local release_id=$1
    local service_name=$2
    local target_tag=$3
    local system_repo=$4

    log_info "Откат" "Начало процесса отката с отслеживанием статуса"

    # Обновление статуса на начало отката
    export RELEASE_ID=$release_id
    update_release_status "stage_rollback"

    # Выполнение отката
    execute_rollback "$release_id" "$service_name" "$target_tag" "$system_repo"

    if [ $? -eq 0 ]; then
        update_release_status "manual_testing"
        verify_rollback_success "$service_name" "$target_tag"
    else
        update_release_status "stage_rollback_test_failed"
        handle_rollback_failure "$service_name" "$target_tag"
        exit 1
    fi
}

# ============================================
# Проверка отката
# ============================================

verify_rollback_success() {
    local service_name=$1
    local target_tag=$2

    log_success "Проверка отката" "Тест отката для $service_name завершён"
    log_info "Сервис" "$service_name"
    log_info "Версия отката" "$target_tag"
    log_info "Статус" "Откат выполнен успешно, текущая версия восстановлена"
    log_info "Файл логов" "/var/log/deployments/rollback/$service_name/${target_tag}-rollback.log"
}

handle_rollback_failure() {
    local service_name=$1
    local target_tag=$2

    log_error "Ошибка отката" "Тест отката для $service_name завершился с ошибкой"
    log_info "Сервис" "$service_name"
    log_info "Целевая версия" "$target_tag"
    log_warning "Требуется действие" "Проверьте логи для получения детальной информации об ошибке"
    log_info "Файл логов" "/var/log/deployments/rollback/$service_name/${target_tag}-rollback.log"
}
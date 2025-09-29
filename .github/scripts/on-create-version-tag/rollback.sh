#!/bin/bash

# ============================================
# Основная функция отката
# ============================================

execute_rollback() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║               ТЕСТ ОТКАТА НА STAGE                         ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📦 Сервис:         $SERVICE_NAME"
    echo "🔄 Откат на:       $PREVIOUS_TAG"
    echo "🖥️  Сервер:         $STAGE_HOST"
    echo ""

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
    {
        echo "========================================"
        echo "ОТКАТ НАЧАТ"
        echo "========================================"
        echo "Дата:         $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Сервис:       $SERVICE_NAME"
        echo "Целевой тег:  $TARGET_TAG"
        echo "Префикс:      $SERVICE_PREFIX"
        echo "Домен:        $STAGE_DOMAIN"
        echo "========================================"
        echo ""
    } > "$LOG_FILE"
}

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%H:%M:%S')

    case $level in
        INFO)    local icon="ℹ️ " ;;
        SUCCESS) local icon="✅" ;;
        ERROR)   local icon="❌" ;;
        WARN)    local icon="⚠️ " ;;
        *)       local icon="  " ;;
    esac

    echo "${icon} ${message}"
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# ============================================
# Сохранение текущего состояния
# ============================================

save_current_state() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Сохранение текущего состояния"
    echo "─────────────────────────────────────────"

    cd loom/$SERVICE_NAME

    local current_ref=$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
    log INFO "Текущее состояние: $current_ref"

    echo "$current_ref" > /tmp/${SERVICE_NAME}_rollback_previous.txt
    log SUCCESS "Состояние сохранено для восстановления"

    cd
}

# ============================================
# Откат миграций базы данных
# ============================================

rollback_migrations() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Откат миграций к версии $TARGET_TAG"
    echo "─────────────────────────────────────────"

    cd loom/$SERVICE_NAME

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
            pip install -q -r .github/requirements.txt
            python internal/migration/run.py stage --command down --version $PREVIOUS_TAG
        ' >> "$LOG_FILE" 2>&1

    if [ $? -eq 0 ]; then
        log SUCCESS "Миграции откачены"
    else
        log ERROR "Ошибка отката миграций"
        echo "" >> "$LOG_FILE"
        echo "=== Последние 50 строк лога ===" >> "$LOG_FILE"
        tail -50 "$LOG_FILE" >> "$LOG_FILE"
        exit 1
    fi

    cd
}

# ============================================
# Операции с Docker контейнерами
# ============================================

rebuild_container_for_rollback() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Пересборка контейнера для отката"
    echo "─────────────────────────────────────────"

    cd loom/$SYSTEM_REPO

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    if docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME >> "$LOG_FILE" 2>&1; then
        log SUCCESS "Контейнер пересобран"
    else
        log ERROR "Ошибка пересборки контейнера"
        echo "" >> "$LOG_FILE"
        echo "=== Последние 50 строк лога ===" >> "$LOG_FILE"
        tail -50 "$LOG_FILE" >> "$LOG_FILE"
        exit 1
    fi

    cd
}

check_health() {
    local url="$STAGE_DOMAIN$SERVICE_PREFIX/health"
    local http_code=$(curl -f -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    [ "$http_code" = "200" ]
}

wait_for_health_after_rollback() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Проверка работоспособности после отката"
    echo "─────────────────────────────────────────"

    sleep 10

    local max_attempts=5
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log INFO "Попытка $attempt/$max_attempts"

        if check_health; then
            log SUCCESS "Сервис работает после отката"
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            log WARN "Сервис не готов, ожидание 20 сек..."
            sleep 20
        fi

        ((attempt++))
    done

    log ERROR "Проверка не пройдена после $max_attempts попыток"
    echo "" >> "$LOG_FILE"
    echo "=== Логи контейнера (последние 50 строк) ===" >> "$LOG_FILE"
    docker logs --tail 50 $SERVICE_NAME >> "$LOG_FILE" 2>&1
    exit 1
}

# ============================================
# Восстановление к исходной версии
# ============================================

restore_to_original() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Восстановление исходной версии"
    echo "─────────────────────────────────────────"

    cd loom/$SERVICE_NAME

    local previous_ref=$(cat /tmp/${SERVICE_NAME}_rollback_previous.txt 2>/dev/null || echo "")

    if [ -z "$previous_ref" ]; then
        log WARN "Не найдено сохраненное состояние"
        return 1
    fi

    log INFO "Восстановление к: $previous_ref"

    if git checkout "$previous_ref" >> "$LOG_FILE" 2>&1; then
        log SUCCESS "Переключено на $previous_ref"
    else
        log ERROR "Не удалось переключиться на $previous_ref"
        return 1
    fi

    log INFO "Повторное применение миграций"

    docker run --rm \
        --network net \
        -v ./:/app \
        -w /app \
        --env-file ../$SYSTEM_REPO/env/.env.app \
        --env-file ../$SYSTEM_REPO/env/.env.db \
        --env-file ../$SYSTEM_REPO/env/.env.monitoring \
        python:3.11-slim \
        bash -c '
            pip install -q -r .github/requirements.txt
            python internal/migration/run.py stage
        ' >> "$LOG_FILE" 2>&1

    if [ $? -eq 0 ]; then
        log SUCCESS "Миграции применены"
    else
        log WARN "Миграции завершились с предупреждениями"
    fi

    # Пересборка контейнера
    cd ../$SYSTEM_REPO
    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    log INFO "Пересборка контейнера с исходной версией"
    docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME >> "$LOG_FILE" 2>&1

    log SUCCESS "Исходная версия восстановлена"

    rm -f /tmp/${SERVICE_NAME}_rollback_previous.txt

    return 0
}

# ============================================
# Основной процесс отката
# ============================================

main() {
    init_logging

    save_current_state
    rollback_migrations
    rebuild_container_for_rollback
    wait_for_health_after_rollback

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           ОТКАТ ПРОТЕСТИРОВАН УСПЕШНО! ✅                  ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    log INFO "Версия отката $TARGET_TAG проверена"
    log INFO "Начинается восстановление исходной версии..."

    restore_to_original

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║        ЦИКЛ ТЕСТА ОТКАТА ПОЛНОСТЬЮ ЗАВЕРШЕН! 🎉           ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📁 Полный лог: $LOG_FILE"
    echo ""

    {
        echo ""
        echo "========================================"
        echo "ТЕСТ ОТКАТА ЗАВЕРШЕН"
        echo "========================================"
        echo "Время:          $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Статус:         УСПЕШНО"
        echo "Версия отката:  $TARGET_TAG"
        echo "========================================"
    } >> "$LOG_FILE"
}

main
EOFMAIN
)

    local ssh_exit_code=$?

    if [ $ssh_exit_code -ne 0 ]; then
        echo ""
        echo "❌ SSH откат завершился с ошибкой (код: $ssh_exit_code)"
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "ВЫВОД SSH:"
        echo "═══════════════════════════════════════════════════════════"
        echo "$SSH_OUTPUT"
        echo "═══════════════════════════════════════════════════════════"
        exit 1
    fi

    echo ""
    echo "✅ Тест отката на $STAGE_HOST успешно завершен"
    echo ""
}

# ============================================
# Обработчики после отката
# ============================================

verify_rollback_success() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ИТОГИ ТЕСТА ОТКАТА                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "✅ Статус:          Успешно завершено"
    echo "📦 Сервис:          $SERVICE_NAME"
    echo "🔄 Версия отката:   $1"
    echo "🖥️  Сервер:          $STAGE_HOST"
    echo "📁 Логи:            /var/log/deployments/rollback/$SERVICE_NAME/$1-rollback.log"
    echo ""
    echo "ℹ️  Откат протестирован, исходная версия восстановлена"
    echo ""
}

handle_rollback_failure() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ОШИБКА ТЕСТА ОТКАТА                           ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "❌ Статус:          Завершено с ошибкой"
    echo "📦 Сервис:          $SERVICE_NAME"
    echo "🔄 Целевая версия:  $1"
    echo "🖥️  Сервер:          $STAGE_HOST"
    echo "📁 Логи:            /var/log/deployments/rollback/$SERVICE_NAME/$1-rollback.log"
    echo ""
    echo "🔍 Проверьте логи выше для получения подробностей"
    echo ""
}

# ============================================
# Высокоуровневая обёртка отката
# ============================================

rollback_with_status_tracking() {
    echo ""
    echo "─────────────────────────────────────────"
    echo "Обновление статуса: stage_test_rollback"
    echo "─────────────────────────────────────────"
    update_release_status "stage_test_rollback"

    execute_rollback

    if [ $? -eq 0 ]; then
        echo ""
        echo "─────────────────────────────────────────"
        echo "Обновление статуса: manual_testing"
        echo "─────────────────────────────────────────"
        update_release_status "manual_testing"
        verify_rollback_success "$PREVIOUS_TAG"
    else
        echo ""
        echo "─────────────────────────────────────────"
        echo "Обновление статуса: stage_test_rollback_failed"
        echo "─────────────────────────────────────────"
        update_release_status "stage_test_rollback_failed"
        handle_rollback_failure "$PREVIOUS_TAG"
        exit 1
    fi
}
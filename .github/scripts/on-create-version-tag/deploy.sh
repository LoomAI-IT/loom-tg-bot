#!/bin/bash

# ============================================
# Основная функция развертывания
# ============================================

deploy_to_server() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║            НАЧАЛО РАЗВЕРТЫВАНИЯ НА STAGE                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📦 Сервис:     $SERVICE_NAME"
    echo "🏷️  Версия:     $TAG_NAME"
    echo "🖥️  Сервер:     $STAGE_HOST"
    echo "🌐 Домен:      $STAGE_DOMAIN"
    echo ""

    SSH_OUTPUT=$(sshpass -p "$STAGE_PASSWORD" ssh -o StrictHostKeyChecking=no root@$STAGE_HOST -p 22 \
        SERVICE_NAME="$SERVICE_NAME" \
        TAG_NAME="$TAG_NAME" \
        SYSTEM_REPO="$SYSTEM_REPO" \
        SERVICE_PREFIX="$SERVICE_PREFIX" \
        STAGE_DOMAIN="$STAGE_DOMAIN" \
        bash << 'EOFMAIN'
set -e

# ============================================
# Настройка логирования на удаленном сервере
# ============================================

LOG_DIR="/var/log/deployments/$SERVICE_NAME"
LOG_FILE="$LOG_DIR/$TAG_NAME.log"

init_logging() {
    mkdir -p "$LOG_DIR"
    {
        echo "========================================"
        echo "РАЗВЕРТЫВАНИЕ НАЧАТО"
        echo "========================================"
        echo "Дата:    $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Сервис:  $SERVICE_NAME"
        echo "Версия:  $TAG_NAME"
        echo "Префикс: $SERVICE_PREFIX"
        echo "Домен:   $STAGE_DOMAIN"
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

    # В консоль - краткий формат
    echo "${icon} ${message}"

    # В файл - полный формат с таймстампом
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# ============================================
# Операции с Git
# ============================================

save_previous_tag() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Сохранение текущей версии для отката"
    echo "─────────────────────────────────────────"

    cd loom/$SERVICE_NAME

    local previous_tag=$(git describe --tags --exact-match 2>/dev/null || echo "")

    if [ -n "$previous_tag" ]; then
        echo "$previous_tag" > /tmp/${SERVICE_NAME}_previous_tag.txt
        log SUCCESS "Сохранен тег для отката: $previous_tag"
    else
        echo "" > /tmp/${SERVICE_NAME}_previous_tag.txt
        log WARN "Предыдущий тег не найден (возможно, первый деплой)"
    fi

    cd
}

update_repository() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Обновление репозитория"
    echo "─────────────────────────────────────────"

    cd loom/$SERVICE_NAME

    local current_ref=$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
    log INFO "Текущее состояние: $current_ref"

    # Удаление локального тега, если существует
    if git tag -l | grep -q "^$TAG_NAME$"; then
        git tag -d $TAG_NAME >> "$LOG_FILE" 2>&1
        log INFO "Удален локальный тег: $TAG_NAME"
    fi

    # Получение обновлений
    log INFO "Получение обновлений из origin..."
    git fetch origin >> "$LOG_FILE" 2>&1
    git fetch origin --tags --force >> "$LOG_FILE" 2>&1

    # Проверка доступности тега
    if ! git tag -l | grep -q "^$TAG_NAME$"; then
        log ERROR "Тег $TAG_NAME не найден после получения"
        echo "" >> "$LOG_FILE"
        echo "Доступные теги (последние 10):" >> "$LOG_FILE"
        git tag -l | tail -10 >> "$LOG_FILE"
        exit 1
    fi

    log SUCCESS "Тег $TAG_NAME получен"
    cd
}

checkout_tag() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Переключение на версию $TAG_NAME"
    echo "─────────────────────────────────────────"

    cd loom/$SERVICE_NAME

    if git checkout $TAG_NAME >> "$LOG_FILE" 2>&1; then
        log SUCCESS "Переключено на $TAG_NAME"
    else
        log ERROR "Не удалось переключиться на $TAG_NAME"
        echo "" >> "$LOG_FILE"
        echo "=== Последние 20 строк лога ===" >> "$LOG_FILE"
        tail -20 "$LOG_FILE" >> "$LOG_FILE"
        exit 1
    fi

    cd
}

cleanup_branches() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Очистка старых веток"
    echo "─────────────────────────────────────────"

    cd loom/$SERVICE_NAME

    local branches_deleted=$(git for-each-ref --format='%(refname:short)' refs/heads | \
        grep -v -E "^(main|master)$" | wc -l)

    git for-each-ref --format='%(refname:short)' refs/heads | \
        grep -v -E "^(main|master)$" | \
        xargs -r git branch -D >> "$LOG_FILE" 2>&1

    git remote prune origin >> "$LOG_FILE" 2>&1

    if [ $branches_deleted -gt 0 ]; then
        log SUCCESS "Удалено веток: $branches_deleted"
    else
        log INFO "Нет веток для удаления"
    fi

    cd
}

# ============================================
# Миграции базы данных
# ============================================

run_migrations() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Запуск миграций базы данных"
    echo "─────────────────────────────────────────"

    cd loom/$SERVICE_NAME

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
        log SUCCESS "Миграции выполнены успешно"
    else
        log ERROR "Миграции завершились с ошибкой"
        echo "" >> "$LOG_FILE"
        echo "=== Последние 50 строк лога миграций ===" >> "$LOG_FILE"
        tail -50 "$LOG_FILE" >> "$LOG_FILE"
        exit 1
    fi

    cd
}

# ============================================
# Операции с Docker контейнерами
# ============================================

build_container() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Сборка и запуск Docker контейнера"
    echo "─────────────────────────────────────────"

    cd loom/$SYSTEM_REPO

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    if docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME >> "$LOG_FILE" 2>&1; then
        log SUCCESS "Контейнер собран и запущен"
    else
        log ERROR "Ошибка сборки контейнера"
        echo "" >> "$LOG_FILE"
        echo "=== Последние 50 строк лога Docker ===" >> "$LOG_FILE"
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

wait_for_health() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Проверка работоспособности сервиса"
    echo "─────────────────────────────────────────"

    sleep 10

    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log INFO "Попытка $attempt/$max_attempts"

        if check_health; then
            log SUCCESS "Сервис работает корректно"
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            log WARN "Сервис не готов, ожидание 15 сек..."
            sleep 15
        fi

        ((attempt++))
    done

    log ERROR "Сервис не прошел проверку после $max_attempts попыток"
    echo "" >> "$LOG_FILE"
    echo "=== Логи контейнера (последние 50 строк) ===" >> "$LOG_FILE"
    docker logs --tail 50 $SERVICE_NAME >> "$LOG_FILE" 2>&1
    exit 1
}

# ============================================
# Основной процесс развертывания
# ============================================

main() {
    init_logging

    save_previous_tag
    update_repository
    checkout_tag
    cleanup_branches
    run_migrations
    build_container
    wait_for_health

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         РАЗВЕРТЫВАНИЕ УСПЕШНО ЗАВЕРШЕНО! 🎉               ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📁 Полный лог: $LOG_FILE"

    if [ -f "/tmp/${SERVICE_NAME}_previous_tag.txt" ]; then
        local saved_tag=$(cat /tmp/${SERVICE_NAME}_previous_tag.txt)
        if [ -n "$saved_tag" ]; then
            echo "💾 Для отката доступен тег: $saved_tag"
        fi
    fi
    echo ""

    # Сохраняем краткую сводку в конец лога
    {
        echo ""
        echo "========================================"
        echo "РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО"
        echo "========================================"
        echo "Время:   $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Статус:  УСПЕШНО"
        echo "Версия:  $TAG_NAME"
        echo "========================================"
    } >> "$LOG_FILE"
}

main
EOFMAIN
)

    local ssh_exit_code=$?

    if [ $ssh_exit_code -ne 0 ]; then
        echo ""
        echo "❌ SSH развертывание завершилось с ошибкой (код: $ssh_exit_code)"
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "ВЫВОД SSH:"
        echo "═══════════════════════════════════════════════════════════"
        echo "$SSH_OUTPUT"
        echo "═══════════════════════════════════════════════════════════"
        exit 1
    fi

    echo ""
    echo "✅ Развертывание на $STAGE_HOST успешно завершено"
    echo ""
}

# ============================================
# Обработчики после развертывания
# ============================================

verify_deployment_success() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ИТОГИ РАЗВЕРТЫВАНИЯ                           ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "✅ Статус:     Успешно завершено"
    echo "📦 Сервис:     $SERVICE_NAME"
    echo "🏷️  Версия:     $TAG_NAME"
    echo "🖥️  Сервер:     $STAGE_HOST"
    echo "📁 Логи:       /var/log/deployments/$SERVICE_NAME/$TAG_NAME.log"
    echo ""
    echo "👉 Следующий шаг: Ручное тестирование"
    echo ""
}

handle_deployment_failure() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ОШИБКА РАЗВЕРТЫВАНИЯ                          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "❌ Статус:     Завершено с ошибкой"
    echo "📦 Сервис:     $SERVICE_NAME"
    echo "🏷️  Версия:     $TAG_NAME"
    echo "🖥️  Сервер:     $STAGE_HOST"
    echo "📁 Логи:       /var/log/deployments/$SERVICE_NAME/$TAG_NAME.log"
    echo ""
    echo "🔍 Проверьте логи выше для получения подробностей"
    echo ""
}
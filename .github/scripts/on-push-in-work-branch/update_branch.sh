#!/bin/bash

# ============================================
# Основная функция обновления ветки
# ============================================

update_branch_on_server() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║        ОБНОВЛЕНИЕ ВЕТКИ НА DEV СЕРВЕРЕ                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📦 Сервис:      $SERVICE_NAME"
    echo "🌿 Ветка:       $BRANCH_NAME"
    echo "👤 Автор:       $AUTHOR_NAME"
    echo "🖥️  Dev сервер:  $DEV_HOST"
    echo ""

    SSH_OUTPUT=$(sshpass -p "$DEV_PASSWORD" ssh -o StrictHostKeyChecking=no root@$DEV_HOST -p 22 \
        SERVICE_NAME="$SERVICE_NAME" \
        BRANCH_NAME="$BRANCH_NAME" \
        AUTHOR_NAME="$AUTHOR_NAME" \
        SYSTEM_REPO="$SYSTEM_REPO" \
        SERVICE_PREFIX="$SERVICE_PREFIX" \
        DEV_DOMAIN="$DEV_DOMAIN" \
        bash << 'EOFMAIN'
set -e

# ============================================
# Настройка логирования на удаленном сервере
# ============================================

LOG_DIR="/var/log/deployments/dev/$SERVICE_NAME"
LOG_FILE="$LOG_DIR/$BRANCH_NAME-$(date '+%Y%m%d-%H%M%S').log"

init_logging() {
    mkdir -p "$LOG_DIR"
    {
        echo "========================================"
        echo "ОБНОВЛЕНИЕ ВЕТКИ НАЧАТО"
        echo "========================================"
        echo "Дата:         $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Сервис:       $SERVICE_NAME"
        echo "Ветка:        $BRANCH_NAME"
        echo "Автор:        $AUTHOR_NAME"
        echo "Префикс:      $SERVICE_PREFIX"
        echo "Домен:        $DEV_DOMAIN"
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
# Обновление Git репозитория
# ============================================

update_git_branch() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Обновление ветки $BRANCH_NAME"
    echo "─────────────────────────────────────────"

    cd loom/$SERVICE_NAME

    log INFO "Получение обновлений из origin"
    git fetch origin >> "$LOG_FILE" 2>&1

    # Сохраняем текущую ветку
    CURRENT_BRANCH=$(git branch --show-current)
    log INFO "Текущая ветка: $CURRENT_BRANCH"

    # Очистка старых веток
    if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
        log INFO "Очистка старых веток"

        # Переключаемся на main для безопасного удаления
        git checkout main >> "$LOG_FILE" 2>&1 || git checkout master >> "$LOG_FILE" 2>&1 || log WARN "Не удалось переключиться на main/master"

        # Удаляем все ветки кроме main/master и целевой
        local deleted_count=$(git branch | grep -v -E "(main|master|\*|$BRANCH_NAME)" | wc -l)
        git branch | grep -v -E "(main|master|\*|$BRANCH_NAME)" | xargs -r git branch -D >> "$LOG_FILE" 2>&1

        # Очищаем удаленные ветки
        git remote prune origin >> "$LOG_FILE" 2>&1

        if [ $deleted_count -gt 0 ]; then
            log SUCCESS "Удалено веток: $deleted_count"
        fi
    fi

    # Проверяем существование ветки локально
    if git show-ref --verify --quiet refs/heads/$BRANCH_NAME; then
        log INFO "Ветка существует локально, обновляем"
        git checkout $BRANCH_NAME >> "$LOG_FILE" 2>&1

        # Проверяем расхождения
        LOCAL_COMMIT=$(git rev-parse HEAD)
        REMOTE_COMMIT=$(git rev-parse origin/$BRANCH_NAME)

        if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
            log WARN "Обнаружены расхождения, принудительное обновление"
            git reset --hard origin/$BRANCH_NAME >> "$LOG_FILE" 2>&1
            log SUCCESS "Ветка обновлена до $REMOTE_COMMIT"
        else
            log SUCCESS "Ветка уже актуальна"
        fi
    else
        log INFO "Первый деплой ветки, создаем"
        git checkout -b $BRANCH_NAME origin/$BRANCH_NAME >> "$LOG_FILE" 2>&1
        log SUCCESS "Ветка создана и переключена"
    fi

    cd
}

# ============================================
# Сборка и запуск Docker контейнера
# ============================================

build_and_start_container() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Сборка и запуск контейнера"
    echo "─────────────────────────────────────────"

    cd loom/$SYSTEM_REPO

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    if docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME >> "$LOG_FILE" 2>&1; then
        log SUCCESS "Контейнер собран и запущен"
    else
        log ERROR "Ошибка сборки контейнера"
        echo "" >> "$LOG_FILE"
        echo "=== Логи контейнера (последние 50 строк) ===" >> "$LOG_FILE"
        docker logs --tail 50 $SERVICE_NAME >> "$LOG_FILE" 2>&1
        exit 1
    fi

    cd
}

# ============================================
# Проверка работоспособности
# ============================================

check_health() {
    local url="${DEV_DOMAIN}${SERVICE_PREFIX}/health"
    local http_code=$(curl -f -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    [ "$http_code" = "200" ]
}

wait_for_health() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Проверка работоспособности сервиса"
    echo "─────────────────────────────────────────"

    sleep 5

    local max_attempts=2
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log INFO "Попытка $attempt/$max_attempts"

        if check_health; then
            log SUCCESS "Сервис работает корректно"
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            log WARN "Сервис не готов, ожидание 10 сек..."
            sleep 10
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
# Основной процесс
# ============================================

main() {
    init_logging

    update_git_branch
    build_and_start_container
    wait_for_health

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║        ВЕТКА УСПЕШНО ОБНОВЛЕНА! 🎉                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    log SUCCESS "Ветка: $BRANCH_NAME"
    log SUCCESS "Автор: $AUTHOR_NAME"
    log SUCCESS "Приложение работает"
    echo ""
    echo "📁 Полный лог: $LOG_FILE"
    echo ""

    {
        echo ""
        echo "========================================"
        echo "ОБНОВЛЕНИЕ ВЕТКИ ЗАВЕРШЕНО"
        echo "========================================"
        echo "Время:          $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Статус:         УСПЕШНО"
        echo "Ветка:          $BRANCH_NAME"
        echo "Автор:          $AUTHOR_NAME"
        echo "========================================"
    } >> "$LOG_FILE"
}

main
EOFMAIN
)

    local ssh_exit_code=$?

    if [ $ssh_exit_code -ne 0 ]; then
        echo ""
        echo "❌ Обновление завершилось с ошибкой (код: $ssh_exit_code)"
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "ВЫВОД SSH:"
        echo "═══════════════════════════════════════════════════════════"
        echo "$SSH_OUTPUT"
        echo "═══════════════════════════════════════════════════════════"
        exit 1
    fi

    echo ""
    echo "✅ Обновление на $DEV_HOST успешно завершено"
    echo ""
}
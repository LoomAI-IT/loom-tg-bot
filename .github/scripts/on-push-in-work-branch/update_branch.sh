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

    # Выполняем SSH команду и выводим результат в реальном времени
    sshpass -p "$DEV_PASSWORD" ssh -o StrictHostKeyChecking=no root@$DEV_HOST -p 22 \
        SERVICE_NAME="$SERVICE_NAME" \
        BRANCH_NAME="$BRANCH_NAME" \
        AUTHOR_NAME="$AUTHOR_NAME" \
        SYSTEM_REPO="$SYSTEM_REPO" \
        SERVICE_PREFIX="$SERVICE_PREFIX" \
        DEV_DOMAIN="$DEV_DOMAIN" \
        DEV_HOST="$DEV_HOST" \
        bash << 'EOFMAIN'
set -e

# ============================================
# Настройка логирования на удаленном сервере
# ============================================

LOG_DIR="/var/log/deployments/dev/$SERVICE_NAME"
LOG_FILE="$LOG_DIR/$BRANCH_NAME.log"

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
        echo "Hostname:     $(hostname)"
        echo "User:         $(whoami)"
        echo "PWD:          $(pwd)"
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
        DEBUG)   local icon="🔍" ;;
        *)       local icon="  " ;;
    esac

    echo "${icon} ${message}"
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

log_command() {
    local cmd="$@"
    log DEBUG "Выполняется команда: $cmd"
    echo "" >> "$LOG_FILE"
    echo ">>> COMMAND: $cmd" >> "$LOG_FILE"
    eval "$cmd" 2>&1 | tee -a "$LOG_FILE"
    local exit_code=${PIPESTATUS[0]}
    echo "<<< EXIT CODE: $exit_code" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    return $exit_code
}

log_to_both() {
    local message="$@"
    echo "$message"
    echo "$message" >> "$LOG_FILE"
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
    log DEBUG "Рабочая директория: $(pwd)"

    # Информация о репозитории
    log INFO "Получение информации о репозитории"
    {
        echo "=== GIT REPOSITORY INFO ==="
        echo "Remote URL: $(git remote get-url origin 2>/dev/null || echo 'N/A')"
        echo "Current HEAD: $(git rev-parse HEAD 2>/dev/null || echo 'N/A')"
        echo "Local branches:"
        git branch -v 2>/dev/null || echo "N/A"
        echo ""
    } >> "$LOG_FILE"

    log INFO "Получение обновлений из origin"
    if log_command "git fetch origin --prune --verbose"; then
        log SUCCESS "Fetch выполнен успешно"
    else
        log ERROR "Ошибка при выполнении fetch"
        exit 1
    fi

    # Сохраняем текущую ветку
    CURRENT_BRANCH=$(git branch --show-current)
    log INFO "Текущая ветка: $CURRENT_BRANCH"

    # Информация о remote ветках
    {
        echo "=== REMOTE BRANCHES ==="
        git branch -r | head -20
        echo ""
    } >> "$LOG_FILE"

    # Очистка старых веток
    if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
        log INFO "Очистка старых веток"

        # Список веток для удаления
        local branches_to_delete=$(git branch | grep -v -E "(main|master|\*|$BRANCH_NAME)" || true)
        if [ -n "$branches_to_delete" ]; then
            {
                echo "=== BRANCHES TO DELETE ==="
                echo "$branches_to_delete"
                echo ""
            } >> "$LOG_FILE"
        fi

        # Переключаемся на main для безопасного удаления
        log INFO "Переключение на main/master"
        if git checkout main >> "$LOG_FILE" 2>&1; then
            log SUCCESS "Переключено на main"
        elif git checkout master >> "$LOG_FILE" 2>&1; then
            log SUCCESS "Переключено на master"
        else
            log WARN "Не удалось переключиться на main/master"
        fi

        # Удаляем все ветки кроме main/master и целевой
        local deleted_count=$(git branch | grep -v -E "(main|master|\*|$BRANCH_NAME)" | wc -l)
        if [ $deleted_count -gt 0 ]; then
            log INFO "Удаление $deleted_count веток"
            git branch | grep -v -E "(main|master|\*|$BRANCH_NAME)" | xargs -r git branch -D >> "$LOG_FILE" 2>&1
            log SUCCESS "Удалено веток: $deleted_count"
        else
            log INFO "Нет веток для удаления"
        fi

        # Очищаем удаленные ветки
        log INFO "Очистка удаленных веток"
        git remote prune origin >> "$LOG_FILE" 2>&1
        log SUCCESS "Remote prune выполнен"
    fi

    # Проверяем существование ветки локально
    if git show-ref --verify --quiet refs/heads/$BRANCH_NAME; then
        log INFO "Ветка существует локально, обновляем"

        if log_command "git checkout $BRANCH_NAME"; then
            log SUCCESS "Переключено на $BRANCH_NAME"
        else
            log ERROR "Не удалось переключиться на $BRANCH_NAME"
            exit 1
        fi

        # Проверяем расхождения
        LOCAL_COMMIT=$(git rev-parse HEAD)
        REMOTE_COMMIT=$(git rev-parse origin/$BRANCH_NAME)

        log INFO "Локальный коммит:  $LOCAL_COMMIT"
        log INFO "Удаленный коммит:  $REMOTE_COMMIT"

        {
            echo "=== COMMIT COMPARISON ==="
            echo "Local:  $LOCAL_COMMIT"
            echo "Remote: $REMOTE_COMMIT"
            echo ""
            echo "Last 5 commits (local):"
            git log --oneline -5 2>/dev/null || echo "N/A"
            echo ""
        } >> "$LOG_FILE"

        if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
            log WARN "Обнаружены расхождения, принудительное обновление"

            if log_command "git reset --hard origin/$BRANCH_NAME"; then
                log SUCCESS "Ветка обновлена до $REMOTE_COMMIT"
            else
                log ERROR "Ошибка при обновлении ветки"
                exit 1
            fi
        else
            log SUCCESS "Ветка уже актуальна"
        fi
    else
        log INFO "Первый деплой ветки, создаем"

        if log_command "git checkout -b $BRANCH_NAME origin/$BRANCH_NAME"; then
            log SUCCESS "Ветка создана и переключена"
        else
            log ERROR "Не удалось создать ветку"
            exit 1
        fi
    fi

    # Финальная информация
    {
        echo "=== FINAL GIT STATE ==="
        echo "Current branch: $(git branch --show-current)"
        echo "Current commit: $(git rev-parse HEAD)"
        echo "Last commit message: $(git log -1 --pretty=%B 2>/dev/null | head -1 || echo 'N/A')"
        echo ""
    } >> "$LOG_FILE"

    cd
    log DEBUG "Возврат в домашнюю директорию: $(pwd)"
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
    log DEBUG "Рабочая директория: $(pwd)"

    # Проверка наличия env файлов
    log INFO "Проверка наличия env файлов"
    for env_file in env/.env.app env/.env.db env/.env.monitoring; do
        if [ -f "$env_file" ]; then
            log SUCCESS "Найден: $env_file"
            echo "File: $env_file ($(wc -l < $env_file) lines)" >> "$LOG_FILE"
        else
            log ERROR "Отсутствует: $env_file"
            exit 1
        fi
    done

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)
    log INFO "Переменные окружения загружены"

    # Информация о текущем состоянии контейнера
    log INFO "Проверка текущего состояния контейнера"
    {
        echo "=== DOCKER STATE BEFORE BUILD ==="
        echo "Container info:"
        docker ps -a --filter "name=$SERVICE_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" 2>/dev/null || echo "Container not found"
        echo ""
        echo "Images:"
        docker images | grep "$SERVICE_NAME" | head -5 || echo "No images found"
        echo ""
    } >> "$LOG_FILE"

    # Остановка существующего контейнера если есть
    if docker ps -a --filter "name=$SERVICE_NAME" --format "{{.Names}}" | grep -q "^${SERVICE_NAME}$"; then
        log INFO "Остановка существующего контейнера"
        docker stop $SERVICE_NAME >> "$LOG_FILE" 2>&1 || true
        docker rm $SERVICE_NAME >> "$LOG_FILE" 2>&1 || true
        log SUCCESS "Контейнер остановлен и удален"
    fi

    log INFO "Запуск сборки контейнера"
    {
        echo "=== DOCKER BUILD LOG ==="
        echo "Command: docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME"
        echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""
    } >> "$LOG_FILE"

    if docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME >> "$LOG_FILE" 2>&1; then
        log SUCCESS "Контейнер собран и запущен"

        {
            echo ""
            echo "Finished at: $(date '+%Y-%m-%d %H:%M:%S')"
            echo ""
        } >> "$LOG_FILE"
    else
        log ERROR "Ошибка сборки контейнера"
        {
            echo ""
            echo "=== BUILD FAILED ==="
            echo "Finished at: $(date '+%Y-%m-%d %H:%M:%S')"
            echo ""
            echo "=== CONTAINER LOGS (last 100 lines) ==="
        } >> "$LOG_FILE"
        docker logs --tail 100 $SERVICE_NAME >> "$LOG_FILE" 2>&1
        exit 1
    fi

    # Информация о запущенном контейнере
    sleep 2
    log INFO "Сбор информации о запущенном контейнере"
    {
        echo "=== DOCKER STATE AFTER BUILD ==="
        echo "Container info:"
        docker ps --filter "name=$SERVICE_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"
        echo ""
        echo "Container inspect (key info):"
        docker inspect $SERVICE_NAME --format '
Container ID: {{.Id}}
Image: {{.Config.Image}}
Created: {{.Created}}
State: {{.State.Status}}
Started At: {{.State.StartedAt}}
Restart Count: {{.RestartCount}}
' 2>/dev/null || echo "Inspect failed"
        echo ""
    } >> "$LOG_FILE"

    cd
    log DEBUG "Возврат в домашнюю директорию: $(pwd)"
}

# ============================================
# Проверка работоспособности
# ============================================

check_health() {
    local url="${DEV_DOMAIN}${SERVICE_PREFIX}/health"
    log DEBUG "Проверка health endpoint: $url"

    local http_code=$(curl -f -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    local curl_exit=$?

    {
        echo "Health check: $url"
        echo "HTTP Code: $http_code"
        echo "Curl exit code: $curl_exit"
        echo ""
    } >> "$LOG_FILE"

    [ "$http_code" = "200" ]
}

send_telegram_notification() {
    local message=$1

    cd loom/$SYSTEM_REPO
    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)
    # Проверяем наличие скрипта уведомлений
    if [ ! -f "script/tg_bot_alert.py" ]; then
        echo "⚠️  Скрипт уведомлений не найден: script/tg_bot_alert.py"
        echo "   Пропуск отправки уведомления"
        return 0
    fi

    # Отправляем уведомление
    if python3 script/tg_bot_alert.py "$message" 2>/dev/null; then
        echo "✅ Уведомление отправлено в Telegram"
    else
        echo "⚠️  Не удалось отправить уведомление в Telegram"
    fi
    cd
}

# ============================================
# Уведомление об успешном обновлении
# ============================================

send_success_notification() {
    echo ""
    echo "─────────────────────────────────────────"
    echo "Отправка уведомления об успехе"
    echo "─────────────────────────────────────────"

    local message="✅ Ветка обновлена на dev сервере

📦 Сервис: $SERVICE_NAME
🌿 Ветка: $BRANCH_NAME
👤 Автор: $AUTHOR_NAME
🖥️  Сервер: $DEV_HOST
🌐 Домен: $DEV_DOMAIN

Приложение работает корректно!"

    send_telegram_notification "$message"
    echo ""
}

# ============================================
# Уведомление об ошибке
# ============================================

send_failure_notification() {
    echo ""
    echo "─────────────────────────────────────────"
    echo "Отправка уведомления об ошибке"
    echo "─────────────────────────────────────────"

    local action_url="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"

    local message="❌ Ошибка обновления ветки на dev сервере

📦 Сервис: $SERVICE_NAME
🌿 Ветка: $BRANCH_NAME
👤 Автор: $AUTHOR_NAME
🖥️  Сервер: $DEV_HOST

🔍 Подробности:
$action_url"
    send_telegram_notification "$message"
    echo ""
}

wait_for_health() {
    echo ""
    echo "─────────────────────────────────────────"
    log INFO "Проверка работоспособности сервиса"
    echo "─────────────────────────────────────────"

    log INFO "Ожидание инициализации (15 сек)"
    sleep 15

    local max_attempts=2
    local attempt=1

    {
        echo "=== HEALTH CHECK LOG ==="
        echo "URL: ${DEV_DOMAIN}${SERVICE_PREFIX}/health"
        echo "Max attempts: $max_attempts"
        echo ""
    } >> "$LOG_FILE"

    while [ $attempt -le $max_attempts ]; do
        log INFO "Попытка $attempt/$max_attempts"

        if check_health; then
            send_success_notification
            log SUCCESS "Сервис работает корректно"
            {
                echo "Success on attempt: $attempt"
                echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
                echo ""
            } >> "$LOG_FILE"
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            log WARN "Сервис не готов, ожидание 10 сек..."

            # Показываем логи контейнера для диагностики
            log DEBUG "Последние 20 строк логов контейнера:"
            {
                echo "=== CONTAINER LOGS (attempt $attempt) ==="
                docker logs --tail 20 $SERVICE_NAME 2>&1
                echo ""
            } >> "$LOG_FILE"

            sleep 10
        fi

        ((attempt++))
    done

    send_failure_notification
    log ERROR "Проверка не пройдена после $max_attempts попыток"

    log_to_both ""
    log_to_both "=== HEALTH CHECK FAILED ==="
    log_to_both "Failed after $max_attempts attempts"
    log_to_both "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    log_to_both ""
    log_to_both "=== FINAL CONTAINER STATE ==="
    docker ps --filter "name=$SERVICE_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1 | tee -a "$LOG_FILE"
    log_to_both ""
    log_to_both "=== CONTAINER LOGS (last 100 lines) ==="
    docker logs --tail 100 $SERVICE_NAME 2>&1 | tee -a "$LOG_FILE"
    log_to_both ""

    exit 1
}

# ============================================
# Основной процесс
# ============================================

main() {
    init_logging

    log INFO "════════════════════════════════════════"
    log INFO "Начало процесса обновления"
    log INFO "════════════════════════════════════════"

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
        echo "Commit:         $(cd loom/$SERVICE_NAME && git rev-parse HEAD)"
        echo "========================================"
        echo ""
        echo "=== SYSTEM INFO ==="
        echo "Disk usage:"
        df -h / | tail -1
        echo ""
        echo "Memory usage:"
        free -h | grep Mem
        echo ""
        echo "Docker info:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Size}}" | grep "$SERVICE_NAME" || echo "N/A"
        echo "========================================"
    } >> "$LOG_FILE"
}

main

# Возвращаем код ошибки если что-то пошло не так
exit $?
EOFMAIN

    local ssh_exit_code=$?

    if [ $ssh_exit_code -ne 0 ]; then
        echo ""
        echo "❌ Обновление завершилось с ошибкой (код: $ssh_exit_code)"
        echo ""
        echo "─────────────────────────────────────────"
        echo "Последние 100 строк логов контейнера:"
        echo "─────────────────────────────────────────"

        sshpass -p "$DEV_PASSWORD" ssh -o StrictHostKeyChecking=no root@$DEV_HOST -p 22 \
            "docker logs --tail 100 $SERVICE_NAME 2>&1 || echo 'Не удалось получить логи контейнера'"

        echo ""
        echo "─────────────────────────────────────────"
        echo "Полный лог на сервере:"
        echo "/var/log/deployments/dev/$SERVICE_NAME/$BRANCH_NAME.log"
        echo "─────────────────────────────────────────"
        exit 1
    fi

    echo ""
    echo "✅ Обновление на $DEV_HOST успешно завершено"
    echo ""
}

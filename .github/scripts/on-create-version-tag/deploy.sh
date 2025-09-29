#!/bin/bash

source .github/scripts/load_config.sh

# ============================================
# Main deployment function
# ============================================

deploy_to_server() {
    log_info "Deployment" "Starting deployment of $TAG_NAME to $STAGE_HOST"
    log_info "Connection" "Connecting via SSH to root@$STAGE_HOST:22"

    SSH_OUTPUT=$(sshpass -p "$STAGE_PASSWORD" ssh -o StrictHostKeyChecking=no root@$STAGE_HOST -p 22 << 'EOFMAIN'
set -e

# ============================================
# Remote server logging setup
# ============================================

LOG_DIR="/var/log/deployments/${{ env.SERVICE_NAME }}"
LOG_FILE="$LOG_DIR/${{ env.TAG_NAME }}.log"

init_logging() {
    mkdir -p "$LOG_DIR"
    echo "========================================" >> "$LOG_FILE"
    echo "Deployment started: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    echo "Service: ${{ env.SERVICE_NAME }}" >> "$LOG_FILE"
    echo "Tag: ${{ env.TAG_NAME }}" >> "$LOG_FILE"
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
# Git operations
# ============================================

update_repository() {
    log_message "INFO" "Updating repository and fetching tags"

    cd loom/${{ env.SERVICE_NAME }}

    local current_ref=$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
    log_message "INFO" "Current git state: $current_ref"

    # Remove local tag if exists
    if git tag -l | grep -q "^${{ env.TAG_NAME }}$"; then
        log_message "INFO" "Removing existing local tag ${{ env.TAG_NAME }}"
        git tag -d ${{ env.TAG_NAME }} >> "$LOG_FILE" 2>&1
    fi

    # Fetch updates from remote
    log_message "INFO" "Fetching updates from origin"
    git fetch origin >> "$LOG_FILE" 2>&1

    log_message "INFO" "Forcing tag update from remote"
    git fetch origin --tags --force >> "$LOG_FILE" 2>&1

    # Verify tag is available
    if ! git tag -l | grep -q "^${{ env.TAG_NAME }}$"; then
        log_message "ERROR" "Tag ${{ env.TAG_NAME }} not found after fetch"
        log_message "INFO" "Available tags (last 10):"
        git tag -l | tail -10 | tee -a "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Tag ${{ env.TAG_NAME }} is available"
}

checkout_tag() {
    log_message "INFO" "Checking out tag ${{ env.TAG_NAME }}"

    git checkout ${{ env.TAG_NAME }} >> "$LOG_FILE" 2>&1

    if [ $? -ne 0 ]; then
        log_message "ERROR" "Failed to checkout tag ${{ env.TAG_NAME }}"
        tail -20 "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Successfully checked out tag ${{ env.TAG_NAME }}"
}

cleanup_branches() {
    log_message "INFO" "Cleaning up old local branches"

    git for-each-ref --format='%(refname:short)' refs/heads | \
        grep -v -E "^(main|master)$" | \
        xargs -r git branch -D >> "$LOG_FILE" 2>&1

    log_message "INFO" "Pruning remote-tracking branches"
    git remote prune origin >> "$LOG_FILE" 2>&1

    log_message "SUCCESS" "Git cleanup completed"
}

# ============================================
# Database migrations
# ============================================

run_migrations() {
    log_message "INFO" "Running database migrations for stage environment"

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
            echo "📦 Installing migration dependencies..."
            cd .github && pip install -r requirements.txt > /dev/null 2>&1 && cd ..
            echo "✅ Dependencies installed"
            echo "🚀 Running migrations..."
            python internal/migration/run.py stage
        ' >> "$LOG_FILE" 2>&1

    local migration_exit_code=$?

    if [ $migration_exit_code -ne 0 ]; then
        log_message "ERROR" "Migrations failed with exit code $migration_exit_code"
        log_message "INFO" "Migration logs (last 50 lines):"
        tail -50 "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Database migrations completed successfully"
}

# ============================================
# Docker container operations
# ============================================

build_container() {
    log_message "INFO" "Building and starting Docker container"

    cd ../${{ env.SYSTEM_REPO }}

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    log_message "INFO" "Running docker compose build for ${{ env.SERVICE_NAME }}"
    docker compose -f ./docker-compose/app.yaml up -d --build ${{ env.SERVICE_NAME }} >> "$LOG_FILE" 2>&1

    if [ $? -ne 0 ]; then
        log_message "ERROR" "Docker container build/start failed"
        log_message "INFO" "Docker logs (last 50 lines):"
        tail -50 "$LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Container built and started successfully"
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
    log_message "INFO" "Waiting for service to become healthy"

    sleep 10

    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log_message "INFO" "Health check attempt $attempt/$max_attempts"

        if check_health; then
            log_message "SUCCESS" "Health check passed - service is running"
            return 0
        else
            log_message "WARNING" "Health check failed, waiting 15 seconds..."
            sleep 15
        fi

        ((attempt++))
    done

    log_message "ERROR" "Health check failed after $max_attempts attempts"
    log_message "INFO" "Container logs (last 50 lines):"
    docker logs --tail 50 ${{ env.SERVICE_NAME }} | tee -a "$LOG_FILE"
    exit 1
}

# ============================================
# Main deployment flow
# ============================================

main() {
    init_logging
    log_message "INFO" "🚀 Starting deployment of tag ${{ env.TAG_NAME }}"

    update_repository
    checkout_tag
    cleanup_branches
    run_migrations
    build_container
    wait_for_health

    log_message "SUCCESS" "🎉 Deployment completed successfully!"
    log_message "INFO" "📁 Full deployment log: $LOG_FILE"

    echo ""
    echo "========================================="
    echo "📋 Deployment Summary (last 20 lines):"
    echo "========================================="
    tail -20 "$LOG_FILE"
}

main
EOFMAIN
)

    local ssh_exit_code=$?

    if [ $ssh_exit_code -ne 0 ]; then
        log_error "Deployment" "SSH deployment failed with exit code $ssh_exit_code"
        echo "$SSH_OUTPUT"
        exit 1
    fi

    log_success "Deployment" "Deployment completed successfully on $STAGE_HOST"
}

# ============================================
# Post-deployment handlers
# ============================================

verify_deployment_success() {
    log_success "Verification" "Deployment of $TAG_NAME completed successfully"
    log_info "Server" "$STAGE_HOST"
    log_info "Version" "$TAG_NAME"
    log_info "Status" "Ready for manual testing"
    log_info "Log File" "/var/log/deployments/$SERVICE_NAME/$TAG_NAME.log"
}

handle_deployment_failure() {
    log_error "Deployment Failed" "Deployment of $TAG_NAME failed"
    log_info "Server" "$STAGE_HOST"
    log_info "Version" "$TAG_NAME"
    log_warning "Action Required" "Check logs above for detailed error information"
    log_info "Log File" "/var/log/deployments/$SERVICE_NAME/$TAG_NAME.log"
}
#!/bin/bash

source .github/scripts/load_config.sh
source .github/scripts/release_api.sh

# ============================================
# Rollback execution
# ============================================

execute_rollback() {
    local release_id=$1
    local service_name=$2
    local target_tag=$3
    local system_repo=$4

    log_info "Rollback" "Starting rollback for $service_name to version $target_tag"
    log_info "Connection" "Connecting via SSH to root@$STAGE_HOST:22"

    SSH_OUTPUT=$(sshpass -p "$STAGE_PASSWORD" ssh -o StrictHostKeyChecking=no root@$STAGE_HOST -p 22 << EOFMAIN
set -e

# ============================================
# Remote rollback logging setup
# ============================================

ROLLBACK_LOG_DIR="/var/log/deployments/rollback/$service_name"
ROLLBACK_LOG_FILE="\$ROLLBACK_LOG_DIR/${target_tag}-rollback.log"

init_rollback_logging() {
    mkdir -p "\$ROLLBACK_LOG_DIR"
    echo "========================================" >> "\$ROLLBACK_LOG_FILE"
    echo "Rollback started: \$(date '+%Y-%m-%d %H:%M:%S')" >> "\$ROLLBACK_LOG_FILE"
    echo "Service: $service_name" >> "\$ROLLBACK_LOG_FILE"
    echo "Target tag: $target_tag" >> "\$ROLLBACK_LOG_FILE"
    echo "Release ID: $release_id" >> "\$ROLLBACK_LOG_FILE"
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
# Update release status (using remote API)
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

    log_message "INFO" "Release status updated to: \$status"
}

# ============================================
# Git operations for rollback
# ============================================

save_current_state() {
    cd loom/$service_name

    local current_ref=\$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
    log_message "INFO" "Current state before rollback: \$current_ref"
    echo "\$current_ref" > /tmp/rollback_previous_ref.txt
}

fetch_target_tag() {
    log_message "INFO" "Fetching target tag $target_tag for rollback"

    # Remove local tag if exists
    if git tag -l | grep -q "^${target_tag}\$"; then
        log_message "INFO" "Removing existing local tag $target_tag"
        git tag -d $target_tag >> "\$ROLLBACK_LOG_FILE" 2>&1
    fi

    # Fetch updates
    log_message "INFO" "Fetching updates from remote repository"
    git fetch origin >> "\$ROLLBACK_LOG_FILE" 2>&1
    git fetch origin --tags --force >> "\$ROLLBACK_LOG_FILE" 2>&1

    # Verify tag exists
    if ! git tag -l | grep -q "^${target_tag}\$"; then
        log_message "ERROR" "Tag $target_tag not found in repository"
        log_message "INFO" "Available tags (last 10):"
        git tag -l | tail -10 | tee -a "\$ROLLBACK_LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Tag $target_tag is ready for rollback"
}

checkout_rollback_tag() {
    log_message "INFO" "Checking out tag $target_tag for rollback"

    git checkout $target_tag >> "\$ROLLBACK_LOG_FILE" 2>&1

    if [ \$? -ne 0 ]; then
        log_message "ERROR" "Failed to checkout tag $target_tag"
        exit 1
    fi

    log_message "SUCCESS" "Successfully checked out tag $target_tag"

    # Cleanup branches
    log_message "INFO" "Cleaning up branches"
    git for-each-ref --format='%(refname:short)' refs/heads | \
        grep -v -E "^(main|master)\$" | \
        xargs -r git branch -D >> "\$ROLLBACK_LOG_FILE" 2>&1
    git remote prune origin >> "\$ROLLBACK_LOG_FILE" 2>&1

    log_message "SUCCESS" "Branch cleanup completed"
}

# ============================================
# Database rollback
# ============================================

rollback_migrations() {
    log_message "INFO" "Rolling back database migrations to $target_tag"

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
            echo "📦 Installing dependencies..."
            cd .github && pip install -r requirements.txt > /dev/null 2>&1 && cd ..
            echo "✅ Dependencies installed"
            echo "🚀 Rolling back migrations..."
            python internal/migration/run.py stage --command down --version '\$PREVIOUS_TAG'
        ' >> "\$ROLLBACK_LOG_FILE" 2>&1

    local migration_exit_code=\$?

    if [ \$migration_exit_code -ne 0 ]; then
        log_message "ERROR" "Migration rollback failed with exit code \$migration_exit_code"
        tail -50 "\$ROLLBACK_LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Migration rollback completed"
}

# ============================================
# Container rebuild for rollback
# ============================================

rebuild_container_for_rollback() {
    log_message "INFO" "Rebuilding container with rollback version $target_tag"

    cd ../$system_repo

    export \$(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    docker compose -f ./docker-compose/app.yaml up -d --build $service_name >> "\$ROLLBACK_LOG_FILE" 2>&1

    if [ \$? -ne 0 ]; then
        log_message "ERROR" "Container rebuild failed during rollback"
        tail -50 "\$ROLLBACK_LOG_FILE"
        exit 1
    fi

    log_message "SUCCESS" "Container rebuilt with rollback version"
    log_message "INFO" "Docker images after rollback:"
    docker images | grep $service_name | tee -a "\$ROLLBACK_LOG_FILE"
}

# ============================================
# Health check after rollback
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
    log_message "INFO" "Waiting for service health after rollback"

    sleep 15

    local max_attempts=5
    local attempt=1

    while [ \$attempt -le \$max_attempts ]; do
        log_message "INFO" "Health check attempt \$attempt/\$max_attempts after rollback"

        if check_health_after_rollback; then
            log_message "SUCCESS" "Health check passed after rollback"
            return 0
        else
            log_message "WARNING" "Health check failed, waiting 20 seconds..."
            sleep 20
        fi

        ((attempt++))
    done

    log_message "ERROR" "Health check failed after \$max_attempts attempts"
    log_message "INFO" "Container logs (last 100 lines):"
    docker logs --tail 100 $service_name | tee -a "\$ROLLBACK_LOG_FILE"

    update_rollback_status_remote "stage_rollback_test_failed"
    exit 1
}

# ============================================
# Restore to current version (after test)
# ============================================

restore_to_current() {
    log_message "INFO" "Restoring to current version after rollback test"

    cd loom/$service_name

    local previous_ref=\$(cat /tmp/rollback_previous_ref.txt)
    log_message "INFO" "Restoring to: \$previous_ref"

    git checkout "\$previous_ref" >> "\$ROLLBACK_LOG_FILE" 2>&1

    if [ \$? -ne 0 ]; then
        log_message "WARNING" "Failed to restore to previous state: \$previous_ref"
    else
        log_message "SUCCESS" "Restored to previous state: \$previous_ref"
    fi

    # Re-run migrations for current version
    log_message "INFO" "Re-applying migrations for current version"

    docker run --rm \
        --network net \
        -v ./:/app \
        -w /app \
        --env-file ../$system_repo/env/.env.app \
        --env-file ../$system_repo/env/.env.db \
        --env-file ../$system_repo/env/.env.monitoring \
        python:3.11-slim \
        bash -c '
            echo "📦 Installing dependencies..."
            cd .github && pip install -r requirements.txt > /dev/null 2>&1 && cd ..
            echo "✅ Dependencies installed"
            echo "🚀 Running migrations..."
            python internal/migration/run.py stage
        ' >> "\$ROLLBACK_LOG_FILE" 2>&1

    log_message "SUCCESS" "Current version restored"

    rm -f /tmp/rollback_previous_ref.txt
}

# ============================================
# Main rollback flow
# ============================================

main() {
    init_rollback_logging
    log_message "INFO" "🔄 Starting rollback test for $service_name to $target_tag"

    update_rollback_status_remote "stage_rollback"

    save_current_state
    fetch_target_tag
    checkout_rollback_tag
    rollback_migrations
    rebuild_container_for_rollback
    wait_for_health_after_rollback

    update_rollback_status_remote "manual_testing"

    log_message "SUCCESS" "🎉 Rollback test completed successfully!"
    log_message "INFO" "Service: $service_name"
    log_message "INFO" "Rollback version: $target_tag"
    log_message "INFO" "Status: Rollback successful"
    log_message "INFO" "Log file: \$ROLLBACK_LOG_FILE"

    restore_to_current

    log_message "SUCCESS" "Rollback test cycle completed"

    echo ""
    echo "========================================="
    echo "📋 Rollback Summary (last 30 lines):"
    echo "========================================="
    tail -30 "\$ROLLBACK_LOG_FILE"
}

main
EOFMAIN
)

    local ssh_exit_code=$?

    if [ $ssh_exit_code -ne 0 ]; then
        log_error "Rollback" "SSH rollback failed with exit code $ssh_exit_code"
        echo "$SSH_OUTPUT"
        exit 1
    fi

    log_success "Rollback" "Rollback test completed successfully for $service_name"
}

# ============================================
# High-level rollback wrapper (uses release_api)
# ============================================

rollback_with_status_tracking() {
    local release_id=$1
    local service_name=$2
    local target_tag=$3
    local system_repo=$4

    log_info "Rollback" "Starting rollback process with status tracking"

    # Update status to rollback started
    export RELEASE_ID=$release_id
    update_release_status "stage_rollback"

    # Execute rollback
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
# Rollback verification
# ============================================

verify_rollback_success() {
    local service_name=$1
    local target_tag=$2

    log_success "Rollback Verification" "Rollback test for $service_name completed"
    log_info "Service" "$service_name"
    log_info "Rollback Version" "$target_tag"
    log_info "Status" "Rollback successful, current version restored"
    log_info "Log File" "/var/log/deployments/rollback/$service_name/${target_tag}-rollback.log"
}

handle_rollback_failure() {
    local service_name=$1
    local target_tag=$2

    log_error "Rollback Failed" "Rollback test for $service_name failed"
    log_info "Service" "$service_name"
    log_info "Target Version" "$target_tag"
    log_warning "Action Required" "Check logs for detailed error information"
    log_info "Log File" "/var/log/deployments/rollback/$service_name/${target_tag}-rollback.log"
}
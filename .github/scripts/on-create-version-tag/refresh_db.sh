#!/bin/bash

source .github/scripts/load_config.sh

# ============================================
# Database table operations
# ============================================

refresh_database_table() {
    local service_prefix=$1
    local service_name=$2

    log_info "Database" "Refreshing $service_name database tables..."

    local drop_url="${STAGE_DOMAIN}${service_prefix}/table/drop"
    local create_url="${STAGE_DOMAIN}${service_prefix}/table/create"

    # Drop existing table
    log_info "Database" "Dropping $service_name tables..."
    local drop_response=$(curl -s -w "\n%{http_code}" -X GET "$drop_url")
    local drop_code=$(echo "$drop_response" | tail -n1)
    local drop_body=$(echo "$drop_response" | head -n -1)

    if [ "$drop_code" -ne 200 ]; then
        log_warning "Database" "Failed to drop $service_name table (HTTP $drop_code)"
        log_info "Response" "$drop_body"
    else
        log_success "Database" "$service_name tables dropped"
    fi

    # Create new table
    log_info "Database" "Creating $service_name tables..."
    local create_response=$(curl -s -w "\n%{http_code}" -X GET "$create_url")
    local create_code=$(echo "$create_response" | tail -n1)
    local create_body=$(echo "$create_response" | head -n -1)

    if [ "$create_code" -ne 200 ]; then
        log_error "Database" "Failed to create $service_name table (HTTP $create_code)"
        log_info "Response" "$create_body"
        return 1
    fi

    log_success "Database" "$service_name tables created successfully"
    return 0
}

# ============================================
# Batch database refresh
# ============================================

refresh_all_databases() {
    log_info "Database Refresh" "Starting database refresh for all services..."
    log_info "Target" "Stage domain: $STAGE_DOMAIN"

    # Define all services to refresh
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

    log_info "Progress" "Processing $total service databases..."

    for service_info in "${services[@]}"; do
        IFS=':' read -r prefix name <<< "$service_info"

        if refresh_database_table "$prefix" "$name"; then
            ((success++))
        else
            ((failed++))
        fi

        echo "" # Empty line for readability
    done

    # Summary
    log_info "Summary" "Completed: $success successful, $failed failed out of $total total"

    if [ $failed -gt 0 ]; then
        log_error "Database Refresh" "$failed service(s) failed to refresh"
        exit 1
    fi

    log_success "Database Refresh" "All $total databases refreshed successfully"
}
#!/bin/bash

# ============================================
# Logging utilities
# ============================================

log_info() {
    local title=$1
    local message=$2
    echo "::notice title=$title::$message"
    echo "ℹ️  $message"
}

log_success() {
    local title=$1
    local message=$2
    echo "::notice title=$title::$message"
    echo "✅ $message"
}

log_error() {
    local title=$1
    local message=$2
    echo "::error title=$title::$message"
    echo "❌ $message"
}

log_warning() {
    local title=$1
    local message=$2
    echo "::warning title=$title::$message"
    echo "⚠️  $message"
}

# ============================================
# Configuration validation
# ============================================

validate_env_var() {
    local var_name=$1
    local var_value=$2
    local error_message=$3

    if [ -z "$var_value" ]; then
        log_error "Configuration Error" "$error_message"
        log_info "Required Variable" "Missing: $var_name"
        exit 1
    fi
}

export_to_github_env() {
    local var_name=$1
    local var_value=$2
    echo "$var_name=$var_value" >> $GITHUB_ENV
}

# ============================================
# Main configuration loader
# ============================================

load_server_config() {
    log_info "Configuration" "Loading server configuration..."

    local config_file="/root/.env.runner"

    # Check if config file exists
    if [ ! -f "$config_file" ]; then
        log_error "Configuration Error" "Server configuration file not found: $config_file"
        exit 1
    fi

    # Load environment variables from config file
    set -a
    source "$config_file"
    set +a

    log_success "Configuration" "Environment variables loaded from $config_file"

    # Validate required API configuration
    validate_env_var "STAGE_DOMAIN" "$STAGE_DOMAIN" "STAGE_DOMAIN not configured in .env.runner"
    validate_env_var "PROD_DOMAIN" "$PROD_DOMAIN" "PROD_DOMAIN not configured in .env.runner"

    # Validate stage server configuration
    validate_env_var "STAGE_HOST" "$STAGE_HOST" "STAGE_HOST not configured in .env.runner"
    validate_env_var "STAGE_PASSWORD" "$STAGE_PASSWORD" "STAGE_PASSWORD not configured in .env.runner"

    log_success "Validation" "All required configuration variables present"

    # Extract and build service prefix
    SERVICE_PREFIX=$(echo "$SERVICE_NAME" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
    SERVICE_PREFIX_VAR_NAME="${SERVICE_PREFIX}_PREFIX"
    SERVICE_PREFIX="${!SERVICE_PREFIX_VAR_NAME}"

    log_info "Service" "Service prefix resolved: $SERVICE_PREFIX"

    # Export main configuration to GitHub environment
    export_to_github_env "SERVICE_PREFIX" "$SERVICE_PREFIX"
    export_to_github_env "STAGE_HOST" "$STAGE_HOST"
    export_to_github_env "STAGE_PASSWORD" "$STAGE_PASSWORD"
    export_to_github_env "STAGE_DOMAIN" "$STAGE_DOMAIN"
    export_to_github_env "PROD_DOMAIN" "$PROD_DOMAIN"

    # Export service-specific prefixes
    export_to_github_env "LOOM_TG_BOT_PREFIX" "$LOOM_TG_BOT_PREFIX"
    export_to_github_env "LOOM_ACCOUNT_PREFIX" "$LOOM_ACCOUNT_PREFIX"
    export_to_github_env "LOOM_AUTHORIZATION_PREFIX" "$LOOM_AUTHORIZATION_PREFIX"
    export_to_github_env "LOOM_EMPLOYEE_PREFIX" "$LOOM_EMPLOYEE_PREFIX"
    export_to_github_env "LOOM_ORGANIZATION_PREFIX" "$LOOM_ORGANIZATION_PREFIX"
    export_to_github_env "LOOM_CONTENT_PREFIX" "$LOOM_CONTENT_PREFIX"
    export_to_github_env "LOOM_RELEASE_TG_BOT_PREFIX" "$LOOM_RELEASE_TG_BOT_PREFIX"
    export_to_github_env "LOOM_INTERSERVER_SECRET_KEY" "$LOOM_INTERSERVER_SECRET_KEY"

    log_success "Configuration" "All variables exported to GitHub environment"
    log_info "Details" "Service: $SERVICE_NAME | Prefix: $SERVICE_PREFIX"
    log_info "Details" "Stage host: $STAGE_HOST | Stage domain: $STAGE_DOMAIN"
    log_info "Details" "Production domain: $PROD_DOMAIN"
}
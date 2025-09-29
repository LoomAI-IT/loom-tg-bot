#!/bin/bash

source .github/scripts/load_config.sh

# ============================================
# API utilities
# ============================================

api_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_code=$4

    log_info "API Request" "Making $method request to $endpoint"

    local response=$(curl -s -w "\n%{http_code}" -X "$method" \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)

    if [ "$http_code" -ne "$expected_code" ]; then
        log_error "API Error" "Request failed with HTTP $http_code (expected $expected_code)"
        log_info "Response Body" "$body"
        return 1
    fi

    log_success "API Request" "Request successful (HTTP $http_code)"
    echo "$body"
    return 0
}

extract_json_value() {
    local json=$1
    local key=$2
    echo "$json" | grep -o "\"$key\":[0-9]*" | sed "s/\"$key\"://"
}

# ============================================
# Release record management
# ============================================

create_release_record() {
    log_info "Release Record" "Creating release record for $SERVICE_NAME:$TAG_NAME"
    log_info "Details" "Initiated by: $GITHUB_ACTOR | Run ID: $GITHUB_RUN_ID"

    local payload=$(cat <<EOF
{
    "service_name": "$SERVICE_NAME",
    "release_tag": "$TAG_NAME",
    "status": "initiated",
    "initiated_by": "$GITHUB_ACTOR",
    "github_run_id": "$GITHUB_RUN_ID",
    "github_action_link": "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID",
    "github_ref": "$GITHUB_REF"
}
EOF
)

    local endpoint="${PROD_DOMAIN}${LOOM_RELEASE_TG_BOT_PREFIX}/release"
    local response=$(api_request "POST" "$endpoint" "$payload" 201)

    if [ $? -ne 0 ]; then
        log_error "Release Record" "Failed to create release record"
        exit 1
    fi

    # Extract release ID from response
    local release_id=$(extract_json_value "$response" "release_id")

    if [ -z "$release_id" ]; then
        log_error "Release Record" "Failed to extract release ID from response"
        log_info "Response" "$response"
        exit 1
    fi

    # Export release ID to GitHub environment
    echo "RELEASE_ID=$release_id" >> $GITHUB_ENV

    log_success "Release Record" "Created release record with ID: $release_id"
    log_info "Status" "Initial status: initiated"
}

update_release_status() {
    local new_status=$1

    if [ -z "$RELEASE_ID" ]; then
        log_warning "Release Status" "RELEASE_ID not set, skipping status update"
        return 0
    fi

    log_info "Release Status" "Updating release #$RELEASE_ID status: $new_status"

    local payload=$(cat <<EOF
{
    "release_id": $RELEASE_ID,
    "status": "$new_status"
}
EOF
)

    local endpoint="${PROD_DOMAIN}${LOOM_RELEASE_TG_BOT_PREFIX}/release"

    local response=$(curl -s -w "\n%{http_code}" -X PATCH \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 204 ]; then
        log_success "Release Status" "Status successfully updated to: $new_status"
    else
        log_warning "Release Status" "Failed to update status (HTTP $http_code)"
        log_info "Response" "$(echo "$response" | head -n -1)"
    fi
}
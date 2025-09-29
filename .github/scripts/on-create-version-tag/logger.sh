#!/bin/bash

# ============================================
# Утилиты логирования
# ============================================

log_info() {
    local title=$1
    local message=$2
    echo "ℹ️  $message"
}

log_success() {
    local title=$1
    local message=$2
    echo "✅ $message"
}

log_error() {
    local title=$1
    local message=$2
    echo "❌ $message"
}

log_debug() {
    local title=$1
    local message=$2
    echo "[DEBUG] $message"
}

log_warning() {
    local title=$1
    local message=$2
    echo "⚠️  $message"
}

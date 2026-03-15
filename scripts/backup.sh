#!/bin/bash

################################################################################
# Database Backup Script for Personal Finance Tracker
################################################################################
# This script performs PostgreSQL backups with optional compression and
# encryption, maintains backup rotation, and supports monitoring via exit codes.
################################################################################

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-.backups}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-finance_user}"
POSTGRES_DB="${POSTGRES_DB:-finance_db}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
LOG_FILE="${BACKUP_DIR}/backup.log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"
BACKUP_META="${BACKUP_DIR}/backup_${TIMESTAMP}.meta"

# Exit codes
EXIT_SUCCESS=0
EXIT_ERROR=1
EXIT_ROTATION_ERROR=2
EXIT_ENCRYPTION_ERROR=3
EXIT_DIR_ERROR=4

################################################################################
# Functions
################################################################################

log_message() {
    local level=$1
    shift
    local message="$@"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $message" | tee -a "$LOG_FILE"
}

log_error() {
    log_message "ERROR" "$@" >&2
}

log_info() {
    log_message "INFO" "$@"
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        log_message "DEBUG" "$@"
    fi
}

init_backup_directory() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_info "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR" || {
            log_error "Failed to create backup directory: $BACKUP_DIR"
            return $EXIT_DIR_ERROR
        }
    fi

    if [[ ! -w "$BACKUP_DIR" ]]; then
        log_error "Backup directory is not writable: $BACKUP_DIR"
        return $EXIT_DIR_ERROR
    fi

    return $EXIT_SUCCESS
}

check_dependencies() {
    local required_cmds=("pg_dump" "gzip")

    if [[ -n "$BACKUP_ENCRYPTION_KEY" ]]; then
        required_cmds+=("gpg")
    fi

    for cmd in "${required_cmds[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            return $EXIT_ERROR
        fi
    done

    return $EXIT_SUCCESS
}

wait_for_database() {
    local max_attempts=30
    local attempt=1

    log_info "Waiting for PostgreSQL to be ready..."

    while [[ $attempt -le $max_attempts ]]; do
        if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" &> /dev/null; then
            log_info "PostgreSQL is ready"
            return $EXIT_SUCCESS
        fi

        log_debug "Attempt $attempt/$max_attempts: PostgreSQL not ready yet"
        ((attempt++))
        sleep 1
    done

    log_error "PostgreSQL did not become ready after $max_attempts attempts"
    return $EXIT_ERROR
}

perform_backup() {
    log_info "Starting backup of database: $POSTGRES_DB"

    local dump_cmd=(
        pg_dump
        -h "$POSTGRES_HOST"
        -p "$POSTGRES_PORT"
        -U "$POSTGRES_USER"
        -d "$POSTGRES_DB"
        --verbose
        --no-password
    )

    if ! PGPASSWORD="${PGPASSWORD:-}" "${dump_cmd[@]}" | gzip -9 > "$BACKUP_FILE" 2>> "$LOG_FILE"; then
        log_error "Backup failed"
        rm -f "$BACKUP_FILE" "$BACKUP_META"
        return $EXIT_ERROR
    fi

    local backup_size=$(du -h "$BACKUP_FILE" | cut -f1)
    log_info "Backup created successfully: $BACKUP_FILE ($backup_size)"

    return $EXIT_SUCCESS
}

encrypt_backup() {
    if [[ -z "$BACKUP_ENCRYPTION_KEY" ]]; then
        log_debug "Encryption disabled"
        return $EXIT_SUCCESS
    fi

    log_info "Encrypting backup with GPG..."

    local encrypted_file="${BACKUP_FILE}.gpg"

    if ! gpg --symmetric --cipher-algo AES256 \
            --batch --passphrase "$BACKUP_ENCRYPTION_KEY" \
            --output "$encrypted_file" "$BACKUP_FILE" 2>> "$LOG_FILE"; then
        log_error "Encryption failed"
        rm -f "$BACKUP_FILE" "$encrypted_file" "$BACKUP_META"
        return $EXIT_ENCRYPTION_ERROR
    fi

    rm -f "$BACKUP_FILE"
    BACKUP_FILE="$encrypted_file"
    log_info "Backup encrypted: $BACKUP_FILE"

    return $EXIT_SUCCESS
}

create_backup_metadata() {
    local backup_size=$(du -h "$BACKUP_FILE" | cut -f1)
    local file_hash=$(sha256sum "$BACKUP_FILE" | cut -d' ' -f1)

    cat > "$BACKUP_META" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "database": "$POSTGRES_DB",
  "host": "$POSTGRES_HOST",
  "backup_file": "$(basename "$BACKUP_FILE")",
  "backup_size": "$backup_size",
  "file_hash": "$file_hash",
  "encrypted": $(if [[ -n "$BACKUP_ENCRYPTION_KEY" ]]; then echo "true"; else echo "false"; fi),
  "status": "success"
}
EOF

    log_info "Metadata file created: $BACKUP_META"
    return $EXIT_SUCCESS
}

rotate_backups() {
    log_info "Rotating old backups (keeping last $BACKUP_RETENTION_DAYS days)..."

    local find_cmd="find $BACKUP_DIR -maxdepth 1 -name 'backup_*.sql.gz*' -o -name 'backup_*.meta'"
    local old_backups=$(eval "$find_cmd" -mtime +$BACKUP_RETENTION_DAYS 2>/dev/null || echo "")

    if [[ -z "$old_backups" ]]; then
        log_info "No old backups to rotate"
        return $EXIT_SUCCESS
    fi

    local count=0
    while IFS= read -r backup_file; do
        if [[ -f "$backup_file" ]]; then
            log_info "Removing old backup: $backup_file"
            rm -f "$backup_file" || {
                log_error "Failed to remove backup: $backup_file"
                return $EXIT_ROTATION_ERROR
            }
            ((count++))
        fi
    done <<< "$old_backups"

    log_info "Rotated $count old backup(s)"
    return $EXIT_SUCCESS
}

generate_summary() {
    log_info "============================================"
    log_info "Backup Summary"
    log_info "============================================"
    log_info "Database: $POSTGRES_DB"
    log_info "Host: $POSTGRES_HOST"
    log_info "Backup file: $(basename "$BACKUP_FILE")"
    log_info "Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
    log_info "Timestamp: $TIMESTAMP"
    log_info "============================================"
}

cleanup_on_failure() {
    log_error "Backup process failed. Cleaning up..."
    rm -f "$BACKUP_FILE" "$BACKUP_META"
}

################################################################################
# Main execution
################################################################################

main() {
    log_info "Starting backup process..."

    # Initialize backup directory
    init_backup_directory || {
        cleanup_on_failure
        return $EXIT_DIR_ERROR
    }

    # Check dependencies
    check_dependencies || {
        cleanup_on_failure
        return $EXIT_ERROR
    }

    # Wait for database
    wait_for_database || {
        cleanup_on_failure
        return $EXIT_ERROR
    }

    # Perform backup
    perform_backup || {
        cleanup_on_failure
        return $EXIT_ERROR
    }

    # Encrypt backup if key is provided
    encrypt_backup || {
        cleanup_on_failure
        return $EXIT_ENCRYPTION_ERROR
    }

    # Create metadata file
    create_backup_metadata || {
        cleanup_on_failure
        return $EXIT_ERROR
    }

    # Rotate old backups
    rotate_backups || {
        log_error "Backup rotation failed, but backup was successful"
        return $EXIT_ROTATION_ERROR
    }

    # Generate summary
    generate_summary

    log_info "Backup process completed successfully"
    return $EXIT_SUCCESS
}

# Run main function and capture exit code
main
exit_code=$?

exit $exit_code

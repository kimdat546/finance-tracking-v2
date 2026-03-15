#!/bin/bash

################################################################################
# Database Restore Script for Personal Finance Tracker
################################################################################
# This script restores PostgreSQL databases from backups created by backup.sh.
# Supports encrypted backups with GPG and provides backup validation.
################################################################################

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-.backups}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-finance_user}"
POSTGRES_DB="${POSTGRES_DB:-finance_db}"
BACKUP_ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
LOG_FILE="${BACKUP_DIR}/restore.log"
DRY_RUN="${DRY_RUN:-false}"

# Exit codes
EXIT_SUCCESS=0
EXIT_ERROR=1
EXIT_VALIDATION_ERROR=2
EXIT_DECRYPTION_ERROR=3
EXIT_BACKUP_NOT_FOUND=4
EXIT_RESTORE_ERROR=5

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

log_warning() {
    log_message "WARNING" "$@"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Restore a PostgreSQL database from a backup file.

OPTIONS:
    -f, --file FILE           Backup file to restore from
    -b, --backup-dir DIR      Backup directory (default: $BACKUP_DIR)
    -l, --latest              Restore from latest backup
    -L, --list                List available backups
    -d, --database DB         Database name (default: $POSTGRES_DB)
    -h, --host HOST           PostgreSQL host (default: $POSTGRES_HOST)
    -p, --port PORT           PostgreSQL port (default: $POSTGRES_PORT)
    -u, --user USER           PostgreSQL user (default: $POSTGRES_USER)
    --dry-run                 Show what would be done without executing
    --validate-only           Only validate the backup without restoring
    --help                    Show this help message

EXAMPLES:
    # Restore from specific backup
    $0 --file backup_20240315_120000.sql.gz

    # Restore from latest backup
    $0 --latest

    # List available backups
    $0 --list

    # Validate backup
    $0 --file backup_20240315_120000.sql.gz --validate-only

EOF
    exit 0
}

init_backup_directory() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_error "Backup directory does not exist: $BACKUP_DIR"
        return $EXIT_BACKUP_NOT_FOUND
    fi

    return $EXIT_SUCCESS
}

check_dependencies() {
    local required_cmds=("psql" "gunzip" "sha256sum")

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

list_backups() {
    log_info "Available backups:"
    log_info "============================================"

    if ! ls -lhS "${BACKUP_DIR}"/backup_*.sql.gz* "${BACKUP_DIR}"/backup_*.meta 2>/dev/null | \
         awk '{print $9, "(" $5 ")"}'; then
        log_warning "No backups found in $BACKUP_DIR"
    fi

    log_info "============================================"
    return $EXIT_SUCCESS
}

get_latest_backup() {
    local latest_backup
    latest_backup=$(find "$BACKUP_DIR" -maxdepth 1 -name "backup_*.sql.gz*" -type f | \
                   sort -r | head -n1)

    if [[ -z "$latest_backup" ]]; then
        log_error "No backup files found in $BACKUP_DIR"
        return $EXIT_BACKUP_NOT_FOUND
    fi

    echo "$latest_backup"
    return $EXIT_SUCCESS
}

validate_backup_file() {
    local backup_file=$1

    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return $EXIT_BACKUP_NOT_FOUND
    fi

    log_info "Validating backup file: $backup_file"

    # Check metadata file
    local meta_file="${backup_file%.sql.gz*}.meta"
    if [[ ! -f "$meta_file" ]]; then
        log_warning "Metadata file not found: $meta_file"
    else
        log_info "Metadata:"
        cat "$meta_file" | sed 's/^/  /'
    fi

    # Verify backup integrity
    if [[ "$backup_file" == *.gpg ]]; then
        log_info "Backup is encrypted with GPG"
        if [[ -z "$BACKUP_ENCRYPTION_KEY" ]]; then
            log_error "Backup is encrypted but no encryption key provided"
            return $EXIT_DECRYPTION_ERROR
        fi
    fi

    log_info "Backup file validation passed"
    return $EXIT_SUCCESS
}

decrypt_backup() {
    local encrypted_file=$1
    local temp_dir
    temp_dir=$(mktemp -d)
    local decrypted_file="$temp_dir/backup.sql.gz"

    log_info "Decrypting backup file..."

    if ! gpg --decrypt --batch --passphrase "$BACKUP_ENCRYPTION_KEY" \
            --output "$decrypted_file" "$encrypted_file" 2>> "$LOG_FILE"; then
        log_error "Failed to decrypt backup file"
        rm -rf "$temp_dir"
        return $EXIT_DECRYPTION_ERROR
    fi

    echo "$decrypted_file"
    return $EXIT_SUCCESS
}

prepare_backup_for_restore() {
    local backup_file=$1
    local temp_dir
    temp_dir=$(mktemp -d)
    local sql_file="$temp_dir/backup.sql"

    log_info "Preparing backup file for restore..."

    # Handle encrypted backups
    if [[ "$backup_file" == *.gpg ]]; then
        local temp_encrypted="$temp_dir/encrypted.sql.gz"
        if ! gpg --decrypt --batch --passphrase "$BACKUP_ENCRYPTION_KEY" \
                --output "$temp_encrypted" "$backup_file" 2>> "$LOG_FILE"; then
            log_error "Failed to decrypt backup"
            rm -rf "$temp_dir"
            return $EXIT_DECRYPTION_ERROR
        fi
        backup_file="$temp_encrypted"
    fi

    # Decompress
    if ! gunzip -c "$backup_file" > "$sql_file" 2>> "$LOG_FILE"; then
        log_error "Failed to decompress backup"
        rm -rf "$temp_dir"
        return $EXIT_ERROR
    fi

    echo "$sql_file"
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

get_database_size() {
    local size
    size=$(PGPASSWORD="${PGPASSWORD:-}" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
           -U "$POSTGRES_USER" -d postgres -t -c \
           "SELECT pg_size_pretty(pg_database.datsize) FROM pg_database WHERE datname = '$POSTGRES_DB';" 2>/dev/null || echo "unknown")
    echo "$size"
}

backup_current_database() {
    log_warning "Creating backup of current database before restore..."
    local backup_file="${BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"

    if ! PGPASSWORD="${PGPASSWORD:-}" pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip -9 > "$backup_file" 2>> "$LOG_FILE"; then
        log_error "Failed to create pre-restore backup"
        return $EXIT_ERROR
    fi

    log_info "Pre-restore backup created: $backup_file"
    return $EXIT_SUCCESS
}

restore_database() {
    local sql_file=$1

    log_info "Starting database restore..."
    log_info "Target database: $POSTGRES_DB"
    log_info "Host: $POSTGRES_HOST:$POSTGRES_PORT"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would restore from: $sql_file"
        return $EXIT_SUCCESS
    fi

    # Backup current database first
    if ! backup_current_database; then
        log_error "Pre-restore backup failed"
        return $EXIT_ERROR
    fi

    log_warning "This will restore the database from the backup file."
    log_warning "Any data not in the backup will be lost."
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Restore cancelled by user"
        return $EXIT_SUCCESS
    fi

    # Perform restore
    if ! PGPASSWORD="${PGPASSWORD:-}" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$sql_file" >> "$LOG_FILE" 2>&1; then
        log_error "Database restore failed"
        return $EXIT_RESTORE_ERROR
    fi

    log_info "Database restore completed successfully"
    return $EXIT_SUCCESS
}

cleanup_temp_files() {
    local temp_dir=$1
    if [[ -d "$temp_dir" ]]; then
        log_debug "Cleaning up temporary files: $temp_dir"
        rm -rf "$temp_dir"
    fi
}

generate_restore_summary() {
    log_info "============================================"
    log_info "Restore Summary"
    log_info "============================================"
    log_info "Database: $POSTGRES_DB"
    log_info "Host: $POSTGRES_HOST:$POSTGRES_PORT"
    log_info "Database size: $(get_database_size)"
    log_info "Restore timestamp: $(date -Iseconds)"
    log_info "============================================"
}

################################################################################
# Main execution
################################################################################

main() {
    local backup_file=""
    local list_only=false
    local validate_only=false
    local use_latest=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--file)
                backup_file="$2"
                shift 2
                ;;
            -l|--latest)
                use_latest=true
                shift
                ;;
            -L|--list)
                list_only=true
                shift
                ;;
            -b|--backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            -d|--database)
                POSTGRES_DB="$2"
                shift 2
                ;;
            -h|--host)
                POSTGRES_HOST="$2"
                shift 2
                ;;
            -p|--port)
                POSTGRES_PORT="$2"
                shift 2
                ;;
            -u|--user)
                POSTGRES_USER="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --validate-only)
                validate_only=true
                shift
                ;;
            --help)
                usage
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                ;;
        esac
    done

    log_info "Starting restore process..."

    # Initialize
    init_backup_directory || return $EXIT_BACKUP_NOT_FOUND
    check_dependencies || return $EXIT_ERROR

    # List backups if requested
    if [[ "$list_only" == "true" ]]; then
        list_backups
        return $EXIT_SUCCESS
    fi

    # Determine backup file
    if [[ "$use_latest" == "true" ]]; then
        backup_file=$(get_latest_backup) || return $?
        log_info "Using latest backup: $backup_file"
    fi

    if [[ -z "$backup_file" ]]; then
        log_error "No backup file specified. Use -f/--file or -l/--latest"
        return $EXIT_BACKUP_NOT_FOUND
    fi

    # Convert to absolute path
    if [[ ! "$backup_file" =~ ^/ ]]; then
        backup_file="$BACKUP_DIR/$backup_file"
    fi

    # Validate backup
    validate_backup_file "$backup_file" || return $?

    # Only validate if requested
    if [[ "$validate_only" == "true" ]]; then
        log_info "Validation only - skipping restore"
        return $EXIT_SUCCESS
    fi

    # Wait for database
    wait_for_database || return $EXIT_ERROR

    # Prepare backup
    local sql_file
    sql_file=$(prepare_backup_for_restore "$backup_file") || return $?

    # Restore database
    restore_database "$sql_file" || {
        cleanup_temp_files "$(dirname "$sql_file")"
        return $EXIT_RESTORE_ERROR
    }

    # Cleanup
    cleanup_temp_files "$(dirname "$sql_file")"

    # Generate summary
    generate_restore_summary

    log_info "Restore process completed successfully"
    return $EXIT_SUCCESS
}

# Run main function and capture exit code
main "$@"
exit_code=$?

exit $exit_code

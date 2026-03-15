#!/bin/bash
set -euo pipefail

# Restore Script for Discord AI Bot
# Restores backups of volumes and configuration

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check arguments
if [ $# -lt 1 ]; then
    log_error "Usage: $0 <backup_directory>"
    log_info "Example: $0 backups/20260313-120000"
    exit 1
fi

BACKUP_DIR="$1"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed."
    exit 1
fi

# Verify backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    log_error "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Verify backup files exist
if [ ! -f "$BACKUP_DIR/data.tar.gz" ]; then
    log_error "data.tar.gz not found in backup directory."
    exit 1
fi

if [ ! -f "$BACKUP_DIR/logs.tar.gz" ]; then
    log_error "logs.tar.gz not found in backup directory."
    exit 1
fi

# Warning
log_warn "WARNING: This will overwrite existing data!"
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Restore cancelled."
    exit 0
fi

# Stop services
log_info "Stopping services..."
docker-compose down

# Restore bot-data volume
log_info "Restoring bot-data volume..."
docker run --rm \
    -v bot-data:/data \
    -v "$(pwd)/$BACKUP_DIR:/backup" \
    alpine sh -c "rm -rf /data/* && tar xzf /backup/data.tar.gz -C /"

if [ $? -eq 0 ]; then
    log_info "bot-data volume restored successfully."
else
    log_error "Failed to restore bot-data volume."
    exit 1
fi

# Restore bot-logs volume
log_info "Restoring bot-logs volume..."
docker run --rm \
    -v bot-logs:/logs \
    -v "$(pwd)/$BACKUP_DIR:/backup" \
    alpine sh -c "rm -rf /logs/* && tar xzf /backup/logs.tar.gz -C /"

if [ $? -eq 0 ]; then
    log_info "bot-logs volume restored successfully."
else
    log_error "Failed to restore bot-logs volume."
    exit 1
fi

# Restore .env file
if [ -f "$BACKUP_DIR/.env.enc" ]; then
    log_info "Encrypted .env backup found."
    read -sp "Enter decryption password: " DECRYPT_PASSWORD
    echo ""
    
    echo "$DECRYPT_PASSWORD" | openssl enc -aes-256-cbc -d -pbkdf2 \
        -in "$BACKUP_DIR/.env.enc" -out .env -pass stdin
    
    if [ $? -eq 0 ]; then
        log_info ".env file restored and decrypted successfully."
    else
        log_error "Failed to decrypt .env file. Incorrect password?"
        exit 1
    fi
elif [ -f "$BACKUP_DIR/.env.backup" ]; then
    log_info "Unencrypted .env backup found."
    cp "$BACKUP_DIR/.env.backup" .env
    log_info ".env file restored successfully."
else
    log_warn "No .env backup found in backup directory."
fi

# Restart services
log_info "Starting services..."
docker-compose up -d

log_info "Restore completed successfully!"
log_info "Services are starting. Check status with: ./scripts/deploy.sh status"
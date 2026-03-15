#!/bin/bash
set -euo pipefail

# Backup Script for Discord AI Bot
# Creates encrypted backups of volumes and configuration

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

# Configuration
BACKUP_DIR="backups/$(date +%Y%m%d-%H%M%S)"
ENCRYPTION_PASSWORD="${BACKUP_ENCRYPTION_PASSWORD:-}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed."
    exit 1
fi

# Create backup directory
log_info "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Backup bot-data volume
log_info "Backing up bot-data volume..."
docker run --rm \
    -v bot-data:/data \
    -v "$(pwd)/$BACKUP_DIR:/backup" \
    alpine tar czf /backup/data.tar.gz /data

if [ $? -eq 0 ]; then
    log_info "bot-data volume backed up successfully."
else
    log_error "Failed to backup bot-data volume."
    exit 1
fi

# Backup bot-logs volume
log_info "Backing up bot-logs volume..."
docker run --rm \
    -v bot-logs:/logs \
    -v "$(pwd)/$BACKUP_DIR:/backup" \
    alpine tar czf /backup/logs.tar.gz /logs

if [ $? -eq 0 ]; then
    log_info "bot-logs volume backed up successfully."
else
    log_error "Failed to backup bot-logs volume."
    exit 1
fi

# Backup .env file (encrypted if password provided)
if [ -f ".env" ]; then
    log_info "Backing up .env file..."
    if [ -n "$ENCRYPTION_PASSWORD" ]; then
        log_info "Encrypting .env backup..."
        echo "$ENCRYPTION_PASSWORD" | openssl enc -aes-256-cbc -salt -pbkdf2 \
            -in .env -out "$BACKUP_DIR/.env.enc" -pass stdin
        if [ $? -eq 0 ]; then
            log_info ".env file backed up and encrypted successfully."
        else
            log_error "Failed to encrypt .env file."
            exit 1
        fi
    else
        log_warn "No encryption password provided. Copying .env without encryption."
        log_warn "Set BACKUP_ENCRYPTION_PASSWORD environment variable for encrypted backups."
        cp .env "$BACKUP_DIR/.env.backup"
    fi
else
    log_warn ".env file not found. Skipping."
fi

# Create backup manifest
cat > "$BACKUP_DIR/manifest.txt" <<EOF
Backup created: $(date)
Backup directory: $BACKUP_DIR

Contents:
- data.tar.gz: bot-data volume backup
- logs.tar.gz: bot-logs volume backup
- .env.enc: encrypted environment configuration (if encryption password was provided)
- .env.backup: environment configuration backup (if no encryption password)

To restore:
1. Extract volume backups:
   docker run --rm -v bot-data:/data -v \$(pwd)/$BACKUP_DIR:/backup alpine tar xzf /backup/data.tar.gz -C /
   docker run --rm -v bot-logs:/logs -v \$(pwd)/$BACKUP_DIR:/backup alpine tar xzf /backup/logs.tar.gz -C /

2. Decrypt .env file (if encrypted):
   openssl enc -aes-256-cbc -d -pbkdf2 -in $BACKUP_DIR/.env.enc -out .env -pass pass:YOUR_PASSWORD

3. Restart services:
   ./scripts/deploy.sh restart
EOF

log_info "Backup manifest created."
log_info "Backup completed successfully!"
log_info "Backup location: $BACKUP_DIR"
log_info ""
log_info "Total backup size:"
du -sh "$BACKUP_DIR"
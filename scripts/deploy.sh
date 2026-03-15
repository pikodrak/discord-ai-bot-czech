#!/bin/bash
set -euo pipefail

# Discord AI Bot - Docker Deployment Script
# This script handles building and deploying the Discord bot container

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="discord-ai-bot-czech"
IMAGE_NAME="discord-ai-bot"
CONTAINER_NAME="discord-ai-bot-czech"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    if [ ! -f ".env" ]; then
        log_warn ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warn "Please edit .env file with your configuration before continuing."
            exit 1
        else
            log_error ".env.example not found. Cannot create .env file."
            exit 1
        fi
    fi
    
    log_info "Prerequisites check passed."
}

build_image() {
    log_info "Building Docker image..."
    docker-compose build --no-cache
    log_info "Docker image built successfully."
}

start_services() {
    log_info "Starting services..."
    docker-compose up -d
    log_info "Services started successfully."
}

stop_services() {
    log_info "Stopping services..."
    docker-compose down
    log_info "Services stopped successfully."
}

restart_services() {
    log_info "Restarting services..."
    docker-compose restart
    log_info "Services restarted successfully."
}

view_logs() {
    log_info "Viewing logs (Ctrl+C to exit)..."
    docker-compose logs -f
}

check_health() {
    log_info "Checking service health..."
    
    # Wait for container to start
    sleep 5
    
    # Check if container is running
    if docker ps | grep -q "$CONTAINER_NAME"; then
        log_info "Container is running."
        
        # Check health endpoint
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            log_info "Health check passed - API is responding."
        else
            log_warn "Health check failed - API is not responding yet."
            log_info "Check logs with: $0 logs"
        fi
    else
        log_error "Container is not running."
        log_info "Check logs with: $0 logs"
        exit 1
    fi
}

show_status() {
    log_info "Service status:"
    docker-compose ps
}

# Main script
case "${1:-help}" in
    build)
        check_prerequisites
        build_image
        ;;
    start)
        check_prerequisites
        start_services
        check_health
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        check_health
        ;;
    logs)
        view_logs
        ;;
    status)
        show_status
        ;;
    health)
        check_health
        ;;
    deploy)
        check_prerequisites
        build_image
        stop_services
        start_services
        check_health
        show_status
        ;;
    *)
        echo "Discord AI Bot - Deployment Script"
        echo ""
        echo "Usage: $0 {build|start|stop|restart|logs|status|health|deploy}"
        echo ""
        echo "Commands:"
        echo "  build    - Build Docker image"
        echo "  start    - Start services"
        echo "  stop     - Stop services"
        echo "  restart  - Restart services"
        echo "  logs     - View service logs"
        echo "  status   - Show service status"
        echo "  health   - Check service health"
        echo "  deploy   - Full deployment (build + stop + start)"
        echo ""
        exit 1
        ;;
esac

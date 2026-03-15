#!/bin/bash
set -euo pipefail

# Docker Image Push Script
# Pushes the built image to a container registry

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
IMAGE_NAME="discord-ai-bot"
REGISTRY="${DOCKER_REGISTRY:-docker.io}"
REPOSITORY="${DOCKER_REPOSITORY:-your-username}"
VERSION="${1:-latest}"

FULL_IMAGE_NAME="${REGISTRY}/${REPOSITORY}/${IMAGE_NAME}:${VERSION}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed."
    exit 1
fi

# Check if image exists locally
if ! docker images | grep -q "$IMAGE_NAME"; then
    log_error "Image $IMAGE_NAME not found locally. Please build it first."
    log_info "Run: docker-compose build"
    exit 1
fi

# Tag the image
log_info "Tagging image as $FULL_IMAGE_NAME..."
docker tag "${IMAGE_NAME}:latest" "$FULL_IMAGE_NAME"

# Login to registry (if credentials provided)
if [ -n "${DOCKER_USERNAME:-}" ] && [ -n "${DOCKER_PASSWORD:-}" ]; then
    log_info "Logging into registry $REGISTRY..."
    echo "$DOCKER_PASSWORD" | docker login "$REGISTRY" -u "$DOCKER_USERNAME" --password-stdin
fi

# Push the image
log_info "Pushing image to registry..."
docker push "$FULL_IMAGE_NAME"

log_info "Image pushed successfully!"
log_info "Pull command: docker pull $FULL_IMAGE_NAME"

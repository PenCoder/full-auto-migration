#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build_linux.sh — Build a double-clickable AppImage using Docker.
#
# Requires: Docker (works on Windows/macOS/Linux).
# Output:   dist/MigrationWizard-x86_64.AppImage  (~120 MB, self-contained)
#
# Usage:
#   bash build_linux.sh            # build AppImage
#   bash build_linux.sh --clean    # wipe dist/ before building
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="migration-wizard-builder"
DIST_DIR="$SCRIPT_DIR/dist"
OUTPUT="MigrationWizard-x86_64.AppImage"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[build]${NC} $*"; }
success() { echo -e "${GREEN}[done] ${NC} $*"; }

if [[ "${1:-}" == "--clean" ]]; then
    info "Removing previous dist/…"
    rm -rf "$DIST_DIR"
fi

mkdir -p "$DIST_DIR"

info "Building Docker image ($IMAGE_NAME)…"
docker build \
    --target builder \
    --tag "$IMAGE_NAME:latest" \
    "$SCRIPT_DIR"

info "Extracting $OUTPUT from container…"
CONTAINER_ID=$(docker create "$IMAGE_NAME:latest")
docker cp "$CONTAINER_ID:/build/dist/$OUTPUT" "$DIST_DIR/$OUTPUT"
docker rm "$CONTAINER_ID" > /dev/null

chmod +x "$DIST_DIR/$OUTPUT"

success "AppImage ready:  $DIST_DIR/$OUTPUT"
echo ""
echo "  Copy to USB stick and double-click on Linux Mint — no installation needed."
echo "  The bundle folder (data/restore/) must also be on the USB stick."

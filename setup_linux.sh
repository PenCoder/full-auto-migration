#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# setup_linux.sh — Bootstrap the Migration Wizard on Linux Mint (or Ubuntu).
#
# Usage:
#   bash setup_linux.sh            # install deps + launch Qt wizard
#   bash setup_linux.sh --cli      # install deps + open CLI help
#   bash setup_linux.sh --restore /path/to/bundle   # run headless restore
#
# This script is designed to be run from a USB stick or a copied project
# folder on a fresh Linux Mint installation.  It installs all system and
# Python dependencies then launches the tool automatically.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_MIN_MINOR=10   # requires Python 3.10+

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Parse arguments ───────────────────────────────────────────────────────────
MODE="gui"
BUNDLE_PATH=""
for arg in "$@"; do
    case "$arg" in
        --cli)     MODE="cli" ;;
        --restore) MODE="restore" ;;
        /*)        BUNDLE_PATH="$arg" ;;   # absolute path treated as bundle dir
        *)         ;;
    esac
done

echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║   Windows → Linux Migration Wizard — Setup       ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""

# ── Check Python version ──────────────────────────────────────────────────────
info "Checking Python version…"
PYTHON_BIN=""
for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" &>/dev/null; then
        VERSION=$("$candidate" -c 'import sys; print(sys.version_info.minor)')
        MAJOR=$("$candidate"  -c 'import sys; print(sys.version_info.major)')
        if [ "$MAJOR" -eq 3 ] && [ "$VERSION" -ge "$PYTHON_MIN_MINOR" ]; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    error "Python 3.${PYTHON_MIN_MINOR}+ is required but was not found."
    info  "Install it with:  sudo apt install python3.11"
    exit 1
fi
success "Found $($PYTHON_BIN --version)"

# ── Install system dependencies for PySide6 ───────────────────────────────────
info "Installing system Qt/graphics libraries (requires sudo)…"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libegl1 \
    libdbus-1-3 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    python3-venv \
    2>/dev/null || warn "Some system packages could not be installed — the app may still work."
success "System libraries ready."

# ── Create virtual environment ────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    info "Creating Python virtual environment at $VENV_DIR…"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    success "Virtual environment created."
else
    info "Virtual environment already exists — skipping creation."
fi

PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

# ── Install Python dependencies ───────────────────────────────────────────────
info "Installing Python dependencies…"
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -r "$SCRIPT_DIR/requirements.txt"
success "Python dependencies installed."

# ── Launch ────────────────────────────────────────────────────────────────────
echo ""
case "$MODE" in
    gui)
        info "Launching Migration Wizard (Qt UI)…"
        cd "$SCRIPT_DIR"
        exec "$PYTHON" app.py
        ;;
    cli)
        success "Setup complete. Run CLI commands with:"
        echo ""
        echo "  source $VENV_DIR/bin/activate"
        echo "  python -m src.cli --help"
        echo ""
        echo "Useful restore commands:"
        echo "  python -m src.cli restore --source /path/to/bundle"
        echo "  python -m src.cli validate"
        echo "  python -m src.cli report"
        ;;
    restore)
        if [ -z "$BUNDLE_PATH" ]; then
            error "Provide the bundle folder path:  bash setup_linux.sh --restore /path/to/bundle"
            exit 1
        fi
        info "Running headless restore from $BUNDLE_PATH…"
        cd "$SCRIPT_DIR"
        exec "$PYTHON" -m src.cli restore --source "$BUNDLE_PATH"
        ;;
esac

#!/bin/bash
# run_bot.sh - Optimized bot launcher with .env support
# Usage: ./run_bot.sh [swap|noswap|fast]

set -euo pipefail

# Configuration
PROJECT_DIR="${HOME}/Dev/Ai/ai-agent"
SWAP_MODE="${1:-swap}"
BOT_NAME="ai-agent"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +%H:%M:%S)] ERROR:${NC} $1"; }

# ==================== LOAD .ENV ====================

cd "${PROJECT_DIR}" || { error "Failed to cd to ${PROJECT_DIR}"; exit 1; }

# Load .env file if exists
ENV_FILE="${PROJECT_DIR}/.env"
if [ -f "${ENV_FILE}" ]; then
    log "📄 Loading .env from ${ENV_FILE}"

    # Export all variables from .env (ignore comments and empty lines)
    set -a  # Automatically export all variables
    source "${ENV_FILE}"
    set +a  # Stop auto-export

    log "✅ Environment loaded"
    log "   Token: ${TELEGRAM_BOT_TOKEN:0:10}..."
    log "   Model: ${OLLAMA_MODEL:-llama3.2:latest}"
else
    warn "No .env file found at ${ENV_FILE}"
    warn "Create one from .env.example"
fi

# ==================== VALIDATE REQUIRED VARS ====================

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    error "TELEGRAM_BOT_TOKEN not set in .env"
    exit 1
fi

if [ -z "${ALLOWED_TELEGRAM_USERS:-}" ]; then
    warn "ALLOWED_TELEGRAM_USERS not set, allowing all users"
fi

# ==================== CLEANUP ====================

log "🤖 Starting ${BOT_NAME} (Mode: ${SWAP_MODE})"
echo "=================================================="

log "Cleaning up old processes..."
pkill -f "python.*main\.py" 2>/dev/null || true
pkill -f "poetry run python" 2>/dev/null || true
sleep 3

if pgrep -f "python.*main\.py" > /dev/null 2>&1; then
    warn "Force killing..."
    pkill -9 -f "python.*main\.py" 2>/dev/null || true
    sleep 2
fi

log "✅ Cleanup complete"

# ==================== PYTHON & OLLAMA SETTINGS ====================

export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Ollama settings (can be overridden in .env)
export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-30m}"
export OLLAMA_NUM_THREADS="${OLLAMA_NUM_THREADS:-4}"
export OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-2}"

# Mode-specific overrides
case "${SWAP_MODE}" in
    "swap")
        log "💾 Mode: Standard (swap enabled)"
        export OLLAMA_NUM_GPU=0
        export OLLAMA_MAX_LOADED_MODELS=2
        ;;
    "noswap")
        log "🚫 Mode: No swap (light models)"
        export OLLAMA_MAX_LOADED_MODELS=1
        export OLLAMA_DEFAULT_MODEL="llama3.2:latest"
        ;;
    "fast")
        log "⚡ Mode: Fast (minimal memory)"
        export OLLAMA_MAX_LOADED_MODELS=1
        export OLLAMA_KEEP_ALIVE="10m"
        export OLLAMA_NUM_THREADS=2
        ;;
esac

# ==================== START ====================

log "🚀 Starting bot with model: ${OLLAMA_MODEL:-llama3.2:latest}"
echo "=================================================="

exec poetry run python main.py
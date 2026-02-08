#!/bin/bash
# restart_bot.sh - Optimized restart with .env support and swap control
# Usage: ./restart_bot.sh [swap|noswap|fast|status|stop]

set -euo pipefail

# Configuration
PROJECT_DIR="${HOME}/Dev/Ai/ai-agent"
cd "${PROJECT_DIR}" || { echo "❌ Failed to cd to ${PROJECT_DIR}"; exit 1; }

CMD="${1:-swap}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)]${NC} $1"; }
error() { echo -e "${RED}[$(date +%H:%M:%S)]${NC} $1"; }

# ==================== LOAD .ENV ====================

ENV_FILE="${PROJECT_DIR}/.env"
if [ -f "${ENV_FILE}" ]; then
    log "📄 Loading .env..."
    set -a
    source "${ENV_FILE}"
    set +a
    log "✅ Loaded: Token=${TELEGRAM_BOT_TOKEN:0:10}..., Model=${OLLAMA_MODEL:-llama3.2:latest}"
else
    warn "No .env file found!"
fi

# ==================== COMMANDS ====================

case "$CMD" in
    status)
        echo ""
        echo "📊 System Status"
        echo "=========================="

        # Bot status
        if pgrep -f "python.*main\.py" > /dev/null 2>&1; then
            echo -e "🤖 Bot: ${GREEN}RUNNING${NC}"
            ps aux | grep "python.*main\.py" | grep -v grep | awk '{print "   PID: " $2 " | CPU: " $3 "% | MEM: " $4 "%"}'
        else
            echo -e "🤖 Bot: ${RED}STOPPED${NC}"
        fi

        # Ollama status
        if curl -s "${OLLAMA_HOST:-http://localhost:11434}/api/tags" > /dev/null 2>&1; then
            echo -e "🦙 Ollama: ${GREEN}RUNNING${NC}"
            # Show loaded models
            curl -s "${OLLAMA_HOST:-http://localhost:11434}/api/tags" 2>/dev/null | grep -o '"name":"[^"]*"' | head -3 | sed 's/"name":"//;s/"//' | sed 's/^/   Model: /' || true
        else
            echo -e "🦙 Ollama: ${RED}STOPPED${NC}"
        fi

        # Memory
        echo ""
        echo "💾 Memory:"
        free -h | grep -E "Mem:|Swap:" | sed 's/^/   /'

        # Disk
        echo ""
        echo "💿 Disk:"
        df -h . | tail -1 | awk '{print "   Used: " $3 " / " $2 " (" $5 ")"}'

        exit 0
        ;;

    stop)
        log "🛑 Stopping bot..."
        pkill -f "python.*main\.py" 2>/dev/null || true
        sleep 2

        if pgrep -f "python.*main\.py" > /dev/null 2>&1; then
            warn "Force killing..."
            pkill -9 -f "python.*main\.py" 2>/dev/null || true
        fi

        ollama stop --all 2>/dev/null || true
        log "✅ Bot stopped"
        exit 0
        ;;

    swap|noswap|fast)
        SWAP_MODE="$CMD"
        ;;

    *)
        echo "Usage: $0 [swap|noswap|fast|status|stop]"
        echo ""
        echo "Modes:"
        echo "  swap   - Standard mode, all models (default)"
        echo "  noswap - Light models only, no swap"
        echo "  fast   - Minimal memory, fastest response"
        echo ""
        echo "Commands:"
        echo "  status - Show system status"
        echo "  stop   - Stop bot"
        exit 1
        ;;
esac

# ==================== RESTART ====================

log "🔄 Restarting bot (Mode: ${SWAP_MODE})"
echo "=========================="

# Stop existing
log "Stopping existing processes..."
pkill -f "python.*main\.py" 2>/dev/null || true
sleep 2

if pgrep -f "python.*main\.py" > /dev/null 2>&1; then
    warn "Force killing..."
    pkill -9 -f "python.*main\.py" 2>/dev/null || true
    sleep 1
fi

# Stop Ollama models
ollama stop --all 2>/dev/null || true
sleep 1

# Environment setup
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Ollama settings from .env or defaults
export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-30m}"
export OLLAMA_NUM_THREADS="${OLLAMA_NUM_THREADS:-4}"

# Mode-specific settings
case "$SWAP_MODE" in
    swap)
        log "💾 Config: Standard (all models, swap enabled)"
        export OLLAMA_NUM_GPU=0
        export OLLAMA_MAX_LOADED_MODELS=2
        ;;
    noswap)
        log "🚫 Config: No swap (light models only)"
        export OLLAMA_MAX_LOADED_MODELS=1
        export OLLAMA_DEFAULT_MODEL="llama3.2:latest"
        ;;
    fast)
        log "⚡ Config: Fast mode (minimal memory)"
        export OLLAMA_MAX_LOADED_MODELS=1
        export OLLAMA_KEEP_ALIVE="10m"
        export OLLAMA_NUM_THREADS=2
        ;;
esac

# Validate token
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    error "TELEGRAM_BOT_TOKEN not set!"
    error "Check your .env file"
    exit 1
fi

# Start
log "🚀 Starting bot..."
echo "=========================="
exec poetry run python main.py
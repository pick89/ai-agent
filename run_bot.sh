#!/bin/bash
# run_bot.sh - Run bot with optional swap optimization
cd ~/Dev/Ai/ai-agent || exit 1

SWAP_MODE="${1:-swap}"
echo "🤖 Starting Bot (Swap: ${SWAP_MODE})"
echo "=========================="

pkill -f "python.*main\.py" 2>/dev/null
sleep 2

if [ "$SWAP_MODE" = "swap" ]; then
    export OLLAMA_NUM_GPU=0
    export OLLAMA_MAX_LOADED_MODELS=2
    echo "💾 Swap enabled - All models available"
else
    echo "⚡ No swap - Use light models"
fi

ollama stop --all 2>/dev/null
echo "🚀 Starting..."
exec poetry run python main.py

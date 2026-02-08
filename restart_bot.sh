#!/bin/bash
# restart_bot.sh - Simple restart with swap control
cd ~/Dev/Ai/ai-agent || exit 1

CMD="${1:-swap}"
case "$CMD" in
    swap|noswap) SWAP="$CMD" ;;
    status)
        echo "📊 Status:"
        ps aux | grep -q "python.*main\.py" && echo "✅ Bot running" || echo "❌ Bot stopped"
        free -h | grep -E "Mem:|Swap:"
        exit 0
        ;;
    stop)
        pkill -f "python.*main\.py"
        echo "✅ Bot stopped"
        exit 0
        ;;
    *) echo "Usage: $0 [swap|noswap|status|stop]"; exit 1 ;;
esac

echo "🤖 Restarting (Swap: $SWAP)"
echo "=========================="

pkill -f "python.*main\.py"
ollama stop --all 2>/dev/null
sleep 2

[ "$SWAP" = "swap" ] && export OLLAMA_NUM_GPU=0
echo "🚀 Starting..."
exec poetry run python main.py

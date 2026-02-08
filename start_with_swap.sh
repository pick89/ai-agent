#!/bin/bash
# start_with_swap.sh
# AI Bot optimized for swap (hard disk) usage
# Location: ~/Dev/Ai/ai-agent/start_with_swap.sh

cd ~/Dev/Ai/ai-agent || {
    echo "❌ Cannot find bot directory"
    exit 1
}

echo "💿 SWAP-OPTIMIZED AI Bot"
echo "========================"
echo "Using hard disk as virtual RAM"
echo ""

# Configure system for heavy swap usage
echo "⚙️ Configuring swap optimization..."
sudo sysctl vm.swappiness=80 2>/dev/null || echo "Note: Could not set swappiness (needs sudo)"
sudo sysctl vm.vfs_cache_pressure=50 2>/dev/null || echo "Note: Could not set cache pressure"

# Check current memory
echo ""
echo "📊 Current memory status:"
free -h
echo ""
echo "💾 Swap usage:"
swapon --show 2>/dev/null || echo "No swap info available"

# Set Ollama environment variables for swap
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_KEEP_ALIVE=-1  # Keep model loaded
export OLLAMA_NUM_GPU=0      # CPU only

# Stop any running instances
echo ""
echo "⏹️ Stopping existing processes..."
pkill -f "python.*main.py" 2>/dev/null && echo "Stopped bot"
ollama stop --all 2>/dev/null && echo "Stopped Ollama models"
sleep 2

# Start Ollama fresh
echo ""
echo "🚀 Starting Ollama (swap-aware)..."
ollama serve > /tmp/ollama_swap.log 2>&1 &
OLLAMA_PID=$!
sleep 5

# Check if Ollama started
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama failed to start. Check: tail -f /tmp/ollama_swap.log"
    exit 1
fi

echo "✅ Ollama is running (PID: $OLLAMA_PID)"

# Pre-load a model to swap (optional - comment out if you want manual loading)
echo ""
read -p "📦 Pre-load a model to swap? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Available models:"
    ollama list 2>/dev/null | head -10

    read -p "Enter model name (default: mistral:latest): " MODEL
    MODEL=${MODEL:-"mistral:latest"}

    echo "Loading $MODEL to swap (this may take a minute)..."
    ollama run $MODEL "test" > /tmp/model_load.log 2>&1 &
    LOAD_PID=$!

    echo "Model loading in background (PID: $LOAD_PID)"
    echo "Check progress: tail -f /tmp/model_load.log"
    sleep 10  # Give it some time to start loading
fi

# Start the bot
echo ""
echo "🤖 Starting AI Bot (using swap for heavy models)..."
echo "================================================"
echo "💡 You can now use heavier models:"
echo "   /use_model mistral"
echo "   /use_model codellama"
echo "   /use_model llama3.1"
echo ""
echo "⚠️  First responses will be slow (loading from disk)"
echo "    Subsequent responses will be faster (cached)"
echo "================================================"

# Run the bot
poetry run python main.py

# Cleanup on exit
echo ""
echo "🧹 Cleaning up..."
kill $OLLAMA_PID 2>/dev/null
[ ! -z "$LOAD_PID" ] && kill $LOAD_PID 2>/dev/null
ollama stop --all 2>/dev/null
echo "✅ Cleanup complete"
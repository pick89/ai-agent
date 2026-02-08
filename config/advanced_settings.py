"""
Advanced Settings for Multi-Modal Bot
"""

# Bot Identity
BOT_NAME = "Buddy 🤖✨"
BOT_SIGNATURE = "✨ Your AI Buddy"

# Available Models with their strengths - MUST MATCH YOUR OLLAMA LIST
MODEL_CONFIGS = {
    "mistral:latest": {
        "name": "Mistral",
        "strength": "General knowledge, reasoning, coding",
        "context": 8192,
        "temperature": 0.7,
        "best_for": ["general questions", "reasoning", "coding", "analysis"],
        "emoji": "🌀"
    },
    "llama3.2:latest": {
        "name": "Llama 3.2",
        "strength": "Balanced performance, creative writing",
        "context": 4096,
        "temperature": 0.8,
        "best_for": ["creative writing", "general chat", "summarization"],
        "emoji": "🦙"
    },
    "llama3.1:8b": {
        "name": "Llama 3.1 8B",
        "strength": "Good balance, smaller size",
        "context": 4096,
        "temperature": 0.7,
        "best_for": ["general purpose", "balanced tasks"],
        "emoji": "🦙"
    },
    "qwen:latest": {
        "name": "Qwen",
        "strength": "Multilingual, general purpose",
        "context": 32768,
        "temperature": 0.7,
        "best_for": ["multilingual", "general tasks"],
        "emoji": "🔢"
    },
    "qwen3:latest": {
        "name": "Qwen 3",
        "strength": "Multilingual, math, coding",
        "context": 32768,
        "temperature": 0.7,
        "best_for": ["multilingual", "mathematics", "coding", "detailed analysis"],
        "emoji": "🔢"
    },
    "qwen3-vl:latest": {
        "name": "Qwen 3 Vision",
        "strength": "Vision capabilities, image understanding",
        "context": 32768,
        "temperature": 0.7,
        "best_for": ["image analysis", "visual content"],
        "emoji": "👁️"
    },
    "codellama:7b-instruct": {
        "name": "CodeLlama",
        "strength": "Programming, code generation",
        "context": 16384,
        "temperature": 0.2,
        "best_for": ["coding", "debugging", "code explanation"],
        "emoji": "💻"
    },
    "OpenLLM-France/Lucie-7B-Instruct:latest": {
        "name": "Lucie (French)",
        "strength": "French language, European context",
        "context": 4096,
        "temperature": 0.7,
        "best_for": ["french language", "european topics"],
        "emoji": "🇫🇷"
    }
}

# Default model
DEFAULT_MODEL = "mistral:latest"

# Mode settings
MODES = {
    "auto": "🤖 Auto-select model and decide when to search",
    "local": "💾 Use local knowledge only (no web search)",
    "search": "🌐 Always search for current information",
    "fast": "⚡ Fast mode (smaller context, no search)",
}

# Web Search Settings
WEB_SEARCH_ENABLED = True
MAX_WEB_SEARCHES = 2
SEARCH_CACHE_TIME = 30

# Performance
MAX_RESPONSE_LENGTH = 3000
MAX_HISTORY_MESSAGES = 8
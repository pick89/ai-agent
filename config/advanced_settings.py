"""
Advanced Settings - Model Configurations & Performance Tuning
Optimized for Python 3.14 + CPU-only inference
"""

from typing import Dict, Any, List

# =============== BOT IDENTITY ===============

BOT_NAME: str = "Buddy ⚡"
BOT_SIGNATURE: str = "🤖 Optimized for Speed"

# =============== MODEL CONFIGURATIONS ===============

MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "llama3.2:latest": {
        "name": "Llama 3.2",
        "strength": "Ultra-fast, memory efficient",
        "context": 2048,
        "temperature": 0.4,
        "num_predict": 400,
        "cpu_threads": 4,
        "memory_mb": 1500,
        "emoji": "🦙",
        "recommended": True,
        "best_for": ["general", "fast", "chat"],
    },
    "llama3.2:3b": {
        "name": "Llama 3.2 (3B)",
        "strength": "Fastest, lowest memory",
        "context": 2048,
        "temperature": 0.4,
        "num_predict": 400,
        "cpu_threads": 4,
        "memory_mb": 800,
        "emoji": "🦙",
        "recommended": True,
        "best_for": ["fast", "mobile", "simple"],
    },
    "mistral:latest": {
        "name": "Mistral",
        "strength": "Balanced quality & speed",
        "context": 2048,
        "temperature": 0.5,
        "num_predict": 500,
        "cpu_threads": 4,
        "memory_mb": 3500,
        "emoji": "🌀",
        "recommended": True,
        "best_for": ["reasoning", "analysis", "writing"],
    },
    "codellama:7b-instruct": {
        "name": "CodeLlama",
        "strength": "Programming & code",
        "context": 1024,
        "temperature": 0.2,
        "num_predict": 600,
        "cpu_threads": 4,
        "memory_mb": 3500,
        "emoji": "💻",
        "recommended": False,
        "best_for": ["code", "debugging", "technical"],
    },
    "qwen2.5:latest": {
        "name": "Qwen 2.5",
        "strength": "Multilingual & reasoning",
        "context": 2048,
        "temperature": 0.5,
        "num_predict": 500,
        "cpu_threads": 4,
        "memory_mb": 3000,
        "emoji": "🔢",
        "recommended": True,
        "best_for": ["multilingual", "math", "logic"],
    },
    "phi3:latest": {
        "name": "Phi-3",
        "strength": "Compact & capable",
        "context": 2048,
        "temperature": 0.4,
        "num_predict": 400,
        "cpu_threads": 4,
        "memory_mb": 1200,
        "emoji": "🔮",
        "recommended": True,
        "best_for": ["fast", "reasoning", "chat"],
    },
}

# =============== DEFAULTS ===============

DEFAULT_MODEL: str = "llama3.2:latest"
AUTO_MODEL_SELECTION: bool = True

# =============== OPERATION MODES ===============

MODES: Dict[str, Dict[str, Any]] = {
    "auto": {
        "description": "Auto-decide when to search",
        "emoji": "🤖",
        "use_tools": True,
        "temperature": 0.5,
    },
    "fast": {
        "description": "Fast responses, no tools",
        "emoji": "⚡",
        "use_tools": False,
        "temperature": 0.3,
        "max_tokens": 300,
    },
    "local": {
        "description": "Local knowledge only",
        "emoji": "💾",
        "use_tools": False,
        "temperature": 0.4,
    },
    "search": {
        "description": "Always search when needed",
        "emoji": "🌐",
        "use_tools": True,
        "temperature": 0.5,
        "force_search": True,
    },
    "code": {
        "description": "Optimized for programming",
        "emoji": "💻",
        "use_tools": False,
        "temperature": 0.2,
        "model": "codellama:7b-instruct",
    },
}

# =============== PERFORMANCE TUNING ===============

# CPU-specific optimizations
CPU_OPTIMIZATIONS = {
    "batch_size": 4,              # Smaller batches for CPU cache efficiency
    "num_thread": 4,              # Match physical cores (not hyperthreads)
    "use_mmap": True,             # Memory-mapped file I/O
    "use_mlock": False,           # Don't lock RAM (prevents OOM)
}

# Memory management
MEMORY_LIMITS = {
    "max_loaded_models": 2,       # Keep 2 models in RAM max
    "swap_threshold": 0.8,        # Use swap at 80% RAM usage
    "context_prune_threshold": 1800,  # Prune context at this token count
}

# Response optimization
RESPONSE_SETTINGS = {
    "max_length": 500,            # Max tokens per response
    "timeout_seconds": 45,        # Kill slow requests
    "streaming": False,           # Disable for CPU (adds overhead)
    "retry_attempts": 2,          # Retry failed requests
}

# =============== QUERY PATTERNS FOR MODEL SELECTION ===============

QUERY_PATTERNS = {
    "code": [
        r"\b(code|program|function|algorithm|debug|error|syntax|compile)\b",
        r"\b(python|javascript|java|c\+\+|rust|go|html|css|sql|bash)\b",
        r"\b(api|library|framework|git|docker|kubernetes)\b",
    ],
    "math": [
        r"\b(calculate|compute|solve|equation|formula|math|algebra|calculus)\b",
        r"\b(statistics|probability|matrix|vector|derivative|integral)\b",
        r"[\d\+\-\*\/\=\(\)]{5,}",  # Math expressions
    ],
    "creative": [
        r"\b(write|story|poem|creative|fiction|imagine|describe|narrative)\b",
        r"\b(character|plot|scene|dialogue|novel|essay|blog)\b",
    ],
    "search": [
        r"\b(current|latest|today|news|weather|price|stock|market)\b",
        r"\b(2024|2025|recent|update|now|happening)\b",
        r"\b(who is|what is|where is|when did|why did|how to)\b",
    ],
    "fast": [
        r"^(hi|hello|hey|ok|yes|no|thanks|bye)$",  # Short greetings
        r"\b(quick|fast|brief|short|simple|one word)\b",
    ],
}

# =============== HELPER FUNCTIONS ===============

def get_model_config(model_name: str) -> Dict[str, Any]:
    """Get configuration for a specific model"""
    return MODEL_CONFIGS.get(model_name, MODEL_CONFIGS[DEFAULT_MODEL])

def get_recommended_models() -> List[str]:
    """Get list of recommended models for CPU"""
    return [
        name for name, config in MODEL_CONFIGS.items()
        if config.get("recommended", False)
    ]

def get_mode_config(mode: str) -> Dict[str, Any]:
    """Get configuration for operation mode"""
    return MODES.get(mode, MODES["auto"])

def estimate_memory_usage(model_name: str, context_size: int = 2048) -> int:
    """
    Estimate RAM usage in MB for a model + context
    Rough formula: base_memory + (context * 0.5)
    """
    config = get_model_config(model_name)
    base = config.get("memory_mb", 2000)
    context_overhead = (context_size / 2048) * 500  # ~500MB per 2K context
    return int(base + context_overhead)

def select_model_for_query(query: str, available_models: List[str]) -> str:
    """
    Simple model selection based on query content
    """
    import re

    query_lower = query.lower()

    # Check patterns
    for category, patterns in QUERY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                if category == "code" and "codellama" in available_models:
                    return "codellama:7b-instruct"
                elif category == "math" and any("qwen" in m for m in available_models):
                    return "qwen2.5:latest"
                elif category == "fast":
                    return "llama3.2:3b" if "llama3.2:3b" in available_models else "llama3.2:latest"

    # Default to fastest recommended
    for model in ["llama3.2:latest", "phi3:latest", "mistral:latest"]:
        if model in available_models:
            return model

    # Fallback
    return available_models[0] if available_models else DEFAULT_MODEL


# Validation on import
if __name__ == "__main__":
    print(f"✅ Advanced settings loaded")
    print(f"   Default model: {DEFAULT_MODEL}")
    print(f"   Recommended: {get_recommended_models()}")
    print(f"   Modes: {list(MODES.keys())}")
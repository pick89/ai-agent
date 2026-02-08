"""
Optimized Settings for Python 3.14 + Async Architecture
CPU-optimized for local Ollama inference
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Load environment variables
from dotenv import load_dotenv

# Find .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# =============== TELEGRAM SETTINGS ===============

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USERS: List[str] = [u.strip() for u in os.getenv("ALLOWED_TELEGRAM_USERS", "").split(",") if u.strip()]

# Allow all users if "*" is specified
if "*" in ALLOWED_USERS:
    ALLOWED_USERS = []  # Empty list = allow all

# Validate
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in .env file")

# =============== OLLAMA CONNECTION SETTINGS ===============

OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:latest")

# Connection pooling - critical for performance
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))  # Total request timeout
OLLAMA_CONNECT_TIMEOUT: int = int(os.getenv("OLLAMA_CONNECT_TIMEOUT", "10"))  # Initial connection
OLLAMA_KEEP_ALIVE: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")  # Keep model in memory

# HTTP Client settings
HTTP_MAX_CONNECTIONS: int = int(os.getenv("HTTP_MAX_CONNECTIONS", "10"))
HTTP_MAX_KEEPALIVE: int = int(os.getenv("HTTP_MAX_KEEPALIVE", "5"))

# =============== PERFORMANCE SETTINGS ===============

# Concurrency control - prevent overwhelming CPU/RAM
MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "3"))
MAX_CONCURRENT_USERS: int = int(os.getenv("MAX_CONCURRENT_USERS", "5"))

# Request timeouts (seconds)
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "45"))
TOOL_TIMEOUT: int = int(os.getenv("TOOL_TIMEOUT", "10"))

# Memory management
MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "4"))
MAX_RESPONSE_TOKENS: int = int(os.getenv("MAX_RESPONSE_TOKENS", "500"))

# CPU Optimization
CPU_THREADS: int = int(os.getenv("CPU_THREADS", "4"))  # Match your CPU cores

# =============== LOGGING SETTINGS ===============

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# =============== UTILITY FUNCTIONS ===============

def get_ollama_options(model_name: str = None) -> Dict[str, Any]:
    """
    Get optimized Ollama options for a specific model
    """
    model = model_name or OLLAMA_MODEL

    # Base options for CPU optimization
    options = {
        "temperature": 0.4,
        "num_ctx": 2048,
        "num_predict": MAX_RESPONSE_TOKENS,
        "num_thread": CPU_THREADS,
        "top_p": 0.9,
        "top_k": 40,
        "repeat_penalty": 1.1,
        "seed": 42,  # Reproducible results
    }

    # Model-specific overrides
    if "codellama" in model:
        options["temperature"] = 0.2
        options["num_ctx"] = 1024
    elif "mistral" in model:
        options["temperature"] = 0.5
    elif "llama3.2" in model:
        options["temperature"] = 0.4
        options["num_ctx"] = 2048

    return options


def validate_settings() -> List[str]:
    """
    Validate all settings and return list of warnings
    """
    warnings = []

    # Check Ollama connection
    try:
        import httpx
        response = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
        if response.status_code != 200:
            warnings.append(f"Ollama returned status {response.status_code}")
    except Exception as e:
        warnings.append(f"Cannot connect to Ollama: {e}")

    # Check Python version
    if sys.version_info < (3, 11):
        warnings.append(f"Python {sys.version_info.major}.{sys.version_info.minor} - 3.11+ recommended")

    # Check CPU threads
    import os as os_module
    cpu_count = os_module.cpu_count() or 4
    if CPU_THREADS > cpu_count:
        warnings.append(f"CPU_THREADS ({CPU_THREADS}) > available cores ({cpu_count})")

    return warnings


# Print validation on import (optional)
if __name__ == "__main__":
    print(f"✅ Settings loaded")
    print(f"   Model: {OLLAMA_MODEL}")
    print(f"   Host: {OLLAMA_HOST}")
    print(f"   Max concurrent: {MAX_CONCURRENT_REQUESTS}")

    warnings = validate_settings()
    if warnings:
        print("\n⚠️  Warnings:")
        for w in warnings:
            print(f"   - {w}")
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.getenv("ALLOWED_TELEGRAM_USERS", "").split(",")

# Ollama settings
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Validate required settings
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in .env file")

if not ALLOWED_USERS or ALLOWED_USERS == ['']:
    raise ValueError("ALLOWED_TELEGRAM_USERS not set in .env file")

print(f"✓ Config loaded successfully")
print(f"  - Model: {OLLAMA_MODEL}")
print(f"  - Allowed users: {len(ALLOWED_USERS)}")

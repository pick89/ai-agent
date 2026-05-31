# CLAUDE.md

Guidance for Claude Code working in this repository.

## Project Overview

**ai-agent** (Buddy) is an async AI assistant running locally with Ollama and Telegram. Includes smart model selection, web search, notes, finance tracking, reminders, and email.

## Build & Development

### Prerequisites
- Python 3.14+
- Ollama running locally
- Telegram Bot Token (@BotFather)
- 16GB+ RAM
- Poetry

### Setup
```bash
cd ai-agent && poetry install
cp .env.example .env  # Edit with TELEGRAM_BOT_TOKEN

ollama serve &
ollama pull llama3.2:latest mistral:latest
```

### Running the Bot
```bash
./restart_bot.sh swap   # Recommended for 16GB RAM
./restart_bot.sh fast   # For 8GB RAM
./restart_bot.sh status
./restart_bot.sh stop
```

### Development Mode
```bash
poetry run python main.py
TELEGRAM_BOT_TOKEN=<token> ALLOWED_TELEGRAM_USERS=* poetry run python main.py
RUST_LOG=debug poetry run python main.py
```

## Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/test_agent.py

# Run with verbose output
poetry run pytest -v
```

## Code Organization

```
ai-agent/
├── main.py                 # Telegram bot entry point (~13KB)
├── agent.py               # Core AI agent logic (~22KB)
├── model_selector.py      # Smart model selection (~4KB)
├── multi_modal_agent.py   # Multi-modal processing (~12KB)
├── config.py              # Configuration management
├── tools/                 # Feature modules
│   ├── web_search.py      # DuckDuckGo web search
│   ├── notes.py           # Auto-categorized notes
│   ├── finance_tracker.py # Expense/income tracking
│   └── notifications.py   # Email & reminders
├── data/                  # Persistent storage
│   ├── notes/             # Note storage
│   ├── finance/           # Finance records
│   └── notifications/     # Reminders config
├── restart_bot.sh         # Start/stop script
├── pyproject.toml         # Poetry dependencies
└── README.md              # Project documentation
```

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **python-telegram-bot** | ^22.6 | Telegram bot integration |
| **ollama** | ^0.3.0 | Ollama LLM interface |
| **httpx** | ^0.27.0 | Async HTTP client |
| **aiohttp** | ^3.9.0 | Async HTTP requests |
| **duckduckgo-search** | ^7.0.0 | Web search |
| **numpy** | ^2.1.0 | Numerical operations |
| **pandas** | ^2.2.0 | Data analysis |
| **python-dotenv** | ^1.0.0 | Environment variables |
| **tenacity** | ^8.0.0 | Retry logic |

## Coding Conventions

**Code Style:** Python 3.14+ with async/await. Run Black before commits. Use type hints. Organize imports with isort.

**File Organization:** Keep modules focused. Use descriptive names. Add docstrings. Target <500 LOC per file.

**Error Handling:** Graceful timeouts. Telegram-friendly messages. Log with context. No bare `except`.

**Logging:**
```python
logger.info(f"User {user_id}: processing query", extra={"user_id": user_id})
```

## Configuration

### Environment Variables (.env)
```bash
# Required
TELEGRAM_BOT_TOKEN=<your_token_here>
ALLOWED_TELEGRAM_USERS=*            # or user_id,user_id,...

# Optional - Performance
MAX_CONCURRENT_REQUESTS=3           # Limit concurrent AI requests
CPU_THREADS=4                       # Match your CPU cores
MAX_HISTORY_MESSAGES=4              # Conversation memory
MAX_RESPONSE_TOKENS=500             # Response length limit

# Optional - Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
OLLAMA_KEEP_ALIVE=30m               # Keep models in RAM
```

### Telegram Integration
Store raw token (no `DISCORD_BOT_TOKEN=` prefix). Use environment variables for all credentials. Never commit `.env`.

## Telegram Bot Commands

Users can interact with these commands:

```
/start           - Welcome message with features
/help            - Show all commands
/status          - System status & performance metrics
/reset           - Clear conversation history
/models          - List available Ollama models
/use_model <name>- Switch AI model
/auto            - Auto-decide when to search (default)
/fast            - Fast responses, no tools
/local           - Local knowledge only
/search          - Always search when needed

# Productivity
note <text>          - Save note with auto-categorization
search notes <term>  - Find notes by keyword
expense <amount>     - Track expense
income <amount>      - Record income
finance summary      - Monthly financial summary
remind me <msg> in <time> - Schedule reminder
list reminders       - Show pending reminders
```

## Common Development Tasks

### Add a new tool/feature
1. Create module in `tools/` directory
2. Implement handler function (async)
3. Register in `agent.py` command router
4. Update `/help` text in `main.py`
5. Add tests in `tests/` directory

### Modify model selection logic
1. Edit `model_selector.py`: update routing rules
2. Test with different query types
3. Update documentation if adding new model

### Add new Telegram command
1. Edit `main.py`: add handler (async)
2. Register command in `handlers_dict`
3. Add to `/help` response
4. Test with actual bot

### Debug bot issues
```bash
# Check Ollama connectivity
poetry run python -c "import ollama; print(ollama.list())"

# Verify Telegram token
poetry run python -c "from telegram import Bot; Bot(token='<token>').get_me()"

# Test imports
poetry run python -c "from config.settings import *; print('OK')"
```

## Troubleshooting

**"Conflict: terminated by other getUpdates request":** Another instance is running. Stop it: `./restart_bot.sh stop && sleep 3 && ./restart_bot.sh swap`.

**Bot won't start:** Check Ollama: `curl http://localhost:11434/api/tags`. Verify env: `poetry run python verify.py`. View logs: `./restart_bot.sh status`.

**Out of Memory:** Use `./restart_bot.sh fast` or set smaller model: `/use_model llama3.2:3b`.

**Slow responses:** Reduce `MAX_HISTORY_MESSAGES=2` in `.env`. Use `/fast` mode or faster model.

**Module import errors:** Run `poetry shell`. Reinstall: `poetry install --no-cache`. Verify Python 3.14+.

## Performance Optimization

### Model Recommendations
| Model | Size | Speed | Best For |
|-------|------|-------|----------|
| llama3.2:latest | 3B | ⚡ Fastest | General chat, fast responses |
| mistral:latest | 7B | 🚀 Fast | Reasoning, analysis |
| codellama:7b | 7B | 🚀 Fast | Programming tasks |
| qwen2.5:latest | 7B | 🚀 Fast | Multilingual, math |

### Memory Management
```bash
# Reduce context for lower memory:
MAX_HISTORY_MESSAGES=2 MAX_RESPONSE_TOKENS=300 ./restart_bot.sh fast

# Keep models in RAM longer:
OLLAMA_KEEP_ALIVE=60m ./restart_bot.sh swap
```

## Deployment

### Systemd User Service
Create `/etc/systemd/user/ai-agent.service`:
```ini
[Unit]
Description=AI Agent Bot
After=network.target ollama.service

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/Dev/Ai/ai-agent
Environment="PATH=/home/youruser/.local/bin:/usr/bin"
ExecStart=/home/youruser/Dev/Ai/ai-agent/restart_bot.sh swap
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Then:
```bash
systemctl --user enable ai-agent
systemctl --user start ai-agent
systemctl --user status ai-agent
```

## Git Conventions

- **Commit messages**: Action-oriented (e.g., "Add finance tracker", "Fix Ollama timeout")
- **Branches**: `feature/name` or `fix/issue`
- **Testing**: Run `poetry run pytest` before committing

## References

- **Python Telegram Bot**: https://python-telegram-bot.readthedocs.io/
- **Ollama API**: https://github.com/ollama/ollama/blob/main/docs/api.md
- **Poetry**: https://python-poetry.org/docs/
- **Async Python**: https://docs.python.org/3/library/asyncio.html

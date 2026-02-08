#!/usr/bin/env python3
"""
Ollama Multi-Modal Telegram Bot - Optimized Async Version
Python 3.14 compatible, high-performance
"""

import asyncio
import logging
import sys
from typing import Dict

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Import optimized components
from config.settings import (
    TELEGRAM_BOT_TOKEN,
    ALLOWED_USERS,
    validate_settings,
    MAX_CONCURRENT_REQUESTS,
)
from config.advanced_settings import (
    BOT_NAME,
    BOT_SIGNATURE,
    MODES,
    get_mode_config,
)
from agent import OptimizedAgent
# Add this after imports in main.py
import os
import socket

def check_single_instance():
    """Prevent multiple bot instances using socket lock"""
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0' + 'ai_agent_bot_lock')
        return lock_socket  # Keep reference alive
    except socket.error:
        print("❌ Another bot instance is already running!")
        print("   Kill it with: pkill -f 'python main.py'")
        sys.exit(1)

# Call in main() before starting bot
lock = check_single_instance()
# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
for name in ["httpx", "httpcore", "telegram.ext.ExtBot"]:
    logging.getLogger(name).setLevel(logging.WARNING)


class BotState:
    """
    Manages bot state, user sessions, and agent lifecycle
    Thread-safe for async operations
    """

    def __init__(self):
        self.agent = OptimizedAgent()
        self.user_modes: Dict[int, str] = {}  # user_id -> mode
        self.user_models: Dict[int, str] = {}  # user_id -> model override

    def is_user_allowed(self, user_id: int) -> bool:
        """Check if user is authorized"""
        if not ALLOWED_USERS:  # Empty list = allow all
            return True
        return str(user_id) in ALLOWED_USERS

    def get_user_mode(self, user_id: int) -> str:
        """Get user's current mode"""
        return self.user_modes.get(user_id, "auto")

    def set_user_mode(self, user_id: int, mode: str):
        """Set user's mode"""
        self.user_modes[user_id] = mode

    async def get_response(
            self,
            user_id: int,
            message: str,
            tools: Dict
    ) -> str:
        """
        Get AI response with user-specific settings
        """
        # Check for user-specific model override
        if user_id in self.user_models:
            original_model = self.agent.model
            self.agent.model = self.user_models[user_id]

        try:
            response = await self.agent.run(message, tools=tools)
            return response
        finally:
            # Restore original model if changed
            if user_id in self.user_models:
                self.agent.model = original_model


# Global state instance
bot_state = BotState()


# =============== COMMAND HANDLERS ===============

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user_id = update.effective_user.id

    if not bot_state.is_user_allowed(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return

    welcome_text = f"""
🤖 **{BOT_NAME}**

⚡ **Optimized Features:**
• Async architecture for speed
• Smart model selection
• Connection pooling
• CPU-optimized inference

📋 **Commands:**
`/models` - Available models
`/mode` - Current mode/settings
`/status` - System status
`/reset` - Clear conversation
`/help` - Show help

**Modes:** `/auto` | `/fast` | `/local` | `/search`

Just send a message to start!
"""
    await update.message.reply_text(welcome_text, parse_mode="Markdown")
    logger.info(f"User {user_id} started bot")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    user_id = update.effective_user.id

    if not bot_state.is_user_allowed(user_id):
        return

    help_text = f"""
📖 **{BOT_NAME} Help**

**Commands:**
• `/start` - Welcome message
• `/models` - List available models
• `/use_model <name>` - Switch model
• `/mode` - Show current mode
• `/status` - System metrics
• `/reset` - Clear conversation history

**Modes:**
• `/auto` - Auto-decide when to search (default)
• `/fast` - Fast responses, no tools
• `/local` - Local knowledge only
• `/search` - Always search when needed

**Tips:**
• Use `/fast` for quick questions
• Use `/search` for current events
• Use `/reset` if conversation gets confused

{BOT_SIGNATURE}
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available Ollama models"""
    user_id = update.effective_user.id

    if not bot_state.is_user_allowed(user_id):
        return

    try:
        await update.message.chat.send_action("typing")

        models = await bot_state.agent.client.list_models()

        if not models:
            await update.message.reply_text("❌ No models found in Ollama.")
            return

        # Format model list
        model_list = "\n".join([f"• `{m}`" for m in models[:10]])

        text = f"""
📦 **Available Models**

{model_list}

**Current:** `{bot_state.agent.model}`

Switch with: `/use_model <name>`
"""
        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Models command error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show system status and metrics"""
    user_id = update.effective_user.id

    if not bot_state.is_user_allowed(user_id):
        return

    try:
        await update.message.chat.send_action("typing")

        # Get stats
        stats = bot_state.agent.get_stats()
        mode = bot_state.get_user_mode(user_id)

        # Get available models count
        models = await bot_state.agent.client.list_models()

        text = f"""
📊 **{BOT_NAME} Status**

🤖 **Model:** `{bot_state.agent.model}`
🎛️ **Mode:** `{mode}`
📦 **Ollama Models:** {len(models)}

⚡ **Performance:**
• Requests: {stats['total_requests']}
• Avg Latency: {stats['avg_latency']:.2f}s
• Errors: {stats['errors']}
• Context: {stats['context_messages']} msgs (~{stats['estimated_tokens']} tokens)

💻 **Config:**
• Max Concurrent: {MAX_CONCURRENT_REQUESTS}
• CPU Threads: Configured per model

{BOT_SIGNATURE}
"""
        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Status command error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear conversation history"""
    user_id = update.effective_user.id

    if not bot_state.is_user_allowed(user_id):
        return

    try:
        bot_state.agent.reset_conversation()
        await update.message.reply_text(
            f"🔄 **Conversation cleared!**\n\n{BOT_SIGNATURE}",
            parse_mode="Markdown"
        )
        logger.info(f"User {user_id} reset conversation")

    except Exception as e:
        logger.error(f"Reset error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show or set operation mode"""
    user_id = update.effective_user.id

    if not bot_state.is_user_allowed(user_id):
        return

    # If no args, show current mode
    if not context.args:
        current_mode = bot_state.get_user_mode(user_id)
        mode_info = get_mode_config(current_mode)

        text = f"""
🎛️ **Current Mode:** {mode_info['emoji']} `{current_mode}`

{mode_info['description']}

**Available Modes:**
• `/auto` - Auto-decide when to search
• `/fast` - Fast responses, no tools
• `/local` - Local knowledge only
• `/search` - Always search when needed

Change with: `/mode <name>`
"""
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    # Set new mode
    new_mode = context.args[0].lower()

    if new_mode not in MODES:
        await update.message.reply_text(
            f"❌ Invalid mode. Use: auto, fast, local, search"
        )
        return

    bot_state.set_user_mode(user_id, new_mode)
    mode_info = get_mode_config(new_mode)

    await update.message.reply_text(
        f"{mode_info['emoji']} **Mode set to:** `{new_mode}`\n"
        f"_{mode_info['description']}_\n\n"
        f"{BOT_SIGNATURE}",
        parse_mode="Markdown"
    )
    logger.info(f"User {user_id} set mode to {new_mode}")


# Mode shortcuts
async def auto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shortcut for /mode auto"""
    context.args = ["auto"]
    await mode_command(update, context)


async def fast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shortcut for /mode fast"""
    context.args = ["fast"]
    await mode_command(update, context)


async def local_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shortcut for /mode local"""
    context.args = ["local"]
    await mode_command(update, context)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shortcut for /mode search"""
    context.args = ["search"]
    await mode_command(update, context)


async def use_model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch to specific model"""
    user_id = update.effective_user.id

    if not bot_state.is_user_allowed(user_id):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: `/use_model <model_name>`\n"
            "Example: `/use_model llama3.2:latest`"
        )
        return

    model_name = context.args[0]

    # Verify model exists
    try:
        available = await bot_state.agent.client.list_models()
        if model_name not in available:
            await update.message.reply_text(
                f"❌ Model `{model_name}` not found.\n"
                f"Available: {', '.join(available[:5])}"
            )
            return

        # Set user-specific model
        bot_state.user_models[user_id] = model_name

        await update.message.reply_text(
            f"🔄 **Model switched to:** `{model_name}`\n\n"
            f"{BOT_SIGNATURE}",
            parse_mode="Markdown"
        )
        logger.info(f"User {user_id} switched to model {model_name}")

    except Exception as e:
        logger.error(f"Model switch error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


# =============== MESSAGE HANDLER ===============

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming messages"""
    user_id = update.effective_user.id

    # Authorization check
    if not bot_state.is_user_allowed(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return

    user_message = update.message.text

    if not user_message or not user_message.strip():
        await update.message.reply_text("Please send me a message!")
        return

    logger.info(f"Message from {user_id}: {user_message[:50]}...")

    # Show typing indicator
    await update.message.chat.send_action("typing")

    try:
        # Determine tools based on mode
        mode = bot_state.get_user_mode(user_id)
        tools = {}

        if mode in ("auto", "search"):
            # Import here to avoid circular imports
            from tools.web_search import web_search
            tools["web_search"] = web_search

        # Get AI response
        response = await bot_state.get_response(user_id, user_message, tools)

        # Ensure response is valid
        if not response or not response.strip():
            response = f"I didn't generate a response. Please try again.\n\n{BOT_SIGNATURE}"

        # Send response (handle long messages)
        if len(response) > 4000:
            # Split into chunks
            chunks = [response[i:i + 4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(response)

        logger.info(f"Response sent to {user_id}")

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ **Sorry, I encountered an error.**\n"
            f"Please try again.\n\n"
            f"{BOT_SIGNATURE}",
            parse_mode="Markdown"
        )


# =============== ERROR HANDLER ===============

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors"""
    logger.error(f"Update {update} caused error: {context.error}")


# =============== LIFECYCLE ===============

async def post_init(application: Application) -> None:
    """Post-initialization setup"""
    logger.info("Bot initialized successfully")

    # Validate settings
    warnings = validate_settings()
    if warnings:
        for warning in warnings:
            logger.warning(f"Config warning: {warning}")


async def post_shutdown(application: Application) -> None:
    """Cleanup on shutdown"""
    logger.info("Shutting down...")
    await bot_state.agent.close()
    logger.info("Cleanup complete")


# =============== MAIN ===============

def main() -> None:
    """Start the bot"""
    print("=" * 60)
    print(f"🤖 {BOT_NAME}")
    print("=" * 60)
    print(f"Model: {bot_state.agent.model}")
    print(f"Python: {sys.version.split()[0]}")
    print("=" * 60)

    # Validate critical settings
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    try:
        # Build application
        application = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .post_init(post_init)
            .post_shutdown(post_shutdown)
            .build()
        )

        # Command handlers
        handlers = [
            CommandHandler("start", start_command),
            CommandHandler("help", help_command),
            CommandHandler("models", models_command),
            CommandHandler("status", status_command),
            CommandHandler("reset", reset_command),
            CommandHandler("mode", mode_command),
            CommandHandler("auto", auto_command),
            CommandHandler("fast", fast_command),
            CommandHandler("local", local_command),
            CommandHandler("search", search_command),
            CommandHandler("use_model", use_model_command),
        ]

        for handler in handlers:
            application.add_handler(handler)

        # Message handler
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )

        # Error handler
        application.add_error_handler(error_handler)

        # Start
        print("\n✅ Bot initialized!")
        print("📱 Press Ctrl+C to stop\n")

        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            timeout=30,
        )

    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
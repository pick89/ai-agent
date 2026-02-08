#!/usr/bin/env python3
"""
Ollama Multi-Modal Telegram Bot - Buddy 🤖✨
Fixed version
"""

import logging
import traceback

# Telegram imports
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Local imports
from config.settings import TELEGRAM_BOT_TOKEN, ALLOWED_USERS
from config.advanced_settings import BOT_NAME, BOT_SIGNATURE
from multi_modal_agent import MultiModalAgent
from tools.web_search import web_search

# =============== CONFIGURATION ===============

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Suppress noisy loggers
for logger_name in ["httpx", "primp", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# =============== GLOBALS ===============

# Initialize the multi-modal agent
agent = MultiModalAgent()


# =============== UTILITY FUNCTIONS ===============

def check_user_allowed(user_id: int) -> bool:
    """Check if user is allowed to use the bot"""
    if not ALLOWED_USERS or "*" in ALLOWED_USERS:
        return True
    return str(user_id) in ALLOWED_USERS


# =============== COMMAND HANDLERS ===============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return

    welcome_message = f"""
{BOT_NAME}

Hello! I'm your intelligent AI assistant with multi-model capabilities.

**✨ Features:**
• Smart model selection based on your query
• Web search for current information
• Multiple specialized AI models
• Fast and accurate responses

**📋 Commands:**
`/start` - Show this message
`/models` - List available AI models
`/mode` - Show current mode and options
`/status` - Check system status
`/reset` - Clear conversation history
`/help` - Get help and examples

**🎛️ Mode Commands:**
`/auto` - Auto-decide (default)
`/local` - Local knowledge only
`/search` - Always search when needed
`/fast` - Fast responses

Just send me a message and I'll use the best AI model for your needs!
"""

    await update.message.reply_text(welcome_message, parse_mode='Markdown')
    logger.info("User %s started the bot", user_id)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        return

    help_text = f"""
{BOT_NAME} - Help Guide

**🤖 Model Commands:**
`/models` - List all available AI models
`/use_model <name>` - Switch to specific model
`/mode` - Show current mode and options

**🎛️ Mode Commands:**
`/auto` - Auto-decide when to search (default)
`/local` - Use local knowledge only (fast)
`/search` - Always search for current info
`/fast` - Quick responses (local only)

**📋 Utility Commands:**
`/start` - Welcome message
`/status` - System status
`/reset` - Clear conversation
`/help` - This message

**💡 Examples:**
• `/use_model codellama` - For coding help
• `/local` then ask general knowledge
• `/search` then ask "latest news"
• Just chat normally for auto mode

{BOT_SIGNATURE}
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /models command - show available models"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        return

    try:
        models_info = agent.get_detailed_models_info()
        await update.message.reply_text(models_info, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting models: {str(e)[:100]}")
        logger.error("Error in models_command: %s", e)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        return

    try:
        import ollama

        await update.message.chat.send_action("typing")

        models_response = ollama.list()
        models = models_response.get('models', [])

        # Get agent status
        conv_length = len(agent.conversation_history)
        current_model = agent.current_model
        current_mode = agent.current_mode

        status_msg = f"""
{BOT_NAME} - System Status

✅ **Ollama Status:** Running
📦 **Available Models:** {len(models)}
🤖 **Current Model:** `{current_model}`
🎛️ **Current Mode:** `{current_mode}`
💬 **Conversation Length:** {conv_length} messages

{BOT_SIGNATURE}
"""
        await update.message.reply_text(status_msg, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Error checking status: {str(e)[:100]}")
        logger.error("Error in status_command: %s", e)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reset command"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        return

    try:
        agent.reset_conversation()
        await update.message.reply_text(
            f"🔄 **Conversation cleared!**\n\n"
            f"{BOT_SIGNATURE}",
            parse_mode='Markdown'
        )
        logger.info("User %s reset conversation", user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
        logger.error("Reset error: %s", e)


async def local_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch to local mode (no web search)"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        return

    try:
        agent.set_mode("local")
        await update.message.reply_text(
            f"💾 **Switched to LOCAL mode**\n\n"
            f"{BOT_SIGNATURE}",
            parse_mode='Markdown'
        )
        logger.info("User %s switched to LOCAL mode", user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch to search mode (always search when needed)"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        return

    try:
        agent.set_mode("search")
        await update.message.reply_text(
            f"🌐 **Switched to SEARCH mode**\n\n"
            f"{BOT_SIGNATURE}",
            parse_mode='Markdown'
        )
        logger.info("User %s switched to SEARCH mode", user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def auto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch to auto mode"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        return

    try:
        agent.set_mode("auto")
        await update.message.reply_text(
            f"🤖 **Switched to AUTO mode**\n\n"
            f"{BOT_SIGNATURE}",
            parse_mode='Markdown'
        )
        logger.info("User %s switched to AUTO mode", user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def fast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch to fast mode"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        return

    try:
        agent.set_mode("fast")
        await update.message.reply_text(
            f"⚡ **Switched to FAST mode**\n\n"
            f"{BOT_SIGNATURE}",
            parse_mode='Markdown'
        )
        logger.info("User %s switched to FAST mode", user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def use_model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch to a specific model"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        return

    try:
        if not context.args:
            await update.message.reply_text(
                f"**Usage:** `/use_model <name>`\n\n"
                f"**Example:** `/use_model mistral`\n\n"
                f"{BOT_SIGNATURE}",
                parse_mode='Markdown'
            )
            return

        model_name = " ".join(context.args)
        success = agent.switch_to_model(model_name)

        if success:
            await update.message.reply_text(
                f"🔄 **Model switched**\n\n"
                f"{BOT_SIGNATURE}",
                parse_mode='Markdown'
            )
            logger.info("User %s switched to model: %s", user_id, model_name)
        else:
            await update.message.reply_text(
                f"❌ **Model not available**\n\n"
                f"{BOT_SIGNATURE}",
                parse_mode='Markdown'
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
        logger.error("Model switch error: %s", e)


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current mode"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        return

    try:
        mode_info = agent.get_mode_info()
        await update.message.reply_text(
            f"{mode_info}\n\n"
            f"{BOT_SIGNATURE}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
        logger.error("Error in mode_command: %s", e)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages with multi-modal agent"""
    user_id = update.effective_user.id

    if not check_user_allowed(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return

    user_message = update.message.text

    if not user_message or not user_message.strip():
        await update.message.reply_text("Please send me a message!")
        return

    logger.info("Message from %s: %s...", user_id, user_message[:50])

    try:
        # Show typing indicator
        await update.message.chat.send_action("typing")

        # Get AI response with tools
        tools = {"web_search": web_search}
        response = agent.run(user_message, tools=tools)

        # Ensure response is not empty
        if not response or not response.strip():
            response = f"I received your message but didn't get a response. Please try again.\n\n{BOT_SIGNATURE}"

        # Send response
        await update.message.reply_text(response)
        logger.info("Response sent to %s", user_id)

    except Exception as e:
        error_msg = (
            f"❌ **Sorry, I encountered an error.**\n\n"
            f"Please try again.\n\n"
            f"{BOT_SIGNATURE}"
        )

        await update.message.reply_text(error_msg, parse_mode='Markdown')
        logger.error("Error handling message from %s: %s", user_id, e)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot framework"""
    logger.error("Bot framework error: %s", context.error)


# =============== MAIN FUNCTION ===============

def main() -> None:
    """Start the bot"""
    print("=" * 60)
    print(f"{BOT_NAME}")
    print("=" * 60)
    print(f"🤖 Current model: {agent.current_model}")
    print(f"🎛️ Current mode: {agent.current_mode}")
    print(f"📦 Available models: {len(agent.available_models)}")
    print("=" * 60)

    try:
        # Create application
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Add command handlers
        handlers = [
            ("start", start),
            ("help", help_command),
            ("models", models_command),
            ("status", status_command),
            ("reset", reset_command),
            ("local", local_command),
            ("search", search_command),
            ("auto", auto_command),
            ("fast", fast_command),
            ("use_model", use_model_command),
            ("mode", mode_command),
        ]

        for command, handler in handlers:
            application.add_handler(CommandHandler(command, handler))

        # Add message handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Add error handler
        application.add_error_handler(error_handler)

        # Start the bot
        print("\n✅ Bot initialized successfully!")
        print("📱 Bot is running! Press Ctrl+C to stop.")
        print("=" * 60)

        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            timeout=30
        )

    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        logger.critical("Bot startup failed: %s", e)
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
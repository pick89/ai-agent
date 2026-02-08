#!/usr/bin/env python3
"""
AI Agent - Telegram Bot
Main entry point for the bot
"""

import logging
import traceback
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config.settings import TELEGRAM_BOT_TOKEN, ALLOWED_USERS
from agent import LocalAgent
from tools.web_search import web_search

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize the agent
agent = LocalAgent()


def check_user_allowed(user_id: int) -> bool:
    """Check if user is allowed to use the bot"""
    # If ALLOWED_USERS is empty or contains "*", allow all users
    if not ALLOWED_USERS or "*" in ALLOWED_USERS:
        return True
    
    return str(user_id) in ALLOWED_USERS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"User {user_id}"
    
    if not check_user_allowed(user_id):
        await update.message.reply_text(
            "⛔ Sorry, you are not authorized to use this bot.\n\n"
            "Please contact the bot administrator to get access."
        )
        logger.warning(f"Unauthorized access attempt from {username} (ID: {user_id})")
        return
    
    welcome_message = """
🤖 **AI Agent Bot**

Hello! I'm your local AI assistant powered by Ollama.

**What I can do:**
🔍 Search the internet for current information
📊 Answer questions based on my knowledge
💬 Have natural conversations
🔧 Use tools to help with tasks

**Commands:**
/start - Show this message
/help - Get help and examples
/status - Check system status
/reset - Clear conversation history

**Just send me a message and I'll help you out!**

*Tip: I can search the web for current information when needed.*
    """
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')
    logger.info(f"User {username} (ID: {user_id}) started the bot")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user_id = update.effective_user.id
    
    if not check_user_allowed(user_id):
        return
    
    help_text = """
**📚 Help & Examples**

**Available Commands:**
/start - Start the bot and see welcome message
/help - Show this help message
/status - Check Ollama status and conversation info
/reset - Clear conversation history

**How to use me:**
Just send me a message with what you need! I'll automatically:
1. Use my knowledge to answer general questions
2. Search the web for current information when needed
3. Use tools to help with specific tasks

**Examples:**
• "What is machine learning?"
• "Search for latest AI news"
• "What happened in technology today?"
• "Explain quantum computing"
• "What's the weather like?"
• "Who won the last World Cup?"

**Available Tools:**
🔍 **Web Search** - I can search the internet for current information when you ask about recent events, news, or things I don't know.

**Privacy:** Your conversation is processed locally via Ollama.
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - check Ollama status"""
    user_id = update.effective_user.id
    
    if not check_user_allowed(user_id):
        return
    
    try:
        import ollama
        
        # Show typing indicator
        await update.message.chat.send_action("typing")
        
        # Try to connect to Ollama
        models_response = ollama.list()
        models = models_response.get('models', [])
        
        # Get current model info
        current_model = agent.model if hasattr(agent, 'model') else "Unknown"
        
        # Get conversation stats
        conv_length = agent.get_conversation_length()
        
        status_msg = f"""
✅ **System Status**

🤖 **Ollama Status:** Running
📦 **Current Model:** `{current_model}`
📊 **Available Models:** {len(models)}
💬 **Conversation Length:** {conv_length} messages

**🛠️ Available Tools:**
• Web Search - Enabled

**🔍 Models Available:**
"""
        
        # Add first few models to status
        for i, model in enumerate(models[:3]):  # Show first 3 models
            model_name = model.get('name', 'Unknown')
            status_msg += f"• `{model_name}`\n"
        
        if len(models) > 3:
            status_msg += f"• ... and {len(models) - 3} more\n"
        
        status_msg += "\n*Type /reset to clear conversation history*"
        
        await update.message.reply_text(status_msg, parse_mode='Markdown')
        
    except ImportError:
        await update.message.reply_text(
            "❌ Ollama package not installed. Please install with: `pip install ollama`",
            parse_mode='Markdown'
        )
    except Exception as e:
        error_detail = str(e)
        await update.message.reply_text(
            f"❌ Error checking Ollama status:\n`{error_detail}`\n\n"
            "Make sure Ollama is running with: `ollama serve`",
            parse_mode='Markdown'
        )
        logger.error(f"Status check error: {e}")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reset command - clear conversation history"""
    user_id = update.effective_user.id
    
    if not check_user_allowed(user_id):
        return
    
    agent.reset_conversation()
    await update.message.reply_text(
        "🔄 **Conversation history cleared!**\n\n"
        "I've forgotten our previous conversation. "
        "You can start fresh now.",
        parse_mode='Markdown'
    )
    logger.info(f"User {user_id} reset conversation")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages with AI agent"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"User {user_id}"
    
    if not check_user_allowed(user_id):
        await update.message.reply_text(
            "⛔ You are not authorized to use this bot.\n\n"
            "Please contact the administrator for access."
        )
        logger.warning(f"Unauthorized message from {username} (ID: {user_id})")
        return
    
    user_message = update.message.text
    
    # Handle empty messages
    if not user_message or not user_message.strip():
        await update.message.reply_text("Please send me a message to get help!")
        return
    
    logger.info(f"Message from {username}: {user_message[:100]}...")
    
    try:
        # Show typing indicator while processing
        await update.message.chat.send_action("typing")
        
        # Get AI response with tools
        tools = {
            "web_search": web_search,
        }
        
        response = agent.run(user_message, tools=tools)
        
        # Ensure response is not empty
        if not response or not response.strip():
            response = "I received your message but didn't get a response. Please try again."
        
        # Truncate very long responses for logging
        log_response = response[:150] + "..." if len(response) > 150 else response
        logger.info(f"Response to {username}: {log_response}")
        
        # Send response (Telegram has 4096 character limit per message)
        if len(response) > 4000:
            # Split long messages
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await update.message.reply_text(chunk)
                else:
                    await update.message.reply_text(f"[Continued]\n\n{chunk}")
        else:
            await update.message.reply_text(response)
            
    except Exception as e:
        error_msg = (
            "❌ **Sorry, I encountered an error processing your request.**\n\n"
            f"**Error:** `{str(e)[:200]}`\n\n"
            "Please try again or use `/reset` to clear the conversation."
        )
        
        await update.message.reply_text(error_msg, parse_mode='Markdown')
        
        # Log full error with traceback
        logger.error(f"Error handling message from {username}: {e}")
        logger.error(traceback.format_exc())


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot framework"""
    logger.error(f"Bot error: {context.error}")
    
    # Try to send error message to user if update exists
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ **Bot encountered an internal error.**\n\n"
                "Please try again or use /reset to clear the conversation.",
                parse_mode='Markdown'
            )
        except:
            pass  # Don't crash if we can't send error message


def main():
    """Start the bot"""
    print("🚀 Starting AI Agent Bot...")
    print(f"🤖 Model: {agent.model}")
    print(f"👤 Allowed users: {ALLOWED_USERS if ALLOWED_USERS else 'All users'}")
    print("📦 Available tools: Web Search")
    print("=" * 50)
    
    try:
        # Test Ollama connection
        import ollama
        models = ollama.list()
        print(f"✅ Connected to Ollama - {len(models.get('models', []))} models available")
    except Exception as e:
        print(f"⚠️ Ollama connection warning: {e}")
        print("Note: Bot will start but may have issues without Ollama running")
    
    # Create application
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("reset", reset_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Start the bot
        print("\n✅ Bot initialized successfully!")
        print("📱 Bot is running! Press Ctrl+C to stop.")
        print("=" * 50)
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            timeout=30
        )
        
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        print("Check your TELEGRAM_BOT_TOKEN in config/settings.py")
        logger.critical(f"Bot startup failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()

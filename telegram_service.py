# telegram_service.py - UPDATED VERSION
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from typing import List, Dict, Any
import os

class TelegramNotifier:
    def __init__(self, bot_token: str = None):
        """
        Initializes the Telegram Bot with better error handling.
        """
        self._refresh_config(bot_token)

    def _refresh_config(self, bot_token: str = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.bot = None
        if self.bot_token:
            try:
                self.bot = Bot(token=self.bot_token)
                # Test if token is valid
                asyncio.run(self._test_token())
            except Exception as e:
                print(f"Telegram Bot initialization failed: {str(e)}")

    async def _test_token(self):
        """Test if bot token is valid"""
        try:
            await self.bot.get_me()
            print("✅ Telegram Bot token is valid")
        except Exception as e:
            print(f"❌ Bot token validation failed: {str(e)}")
            self.bot = None

    def is_configured(self) -> bool:
        """
        Checks if the Telegram Bot Token is configured and valid.
        """
        # Always check the latest environment variable
        current_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if current_token and not self.bot_token:
            self._refresh_config()
        
        # Check both token existence and bot initialization
        return self.bot_token is not None and self.bot_token != "" and self.bot is not None

    async def send_reminder(self, chat_id: str, task_name: str, time_remaining: str):
        """
        Sends a reminder with detailed error reporting.
        """
        if not self.bot:
            error_msg = "Telegram Bot not properly configured. Check your Bot Token."
            print(error_msg)
            return False, error_msg

        # Generate reminder message
        message = f"⏰ *Task Reminder*\n\n📋 **Task:** {task_name}\n⏳ **Due in:** {time_remaining}\n\n💡 Stay focused! 💪"
        
        try:
            # Validate chat_id format
            if not chat_id or not chat_id.strip():
                return False, "Chat ID is empty"
            
            chat_id_clean = chat_id.strip()
            if not chat_id_clean.isdigit():
                return False, f"Chat ID must be numeric. Got: '{chat_id_clean}'"
            
            # Convert to integer
            chat_id_int = int(chat_id_clean)
            
            # Send notification
            await self.bot.send_message(
                chat_id=chat_id_int, 
                text=message, 
                parse_mode='Markdown'
            )
            print(f"✅ Reminder sent successfully to {chat_id_int}")
            return True, "Reminder sent successfully!"
            
        except TelegramError as e:
            error_msg = str(e)
            
            # Provide user-friendly messages for common errors
            if "chat not found" in error_msg.lower():
                user_msg = """❌ Chat not found. Please:
1. Start a chat with your bot (search for @YOUR_BOT_NAME on Telegram)
2. Send `/start` command to the bot
3. Try again with the correct Chat ID"""
            elif "bot was blocked by the user" in error_msg.lower():
                user_msg = "❌ Bot was blocked. Please unblock the bot and try again."
            elif "forbidden" in error_msg.lower():
                user_msg = """❌ Bot cannot send messages to this user. Please:
1. Start a chat with the bot
2. Send `/start` command
3. Make sure you haven't blocked the bot"""
            elif "unauthorized" in error_msg.lower():
                user_msg = "❌ Invalid Bot Token. Please check your token and try again."
            elif "bad request: chat_id is empty" in error_msg.lower():
                user_msg = "❌ Chat ID is empty. Please enter a valid Chat ID."
            elif "peer_id_invalid" in error_msg.lower():
                user_msg = "❌ Invalid Chat ID. Please check and enter the correct Chat ID."
            else:
                user_msg = f"❌ Telegram error: {error_msg}"
            
            print(f"❌ Telegram error for {chat_id}: {error_msg}")
            return False, user_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"❌ Unexpected error for {chat_id}: {error_msg}")
            return False, error_msg

# Simple synchronous wrapper for Streamlit
def send_reminder_sync(notifier, chat_id, task_name, time_remaining):
    """Synchronous wrapper for async function"""
    try:
        return asyncio.run(notifier.send_reminder(chat_id, task_name, time_remaining))
    except Exception as e:
        return False, f"Failed to execute: {str(e)}"

# Test function for debugging
async def test_bot_connection(bot_token: str):
    """Test bot connection and get bot info"""
    try:
        bot = Bot(token=bot_token)
        bot_info = await bot.get_me()
        return True, f"✅ Bot connected: @{bot_info.username} ({bot_info.first_name})"
    except Exception as e:
        return False, f"❌ Connection failed: {str(e)}"

# Helper function to get chat ID
async def get_chat_id(bot_token: str):
    """Get updates to find chat IDs"""
    try:
        bot = Bot(token=bot_token)
        updates = await bot.get_updates()
        if updates:
            return [update.effective_chat.id for update in updates]
        return []
    except Exception as e:
        print(f"Error getting chat IDs: {e}")
        return []

if __name__ == "__main__":
    # Test the notifier
    print("Testing Telegram Notifier...")
    
    # Get token from environment
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ No TELEGRAM_BOT_TOKEN found in environment")
        print("Please set it: export TELEGRAM_BOT_TOKEN='your_token'")
    else:
        print(f"✅ Found token: {token[:10]}...")
        
        # Test connection
        success, message = asyncio.run(test_bot_connection(token))
        print(message)
        
        if success:
            # Test getting chat IDs
            chat_ids = asyncio.run(get_chat_id(token))
            if chat_ids:
                print(f"✅ Found chat IDs: {chat_ids}")
            else:
                print("⚠️ No chat IDs found. Start a chat with your bot first.")
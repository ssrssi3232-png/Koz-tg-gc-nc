import asyncio
import random
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext
from telegram.constants import ChatAction

# ===== CONFIGURATION =====
# Replace with your actual bot token from @BotFather
BOT_TOKEN = '7717413257:AAGc68RUcaxifvvY_69ymqGiQpqAvJsepLU'
# Replace with your Telegram user ID (get it from @userinfobot)
MY_USER_ID = 7984931982  # e.g., 123456789

# ===== GLOBAL STATE MANAGEMENT =====
# Structure: {chat_id: {'task': asyncio.Task, 'target': 'Koz', 'speed': 0.1, 'active': False, 'count': 0, 'texts': []}}
group_state = {}

# ===== EMOJI AND SYMBOL DATABASE =====
SYMBOLS = ['✦', '☣', '⚡', '⛧', '🔥', '⚔', '😈', '✘', '🦂', '⸻', '☠', '⌁', '⚙', '⛓', '🗡', '✧', '🩸', '⟐', '👁', '☢', '💀', '✪', '⎔', '🧿', '✖', '⛨', '😼', '⌬', '⚠', '✦⃝', '🕷', '☬', '⚔', '⟁', '🪓', '✵', '🧠', '⛓⃝', '🗝', '✣', '⟠', '⚛', '⸸', '✹', '🧬', '⌘', '⚒', '☾', '🌑', '⛩', '🜏', '✜', '😎', '⟟', '🪬', '✚', '🔒', '✥', '⌖', '☲', '🧱', '⟔', '🕶', '🩶', '🧿', '😙', '💣', '😭', '🥀']

# ===== HELPER FUNCTIONS =====
def is_authorized(update: Update) -> bool:
    """Check if command is from the authorized user."""
    return update.effective_user.id == MY_USER_ID

def generate_random_name(target):
    """Generate target + random symbol pair."""
    return f"{target} {random.choice(SYMBOLS)} {random.choice(SYMBOLS)}"

# ===== COMMAND HANDLERS =====
async def target_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set target text for name changing. Usage: /target Koz"""
    if not is_authorized(update):
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /target <text>")
        return
    
    chat_id = update.effective_chat.id
    target_text = ' '.join(context.args)
    
    if chat_id not in group_state:
        group_state[chat_id] = {'target': target_text, 'speed': 0.1, 'active': False, 'count': 0, 'texts': [], 'task': None}
    else:
        group_state[chat_id]['target'] = target_text
    
    await update.message.reply_text(f"✅ Target set to: {target_text}")

async def speed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set speed in seconds. Usage: /speed 0.2"""
    if not is_authorized(update):
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /speed <seconds>")
        return
    
    try:
        speed_val = float(context.args[0])
        if speed_val < 0.05:
            await update.message.reply_text("⚠️ Minimum speed is 0.05 seconds for safety.")
            return
    except ValueError:
        await update.message.reply_text("❌ Speed must be a number (e.g., 0.1)")
        return
    
    chat_id = update.effective_chat.id
    if chat_id not in group_state:
        group_state[chat_id] = {'target': 'Default', 'speed': speed_val, 'active': False, 'count': 0, 'texts': [], 'task': None}
    else:
        group_state[chat_id]['speed'] = speed_val
    
    changes_per_second = 1 / speed_val
    await update.message.reply_text(f"✅ Speed set to {speed_val}s (~{changes_per_second:.1f} changes/second)")

async def text_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set texts to send after every 100 name changes. Usage: /text Hello|Hi|Welcome"""
    if not is_authorized(update):
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /text message1|message2|message3")
        return
    
    chat_id = update.effective_chat.id
    texts = context.args[0].split('|')
    
    if chat_id not in group_state:
        group_state[chat_id] = {'target': 'Default', 'speed': 0.1, 'active': False, 'count': 0, 'texts': texts, 'task': None}
    else:
        group_state[chat_id]['texts'] = texts
    
    await update.message.reply_text(f"✅ {len(texts)} text messages set")

async def startchanging_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the name changing process."""
    if not is_authorized(update):
        return
    
    chat_id = update.effective_chat.id
    
    # Initialize if not exists
    if chat_id not in group_state:
        group_state[chat_id] = {'target': 'Koz', 'speed': 0.1, 'active': False, 'count': 0, 'texts': [], 'task': None}
    
    state = group_state[chat_id]
    
    if state['active']:
        await update.message.reply_text("⚠️ Already running in this group!")
        return
    
    if not state['target']:
        await update.message.reply_text("❌ Set target first with /target")
        return
    
    # Check bot admin status
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not bot_member.status == 'administrator' or not bot_member.can_change_info:
            await update.message.reply_text("❌ I need admin rights with 'Change Group Info' permission!")
            return
    except Exception as e:
        await update.message.reply_text(f"❌ Admin check failed: {e}")
        return
    
    state['active'] = True
    state['count'] = 0
    
    # Start the name changing task
    state['task'] = asyncio.create_task(name_changer_loop(context.bot, chat_id, state))
    await update.message.reply_text(f"🚀 Started! Target: {state['target']}, Speed: {state['speed']}s")

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the name changing process."""
    if not is_authorized(update):
        return
    
    chat_id = update.effective_chat.id
    
    if chat_id not in group_state or not group_state[chat_id]['active']:
        await update.message.reply_text("⚠️ Not running in this group!")
        return
    
    state = group_state[chat_id]
    state['active'] = False
    
    if state['task']:
        state['task'].cancel()
        try:
            await state['task']
        except asyncio.CancelledError:
            pass
        state['task'] = None
    
    await update.message.reply_text("⏹️ Stopped!")

async def refresh_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh/reset bot state for this group."""
    if not is_authorized(update):
        return
    
    chat_id = update.effective_chat.id
    
    if chat_id in group_state and group_state[chat_id]['active']:
        await update.message.reply_text("⚠️ Stop first with /stop before refresh!")
        return
    
    if chat_id in group_state:
        group_state.pop(chat_id)
    
    await update.message.reply_text("🔄 Refreshed! All settings cleared for this group.")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current status."""
    if not is_authorized(update):
        return
    
    chat_id = update.effective_chat.id
    
    if chat_id not in group_state:
        await update.message.reply_text("📊 No active session in this group.")
        return
    
    state = group_state[chat_id]
    status_text = f"""
📊 STATUS for This Group:
├ Active: {'✅ Yes' if state['active'] else '❌ No'}
├ Target: {state['target']}
├ Speed: {state['speed']}s
├ Changes made: {state['count']}
├ Texts queued: {len(state['texts'])}
└ Task running: {'✅ Yes' if state['task'] else '❌ No'}
    """
    await update.message.reply_text(status_text)

# ===== CORE NAME CHANGING LOGIC =====
async def name_changer_loop(bot: Bot, chat_id: int, state: dict):
    """Main loop for changing group names."""
    try:
        while state['active']:
            # Generate and set new name
            new_name = generate_random_name(state['target'])
            
            try:
                await bot.set_chat_title(chat_id=chat_id, title=new_name)
                state['count'] += 1
            except Exception as e:
                print(f"Error changing name in {chat_id}: {e}")
                if "Too Many Requests" in str(e):
                    await asyncio.sleep(5)  # Wait if rate-limited
                continue
            
            # Check for 100 changes and send texts
            if state['count'] % 100 == 0 and state['texts']:
                for text in state['texts']:
                    try:
                        await bot.send_message(chat_id=chat_id, text=text)
                        await asyncio.sleep(1)  # Small delay between texts
                    except Exception as e:
                        print(f"Error sending text: {e}")
            
            # Wait for next change
            await asyncio.sleep(state['speed'])
    
    except asyncio.CancelledError:
        print(f"Task cancelled for {chat_id}")
    except Exception as e:
        print(f"Unexpected error in loop for {chat_id}: {e}")

# ===== BOT SETUP =====
async def post_init(application: Application):
    """Optional: Send message when bot starts."""
    print(f"✅ Bot is online! Waiting for commands...")

def main():
    """Start the bot."""
    # Create application
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("target", target_cmd))
    application.add_handler(CommandHandler("speed", speed_cmd))
    application.add_handler(CommandHandler("text", text_cmd))
    application.add_handler(CommandHandler("startchanging", startchanging_cmd))
    application.add_handler(CommandHandler("stop", stop_cmd))
    application.add_handler(CommandHandler("refresh", refresh_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    
    # Suggested additional commands
    application.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text(
        "📚 Available Commands:\n"
        "/target <text> - Set target name\n"
        "/speed <seconds> - Set change speed\n"
        "/text <t1|t2|t3> - Set texts for every 100 changes\n"
        "/startchanging - Start the process\n"
        "/stop - Stop the process\n"
        "/refresh - Reset settings\n"
        "/status - Check current status"
    ) if is_authorized(u) else None))
    
    # Start the bot
    print("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

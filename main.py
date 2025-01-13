from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Command handler function for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Reply to the user with "Testing Done"
    await update.message.reply_text("Testing Done")

# Main function to set up the bot
def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual Telegram Bot API token
    bot_token = "7626493889:AAHERZUnMu6Qbms5bWpggooESfyWETvUMRU"

    # Create an application (bot instance)
    app = ApplicationBuilder().token(bot_token).build()

    # Add command handler for /start
    app.add_handler(CommandHandler("start", start))

    # Run the bot
    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()

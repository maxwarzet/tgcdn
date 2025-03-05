from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import asyncio

# Replace with your bot token and channel username
BOT_TOKEN = '7135940302:AAFhnlMTqUptvegthjba1-bpcJ3F_pfIlM0'  # Your bot token
CHANNEL_USERNAME = '@cdntelegraph'  # Your channel username

# Dictionary to track files uploaded by the bot
uploaded_files = {}

# Test the bot token
async def test_bot_token():
    from telegram import Bot
    bot = Bot(token=BOT_TOKEN)
    try:
        me = await bot.get_me()
        print("Bot username:", me.username)
        print("Bot token is valid!")
        return True
    except Exception as e:
        print("Invalid bot token:", e)
        return False

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send me a file, and I'll upload it to the channel and share the URL.")

# Command: /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Available commands:
/start - Start the bot and get instructions.
/help - Show this help message.
/restart - Restart the bot (clears cached data).
/upload - Learn how to upload files to the bot.
"""
    await update.message.reply_text(help_text)

# Command: /restart
async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clear the uploaded_files dictionary (optional: add more cleanup logic if needed)
    uploaded_files.clear()
    await update.message.reply_text("Bot has been restarted. All cached data has been cleared.")

# Command: /upload
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upload_instructions = """
To upload a file:
1. Send a file (document, photo, video, or audio) to this bot.
2. The bot will upload it to the channel and provide a URL.
3. You can delete the file using the "Delete File" button.
"""
    await update.message.reply_text(upload_instructions)

# Handle file uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Check if the message contains a file
        if update.message.document:
            file = update.message.document
        elif update.message.photo:
            # If it's a photo, get the largest size
            file = update.message.photo[-1]
        elif update.message.video:
            file = update.message.video
        elif update.message.audio:
            file = update.message.audio
        else:
            await update.message.reply_text("Please send a valid file (document, photo, video, or audio).")
            return

        # Get the file ID and file URL
        file_id = file.file_id
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_id}"

        # Send the file to the channel
        if update.message.document:
            sent_message = await context.bot.send_document(chat_id=CHANNEL_USERNAME, document=file_id)
        elif update.message.photo:
            sent_message = await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=file_id)
        elif update.message.video:
            sent_message = await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=file_id)
        elif update.message.audio:
            sent_message = await context.bot.send_audio(chat_id=CHANNEL_USERNAME, audio=file_id)

        # Generate the public URL for the file in the channel
        channel_message_id = sent_message.message_id
        channel_url = f"https://t.me/{CHANNEL_USERNAME[1:]}/{channel_message_id}"  # Remove '@' from username

        # Store the file information for deletion
        uploaded_files[channel_message_id] = {
            "file_id": file_id,
            "file_type": "document" if update.message.document else
                         "photo" if update.message.photo else
                         "video" if update.message.video else
                         "audio",
            "user_id": update.message.from_user.id
        }

        # Send the URL back to the user with a delete button
        keyboard = [
            [InlineKeyboardButton("Delete File", callback_data=f"delete_{channel_message_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"File uploaded to the channel! Here's the URL:\n{channel_url}", reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

# Handle file deletion
async def handle_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Extract the message ID from the callback data
    channel_message_id = int(query.data.split("_")[1])

    # Check if the file exists and belongs to the user
    if channel_message_id in uploaded_files and uploaded_files[channel_message_id]["user_id"] == query.from_user.id:
        try:
            # Delete the file from the channel
            await context.bot.delete_message(chat_id=CHANNEL_USERNAME, message_id=channel_message_id)
            # Remove the file from the tracking dictionary
            del uploaded_files[channel_message_id]
            await query.edit_message_text("File successfully deleted!")
        except Exception as e:
            await query.edit_message_text(f"Failed to delete the file: {e}")
    else:
        await query.edit_message_text("You do not have permission to delete this file or it no longer exists.")

async def main():
    # Test the bot token
    if not await test_bot_token():
        return

    # Build the application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler("upload", upload_command))

    # Add file handler
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO, handle_file))

    # Add callback query handler for delete button
    application.add_handler(CallbackQueryHandler(handle_delete))

    # Start the bot
    print("Bot is running...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # Keep the bot running
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Run the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
    finally:
        loop.close()
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import asyncio

# Replace with your bot token and default channel username
BOT_TOKEN = '7424412215:AAGCdg0ffY8wceV5m6sOxCCni9UJvIMjjQw'  # Your bot token
DEFAULT_CHANNEL_USERNAME = '@cdntelegraph'  # Default channel username

# Dictionary to track files uploaded by the bot and user-specific channels
uploaded_files = {}
user_channels = {}

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
    await update.message.reply_text("Welcome! Send me a file, and I'll upload it to your chosen channel and share the URL.")

# Command: /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Available commands:
/start - Start the bot and get instructions.
/help - Show this help message.
/restart - Restart the bot (clears cached data).
/upload - Learn how to upload files to the bot.
/choose_channel - Choose your own channel to upload files.
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
2. The bot will upload it to your chosen channel and provide a URL.
3. You can delete the file using the "Delete File" button.
"""
    await update.message.reply_text(upload_instructions)

# Command: /choose_channel
async def choose_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        # Get the list of channels where the user is an admin
        # Note: This requires the bot to be an admin in those channels
        chat_admins = await context.bot.get_chat_administrators(chat_id=DEFAULT_CHANNEL_USERNAME)
        
        # Filter channels where the user is an admin
        user_admin_channels = []
        for admin in chat_admins:
            if admin.user.id == user_id and admin.status in ['creator', 'administrator']:
                user_admin_channels.append(admin)

        if not user_admin_channels:
            await update.message.reply_text("You are not an admin of any channels. Using the default channel.")
            return

        # Create an inline keyboard with the user's channels
        keyboard = []
        for admin in user_admin_channels:
            # Get the chat (channel) information
            chat = await context.bot.get_chat(chat_id=DEFAULT_CHANNEL_USERNAME)
            keyboard.append([InlineKeyboardButton(chat.title, callback_data=f"channel_{chat.id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Choose your channel:", reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

# Handle channel selection
async def handle_channel_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    channel_id = int(query.data.split("_")[1])  # Ensure channel_id is an integer

    # Store the selected channel for the user
    user_channels[user_id] = channel_id
    await query.edit_message_text(f"Channel successfully added! You can now upload files to this channel.")

# Handle file uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ensure the update contains a message
    if not update.message:
        return  # Ignore updates without a message

    user_id = update.message.from_user.id
    channel_id = user_channels.get(user_id, DEFAULT_CHANNEL_USERNAME)

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
            sent_message = await context.bot.send_document(chat_id=channel_id, document=file_id)
        elif update.message.photo:
            sent_message = await context.bot.send_photo(chat_id=channel_id, photo=file_id)
        elif update.message.video:
            sent_message = await context.bot.send_video(chat_id=channel_id, video=file_id)
        elif update.message.audio:
            sent_message = await context.bot.send_audio(chat_id=channel_id, audio=file_id)

        # Generate the public URL for the file in the channel
        channel_message_id = sent_message.message_id

        # Handle channel_id (can be a string like '@channel_username' or an integer like -1001234567890)
        if isinstance(channel_id, str):
            # Remove '@' from the username
            channel_username = channel_id[1:]
            channel_url = f"https://t.me/{channel_username}/{channel_message_id}"
        else:
            # For integer channel IDs, use the format https://t.me/c/<channel_id>/<message_id>
            channel_url = f"https://t.me/c/{abs(channel_id)}/{channel_message_id}"

        # Store the file information for deletion
        uploaded_files[channel_message_id] = {
            "file_id": file_id,
            "file_type": "document" if update.message.document else
                         "photo" if update.message.photo else
                         "video" if update.message.video else
                         "audio",
            "user_id": user_id,
            "channel_id": channel_id
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
            await context.bot.delete_message(chat_id=uploaded_files[channel_message_id]["channel_id"], message_id=channel_message_id)
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
    application.add_handler(CommandHandler("choose_channel", choose_channel))

    # Add file handler
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO, handle_file))

    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(handle_channel_selection, pattern="^channel_"))
    application.add_handler(CallbackQueryHandler(handle_delete, pattern="^delete_"))

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
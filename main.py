import requests
import logging
import json
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import io

# Set up OpenRouter API key
OPENROUTER_API_KEY = "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"  # Replace with your OpenRouter API key
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Global variable to store conversation history
conversation_history = []

# Function to interact with OpenRouter's API for text
def chat_with_openrouter(prompt):
    global conversation_history
    # Add user message to conversation history
    conversation_history.append({"role": "user", "content": prompt})

    # Prepare the request payload
    payload = {
        "model": "openai/gpt-3.5-turbo",  # You can change this to any model supported by OpenRouter
        "messages": conversation_history
    }

    # Send the request to OpenRouter
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers)

    # Check for errors
    if response.status_code != 200:
        raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

    # Extract the assistant's reply
    assistant_reply = response.json()["choices"][0]["message"]["content"]
    # Add assistant's reply to conversation history
    conversation_history.append({"role": "assistant", "content": assistant_reply})

    return assistant_reply

# Function to handle image inputs
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get the image file from the user
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    # Convert the image to a format suitable for processing (e.g., base64 or PIL Image)
    image = Image.open(io.BytesIO(photo_bytes))

    # For now, let's just save the image and send a placeholder response
    image.save("user_image.png")
    await update.message.reply_text("🖼️ *Image received!* I'll process it shortly.", parse_mode="Markdown")

    # Example: Use an image processing API (e.g., GPT-4 Vision or OpenRouter's image-capable models)
    # You can integrate an API like OpenAI's GPT-4 Vision here to analyze the image.
    # For now, we'll just send a placeholder response.
    await update.message.reply_text("🔍 *Processing image...* This feature is under development!", parse_mode="Markdown")

# Save conversation history to a JSON file
def save_conversation():
    global conversation_history
    with open("conversation_history.json", "w") as file:
        json.dump(conversation_history, file, indent=4)

# Load conversation history from a JSON file
def load_conversation():
    global conversation_history
    try:
        with open("conversation_history.json", "r") as file:
            conversation_history = json.load(file)
    except FileNotFoundError:
        conversation_history = []

# Telegram bot command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Stylish welcome message with command list
    welcome_message = """
🌟 *Welcome to Your ChatGPT Bot!* 🌟

I'm powered by Hojiev Makhmud and ready to assist you. Here's what I can do:

📜 *Available Commands:*
/start - Start the bot and see the welcome message.
/history - View the conversation history between you and the bot.
/clear - Clear the conversation history.
/help - Show this list of commands.

🖼️ *Image Commands:*
- Send an image to analyze it (under development).

🚀 *Other Features:*
- Ask me anything! I can answer questions, help with coding, generate creative content, and more.

Just send me a message or an image, and I'll respond right away! 🚀
"""
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

# Telegram bot command: /history
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not conversation_history:
        await update.message.reply_text("📜 *No conversation history found.*", parse_mode="Markdown")
        return

    # Format the conversation history
    history_text = "📜 *Conversation History:*\n\n"
    for message in conversation_history:
        role = "👤 You" if message["role"] == "user" else "🤖 Bot"
        # Escape Markdown special characters
        content = message["content"].replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
        history_text += f"{role}: {content}\n\n"

    # Split the message if it exceeds the maximum length
    max_length = constants.MessageLimit.MAX_TEXT_LENGTH
    if len(history_text) > max_length:
        for i in range(0, len(history_text), max_length):
            await update.message.reply_text(history_text[i:i + max_length], parse_mode="Markdown")
    else:
        await update.message.reply_text(history_text, parse_mode="Markdown")

# Telegram bot command: /clear
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global conversation_history
    conversation_history = []
    save_conversation()
    await update.message.reply_text("🧹 *Conversation history cleared!*", parse_mode="Markdown")

# Telegram bot command: /help
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Command list text
    help_message = """
📜 *Available Commands:*

/start - Start the bot and see the welcome message.
/history - View the conversation history between you and the bot.
/clear - Clear the conversation history.
/help - Show this list of commands.

🖼️ *Image Commands:*
- Send an image to analyze it (under development).

🚀 *Other Features:*
- Ask me anything! I can answer questions, help with coding, generate creative content, and more.
"""
    await update.message.reply_text(help_message, parse_mode="Markdown")

# Telegram bot command: Handle all text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    # Check for specific questions about the creator
    creator_keywords = ["who created you", "who made you", "who is your creator", "who developed you"]
    if any(keyword in user_message.lower() for keyword in creator_keywords):
        await update.message.reply_text("🤖 *This bot was created by Makhmud Hojiev.*", parse_mode="Markdown")
        return

    # Typing indicator to simulate ChatGPT-like behavior
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Get bot's reply using OpenRouter
    try:
        bot_reply = chat_with_openrouter(user_message)
    except Exception as e:
        bot_reply = f"❌ *Oops! An error occurred:*\n```{str(e)}```"

    # Send the reply back to the user
    await update.message.reply_text(bot_reply, parse_mode="Markdown")

    # Save the conversation after each interaction
    save_conversation()

# Log errors
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")

# Main function to run the bot
def main():
    # Replace 'your_telegram_bot_token' with your actual bot token
    application = Application.builder().token("7068232790:AAHyixt2Ne5ObjUMvVwE5fxL4q3jjV7MtR8").build()

    # Load previous conversation history (if any)
    load_conversation()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
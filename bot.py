import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_IDS = [x.strip() for x in os.getenv("ADMIN_CHAT_IDS","").split(",") if x.strip()]
MODE = os.getenv("MODE","PAPER")

# Simple logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# strategy module
from ict_smc import analyze_prices, format_signal

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id in ADMIN_CHAT_IDS:
        await update.message.reply_text(f"Hello Admin! Your chat ID is {chat_id}\\nBot is running in {MODE} mode.")
    else:
        await update.message.reply_text("Hello — bot is running, but you are not an admin for trading actions.")

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Use exchangerate.host to get AUD -> USD rate (1 AUD = X USD)
        r = requests.get("https://api.exchangerate.host/latest", params={"base":"AUD","symbols":"USD"}, timeout=10)
        r.raise_for_status()
        js = r.json()
        rate = js.get("rates",{}).get("USD")
        if rate:
            await update.message.reply_text(f"AUD/USD (1 AUD = {rate:.6f} USD)")
        else:
            await update.message.reply_text("Price unavailable.")
    except Exception as e:
        logger.exception("price error")
        await update.message.reply_text(f"Error fetching price: {e}")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching recent prices and computing ICT/SMC signal...")
    try:
        # fetch recent daily series (last 30 days) as fallback for signal
        import datetime
        end = datetime.date.today()
        start = end - datetime.timedelta(days=30)
        r = requests.get("https://api.exchangerate.host/timeseries", params={
            "base":"AUD","symbols":"USD","start_date":start.isoformat(),"end_date":end.isoformat()
        }, timeout=15)
        r.raise_for_status()
        js = r.json()
        rates = js.get("rates", {})
        if not rates:
            await update.message.reply_text("Not enough data for signal.")
            return
        # build list of (date, price)
        series = sorted([(d, rates[d]["USD"]) for d in rates.keys()])
        dates = [d for d,p in series]
        prices = [p for d,p in series]
        # analyze
        res = analyze_prices(prices)
        msg = format_signal(res, prices[-1], dates[-1])
        await update.message.reply_text(msg)
    except Exception as e:
        logger.exception("signal error")
        await update.message.reply_text(f"Error generating signal: {e}")

def main():
    if not TOKEN:
        print("Please set TELEGRAM_TOKEN in environment (.env).")
        return
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("signal", signal))
    print("Bot started. Listening for commands...")
    app.run_polling()

if __name__ == '__main__':
    main()

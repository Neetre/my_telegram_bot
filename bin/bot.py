import logging
import os
from dotenv import load_dotenv
load_dotenv()

import requests
import sqlite3
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_NINJA_KEY = os.environ.get("API_NINJA_KEY")

RATE_LIMIT = 5
RATE_LIMIT_WINDOW = 60

user_requests: Dict[int, List[datetime]] = {}

class QuoteDB:
    def __init__(self):
        self.conn = sqlite3.connect('../data/quotes.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER,
            quote TEXT,
            author TEXT,
            category TEXT,
            added_date TIMESTAMP,
            PRIMARY KEY (user_id, quote)
        )''')
        self.conn.commit()

    def add_favorite(self, user_id: int, quote: str, author: str, category: str) -> bool:
        try:
            self.conn.execute(
                'INSERT INTO favorites VALUES (?, ?, ?, ?, ?)',
                (user_id, quote, author, category, datetime.now())
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_favorites(self, user_id: int) -> List[Tuple]:
        cursor = self.conn.execute(
            'SELECT quote, author, category FROM favorites WHERE user_id = ?',
            (user_id,)
        )
        return cursor.fetchall()

    def remove_favorite(self, user_id: int, quote: str) -> bool:
        cursor = self.conn.execute(
            'DELETE FROM favorites WHERE user_id = ? AND quote = ?',
            (user_id, quote)
        )
        self.conn.commit()
        return cursor.rowcount > 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I'm a bot that can give you quotes. Send /help to see all available commands.",
        reply_markup=ForceReply(selective=True),
    )

help_text = """
/help - Show this help message
/quote - Get a random quote
/favorite - Save the last quote to favorites
/favorites - Get a list of your favorite quotes
/remove_favorite <quote> - Remove a quote from favorites
"""

# /categories - Get a list of available categories

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(help_text)

async def check_rate_limit(user_id: int) -> bool:
    """Check if the user has exceeded the rate limit."""
    now = datetime.now()
    if user_id not in user_requests:
        user_requests[user_id] = []

    user_requests[user_id] = [req for req in user_requests[user_id] if now - req < timedelta(seconds=RATE_LIMIT_WINDOW)]
    
    if len(user_requests[user_id]) >= RATE_LIMIT:
        return False
    
    user_requests[user_id].append(now)
    return True

async def get_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_rate_limit(user_id):
        await update.message.reply_text("You've exceeded the rate limit. Please try again later.")
        return
    
    # category = context.args[0] if context.args else 'happiness'
    api_url = f'https://api.api-ninjas.com/v1/quotes' # ?category={category}
    try:
        response = requests.get(api_url, headers={'X-Api-Key': API_NINJA_KEY})
        response.raise_for_status()
        quote_data = response.json()[0]
        context.user_data['last_quote'] = quote_data  # Store the quote
        quote = f"{quote_data['quote']}\n- {quote_data['author']}"
        await update.message.reply_text(quote)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching quote: {e}")
        await update.message.reply_text("Sorry, I couldn't fetch a quote at the moment. Please try again later.")

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("../data/categories.txt", "r") as f:
            categories = f.read()
        await update.message.reply_text(categories)
    except IOError as e:
        logger.error(f"Error reading categories file: {e}")
        await update.message.reply_text("Sorry, I couldn't fetch the categories at the moment. Please try again later.")

async def add_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.user_data.get('last_quote'):
        await update.message.reply_text("No quote to save. Get a quote first!")
        return
    
    quote_data = context.user_data['last_quote']
    db = QuoteDB()
    
    if db.add_favorite(user_id, quote_data['quote'], quote_data['author'], quote_data['category']):
        await update.message.reply_text("Quote saved to favorites!")
    else:
        await update.message.reply_text("Quote already in favorites!")

async def get_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = QuoteDB()
    favorites = db.get_favorites(user_id)
    
    if not favorites:
        await update.message.reply_text("You haven't saved any favorites yet!")
        return
        
    response = "Your favorite quotes:\n\n"
    for quote, author, category in favorites:
        response += f"📝 {quote}\n- {author} ({category})\n\n"
    
    await update.message.reply_text(response)

async def remove_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Please provide a quote to remove.")
        return
    
    quote = ' '.join(context.args)
    db = QuoteDB()
    if db.remove_favorite(user_id, quote):
        await update.message.reply_text("Quote removed from favorites!")
    else:
        await update.message.reply_text("Quote not found in favorites.")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quote", get_quote))
    # application.add_handler(CommandHandler("categories", get_category))
    application.add_handler(CommandHandler("favorite", add_favorite))
    application.add_handler(CommandHandler("favorites", get_favorites))
    application.add_handler(CommandHandler("remove_favorite", remove_favorite))

    application.run_polling()

if __name__ == "__main__":
    main()
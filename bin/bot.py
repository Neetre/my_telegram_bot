import logging
import os
from dotenv import load_dotenv
load_dotenv()

import requests

import sqlite3
from datetime import datetime
from typing import List, Tuple

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_NINJA_KEY = os.environ.get("API_NINJA_KEY")


class QuoteDB:
    def __init__(self):
        self.conn = sqlite3.connect('../data/quotes.db')
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I'm a bot that can give you quotes. Send /quote to get a quote. Add a category to get a quote from a specific category. For example, /quote happiness",
        reply_markup=ForceReply(selective=True),
    )

help_text = """
/start - Start the bot
/help - Show this help message
/quote - Get a random quote
/quote <category> - Get a quote from a specific category
/categories - Get a list of available categories
/favorite - Save the last quote to favorites
/favorites - Get a list of your favorite quotes
"""

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(help_text)


async def get_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = context.args[0] if context.args else 'happiness'
    api_url = 'https://api.api-ninjas.com/v1/quotes?category={}'.format(category)
    response = requests.get(api_url, headers={'X-Api-Key': API_NINJA_KEY})
    if response.status_code == requests.codes.ok:
        quote_data = response.json()[0]
        context.user_data['last_quote'] = quote_data  # Store the quote
        quote = quote_data["quote"] + "\n- " + quote_data["author"]
        await update.message.reply_text(quote)
    else:
        await update.message.reply_text(f"Error: {response.status_code} {response.text}")


async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open("../data/categories.txt", "r") as f:
        categories = f.read()
    await update.message.reply_text(categories)


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


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quote", get_quote))
    application.add_handler(CommandHandler("categories", get_category))
    application.add_handler(CommandHandler("favorite", add_favorite))
    application.add_handler(CommandHandler("favorites", get_favorites))

    application.run_polling()


if __name__ == "__main__":
    main()

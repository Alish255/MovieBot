import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes
)
import openai

import os

# Ключи из переменных окружения
TMDB_KEY = os.getenv("TMDB_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_KEY")

openai.api_key = OPENAI_API_KEY

TMDB_URL = "https://api.themoviedb.org/3"


# --- ИИ РЕКОМЕНДАЦИИ ---
async def ai_recommend(query):
    prompt = f"""
    Пользователь ищет фильмы по запросу: {query}.
    Дай список из 5 фильмов с коротким объяснением.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]


# --- ПОИСК ФИЛЬМА ---
def search_movie_tmdb(query):
    url = f"{TMDB_URL}/search/movie"
    params = {
        "api_key": TMDB_KEY,
        "language": "ru-RU",
        "query": query
    }
    data = requests.get(url, params=params).json()
    if data.get("results"):
        return data["results"][0]
    return None


# --- ПОХОЖИЕ ФИЛЬМЫ ---
def get_similar_movies(movie_id):
    url = f"{TMDB_URL}/movie/{movie_id}/similar"
    params = {"api_key": TMDB_KEY, "language": "ru-RU"}
    data = requests.get(url, params=params).json()
    return data.get("results", [])[:5]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Привет! Напиши название фильма или задай вопрос про кино."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    movie = search_movie_tmdb(query)

    if movie:
        title = movie.get("title")
        desc = movie.get("overview", "Описание отсутствует.")
        rating = movie.get("vote_average", "?")
        poster = movie.get("poster_path")

        msg = f"🎬 *{title}*\n⭐ Рейтинг: {rating}\n\n{desc}"

        if poster:
            image_url = f"https://image.tmdb.org/t/p/w500{poster}"
            await update.message.reply_photo(image_url, caption=msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")

        similar = get_similar_movies(movie["id"])
        if similar:
            text = "🎯 *Похожие фильмы:*\n\n"
            for m in similar:
                text += f"• {m['title']} (⭐ {m.get('vote_average', '?')})\n"
            await update.message.reply_text(text, parse_mode="Markdown")

        return

    # если фильм не найден → ИИ
    ai_answer = await ai_recommend(query)
    await update.message.reply_text(ai_answer)


# --- ЗАПУСК ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()

import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ========================
# SOZLAMALAR
# ========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8621461817:AAHT3HBWe7ljJ64uDE13U1eDPVjmdiw1hVg")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",")]
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1004241881660")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ========================
# BAZA
# ========================
def init_db():
    conn = sqlite3.connect("movies.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            year INTEGER,
            genre TEXT,
            file_id TEXT NOT NULL,
            description TEXT,
            views INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect("movies.db")

def is_admin(user_id):
    return user_id in ADMIN_IDS

def save_user(user):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?,?,?)",
        (user.id, user.username, user.first_name)
    )
    conn.commit()
    conn.close()

# ========================
# /start
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"🎬 Salom, {name}!\n\n"
        "Kino botga xush kelibsiz!\n\n"
        "🔍 Kino nomini yozing — topib beraman\n"
        "📋 /list — barcha kinolar\n"
        "❓ /help — yordam"
    )

# ========================
# /help
# ========================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 Yordam\n\n"
        "👤 Foydalanuvchi:\n"
        "• Kino nomini yozing\n"
        "• /list — kinolar ro'yxati\n\n"
        "🔐 Admin:\n"
        "• /add — kino qo'shish\n"
        "• /delete [id] — o'chirish\n"
        "• /stats — statistika\n"
        "• /myid — ID ni bilish"
    )
    await update.message.reply_text(text)

# ========================
# /myid — admin ID bilish
# ========================
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Sizning ID: {update.effective_user.id}")

# ========================
# /list
# ========================
async def list_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    movies = conn.execute(
        "SELECT id, title, year, genre FROM movies ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()

    if not movies:
        await update.message.reply_text("📭 Hozircha kinolar yo'q.")
        return

    text = "🎬 Kinolar ro'yxati:\n\n"
    for m in movies:
        year = f" ({m[2]})" if m[2] else ""
        genre = f" | {m[3]}" if m[3] else ""
        text += f"🎥 {m[1]}{year}{genre}\n"
    await update.message.reply_text(text)

# ========================
# QIDIRISH
# ========================
async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    conn = get_db()
    results = conn.execute(
        "SELECT id, title, year, genre, file_id, description FROM movies WHERE title LIKE ? LIMIT 5",
        (f"%{query}%",)
    ).fetchall()
    conn.close()

    if not results:
        await update.message.reply_text(
            f"🔍 '{query}' topilmadi.\n\n"
            "/list orqali barcha kinolarni ko'ring."
        )
        return

    if len(results) == 1:
        await send_movie(update, results[0])
    else:
        buttons = [[InlineKeyboardButton(
            f"🎬 {m[1]}" + (f" ({m[2]})" if m[2] else ""),
            callback_data=f"movie_{m[0]}"
        )] for m in results]
        await update.message.reply_text(
            f"🔍 '{query}' bo'yicha {len(results)} ta natija:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

async def send_movie(update, movie):
    movie_id, title, year, genre, file_id, description = movie
    caption = f"🎬 {title}"
    if year: caption += f"\n📅 Yil: {year}"
    if genre: caption += f"\n🎭 Janr: {genre}"
    if description: caption += f"\n\n📝 {description}"

    conn = get_db()
    conn.execute("UPDATE movies SET views = views + 1 WHERE id = ?", (movie_id,))
    conn.commit()
    conn.close()

    msg = update.message if update.message else update.callback_query.message
    await msg.reply_video(video=file_id, caption=caption)

async def movie_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = int(query.data.split("_")[1])
    conn = get_db()
    movie = conn.execute(
        "SELECT id, title, year, genre, file_id, description FROM movies WHERE id = ?",
        (movie_id,)
    ).fetchone()
    conn.close()
    if movie:
        await send_movie(update, movie)
    else:
        await query.message.reply_text("❌ Kino topilmadi.")

# ========================
# ADMIN: /add
# ========================
async def add_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sizda admin huquqi yo'q.\n\n/myid buyrug'i bilan ID ni bilib, botni sozlang.")
        return
    context.user_data["adding"] = {"step": "title"}
    await update.message.reply_text("➕ Kino qo'shish\n\n1️⃣ Kino nomini yozing:")

async def handle_admin_steps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "adding" not in context.user_data:
        return False
    data = context.user_data["adding"]
    text = update.message.text

    if data["step"] == "title":
        data["title"] = text
        data["step"] = "year"
        await update.message.reply_text("2️⃣ Yilini yozing (masalan: 2024)\no'tkazish uchun: -")
    elif data["step"] == "year":
        data["year"] = int(text) if text.isdigit() else None
        data["step"] = "genre"
        await update.message.reply_text("3️⃣ Janrini yozing (masalan: Drama)\no'tkazish uchun: -")
    elif data["step"] == "genre":
        data["genre"] = None if text == "-" else text
        data["step"] = "description"
        await update.message.reply_text("4️⃣ Tavsif yozing\no'tkazish uchun: -")
    elif data["step"] == "description":
        data["description"] = None if text == "-" else text
        data["step"] = "file"
        await update.message.reply_text("5️⃣ Endi video faylni yuboring 🎬\n(Kanalingizdan forward qiling)")
    return True

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if "adding" not in context.user_data:
        return
    if context.user_data["adding"].get("step") != "file":
        return

    data = context.user_data["adding"]
    video = update.message.video or update.message.document
    if not video:
        await update.message.reply_text("❌ Video yuboring!")
        return

    conn = get_db()
    conn.execute(
        "INSERT INTO movies (title, year, genre, file_id, description) VALUES (?,?,?,?,?)",
        (data["title"], data.get("year"), data.get("genre"), video.file_id, data.get("description"))
    )
    conn.commit()
    conn.close()

    del context.user_data["adding"]
    await update.message.reply_text(f"✅ '{data['title']}' muvaffaqiyatli qo'shildi!")

# ========================
# ADMIN: /delete
# ========================
async def delete_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sizda admin huquqi yo'q.")
        return
    if not context.args:
        await update.message.reply_text("Foydalanish: /delete [ID]\nMasalan: /delete 5")
        return
    conn = get_db()
    movie = conn.execute("SELECT title FROM movies WHERE id = ?", (context.args[0],)).fetchone()
    if movie:
        conn.execute("DELETE FROM movies WHERE id = ?", (context.args[0],))
        conn.commit()
        await update.message.reply_text(f"🗑 '{movie[0]}' o'chirildi.")
    else:
        await update.message.reply_text("❌ Bu ID bilan kino topilmadi.")
    conn.close()

# ========================
# ADMIN: /stats
# ========================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    conn = get_db()
    total_movies = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    top = conn.execute("SELECT title, views FROM movies ORDER BY views DESC LIMIT 5").fetchall()
    conn.close()

    text = f"📊 Statistika\n\n🎬 Kinolar: {total_movies}\n👤 Foydalanuvchilar: {total_users}\n\n🔥 Top kinolar:\n"
    for i, (title, views) in enumerate(top, 1):
        text += f"{i}. {title} — {views} marta\n"
    await update.message.reply_text(text)

# ========================
# ASOSIY HANDLER
# ========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_admin_steps(update, context):
        return
    await search_movie(update, context)

# ========================
# ISHGA TUSHIRISH
# ========================
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("list", list_movies))
    app.add_handler(CommandHandler("add", add_movie))
    app.add_handler(CommandHandler("delete", delete_movie))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(movie_callback, pattern="^movie_"))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()

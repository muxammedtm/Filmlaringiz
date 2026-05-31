from telegram import Update
from telegram.ext import ContextTypes
from database import Database
from texts import t
from keyboards import (
    lang_keyboard, main_menu, subscription_keyboard, movie_keyboard
)
from config import Config

db = Database()
cfg = Config()


async def _check_sub(user_id, bot) -> list:
    if db.get_setting("sub_required") != "1":
        return []
    channels = db.get_channels()
    not_subbed = []
    for ch in channels:
        try:
            m = await bot.get_chat_member(ch["channel_id"], user_id)
            if m.status in ("left", "kicked", "banned"):
                not_subbed.append(ch)
        except Exception:
            not_subbed.append(ch)
    return not_subbed


def _lang(user_id) -> str:
    u = db.get_user(user_id)
    return u["lang"] if u else "uz"


# ─── /start ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args  # deep link parametri

    # Yangi foydalanuvchi
    if not db.get_user(user.id):
        db.add_user(user.id, user.username or "", user.first_name or "")
        await update.message.reply_text(
            t("choose_lang", "uz"),
            reply_markup=lang_keyboard(),
            parse_mode="HTML"
        )
        if args:
            context.user_data["pending_code"] = args[0]
        return

    if db.is_banned(user.id):
        await update.message.reply_text(t("banned", _lang(user.id)))
        return

    lang = _lang(user.id)

    # Majburiy obuna
    not_subbed = await _check_sub(user.id, context.bot)
    if not_subbed:
        await update.message.reply_text(
            t("sub_required", lang),
            reply_markup=subscription_keyboard(not_subbed, lang),
            parse_mode="HTML"
        )
        if args:
            context.user_data["pending_code"] = args[0]
        return

    # Deep link orqali kino kodi
    if args:
        await _send_movie(update, context, args[0], lang)
        return

    await update.message.reply_text(
        t("main_menu", lang),
        reply_markup=main_menu(lang),
        parse_mode="HTML"
    )


# ─── TIL TANLASH ─────────────────────────────────────────────────────────────

async def cb_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data.split("_")[1]  # lang_uz → uz

    db.set_lang(user_id, lang)
    await query.message.edit_text(t("lang_set", lang), parse_mode="HTML")

    # Pending kod bormi?
    pending = context.user_data.pop("pending_code", None)
    if pending:
        not_subbed = await _check_sub(user_id, context.bot)
        if not_subbed:
            await query.message.reply_text(
                t("sub_required", lang),
                reply_markup=subscription_keyboard(not_subbed, lang),
                parse_mode="HTML"
            )
            context.user_data["pending_code"] = pending
            return
        await _send_movie_query(query, context, pending, lang)
        return

    await query.message.reply_text(
        t("main_menu", lang),
        reply_markup=main_menu(lang),
        parse_mode="HTML"
    )


# ─── OBUNA TEKSHIRISH ─────────────────────────────────────────────────────────

async def cb_check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = _lang(user_id)

    not_subbed = await _check_sub(user_id, context.bot)
    if not_subbed:
        await query.message.edit_text(
            t("sub_not_done", lang),
            reply_markup=subscription_keyboard(not_subbed, lang),
            parse_mode="HTML"
        )
        return

    await query.message.edit_text(t("sub_ok", lang), parse_mode="HTML")

    # Pending kod
    pending = context.user_data.pop("pending_code", None)
    if pending:
        await _send_movie_query(query, context, pending, lang)
        return

    await context.bot.send_message(
        user_id, t("main_menu", lang),
        reply_markup=main_menu(lang),
        parse_mode="HTML"
    )


# ─── KINO YUBORISH YORDAMCHI ─────────────────────────────────────────────────

async def _send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str, lang: str):
    user_id = update.effective_user.id
    movie = db.get_movie_by_code(code.strip())
    if not movie:
        await update.message.reply_text(t("movie_not_found", lang), parse_mode="HTML")
        return
    await _deliver_movie(context.bot, user_id, movie, lang)


async def _send_movie_query(query, context, code: str, lang: str):
    user_id = query.from_user.id
    movie = db.get_movie_by_code(code.strip())
    if not movie:
        await context.bot.send_message(user_id, t("movie_not_found", lang), parse_mode="HTML")
        return
    await _deliver_movie(context.bot, user_id, movie, lang)


async def _deliver_movie(bot, user_id, movie: dict, lang: str):
    db.inc_views(movie["id"])
    db.add_history(user_id, movie["id"])
    is_fav = db.is_favorite(user_id, movie["id"])
    protect = db.get_setting("save_block") == "1"

    cap = f"🎬 <b>{movie['title']}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    if movie.get("description"):
        cap += f"📝 {movie['description']}\n"
    if movie.get("year"):
        cap += f"📅 {'Yil' if lang == 'uz' else 'Год'}: {movie['year']}\n"
    if movie.get("genre"):
        cap += f"🎭 {'Janr' if lang == 'uz' else 'Жанр'}: {movie['genre']}\n"
    if movie.get("category"):
        cap += f"📂 {movie['category']}\n"
    cap += f"\n🆔 Kod: <code>{movie['code']}</code>"

    kb = movie_keyboard(movie["id"], is_fav, lang)
    try:
        await bot.send_video(
            user_id, video=movie["file_id"],
            caption=cap, parse_mode="HTML",
            reply_markup=kb,
            protect_content=protect
        )
    except Exception:
        await bot.send_document(
            user_id, document=movie["file_id"],
            caption=cap, parse_mode="HTML",
            reply_markup=kb,
            protect_content=protect
        )


# ─── XABAR HANDLER ───────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not db.get_user(user.id):
        await cmd_start(update, context)
        return
    if db.is_banned(user.id):
        return

    lang = _lang(user.id)
    not_subbed = await _check_sub(user.id, context.bot)
    if not_subbed:
        await update.message.reply_text(
            t("sub_required", lang),
            reply_markup=subscription_keyboard(not_subbed, lang),
            parse_mode="HTML"
        )
        return

    text = update.message.text.strip()

    # ─── Tugma navlari ───
    if text in ("🎬 Kino qidirish", "🎬 Поиск фильма"):
        await update.message.reply_text(t("send_code", lang), parse_mode="HTML")
        return

    if text in ("⭐ Sevimlilar", "⭐ Избранное"):
        await show_favorites(update, context, lang)
        return

    if text in ("🔥 TOP kinolar", "🔥 ТОП фильмов"):
        await show_top(update, context, lang)
        return

    if text in ("🆕 Yangi kinolar", "🆕 Новые"):
        await show_new(update, context, lang)
        return

    if text in ("📜 Tarix", "📜 История"):
        await show_history(update, context, lang)
        return

    if text in ("🌐 Til", "🌐 Язык"):
        await update.message.reply_text(t("choose_lang", lang), reply_markup=lang_keyboard(), parse_mode="HTML")
        return

    if text in ("ℹ️ Yordam", "ℹ️ Помощь"):
        await update.message.reply_text(t("help", lang), parse_mode="HTML")
        return

    # ─── Kino kodi ───
    await _send_movie(update, context, text, lang)


# ─── SEVIMLILAR ──────────────────────────────────────────────────────────────

async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    user_id = update.effective_user.id
    favs = db.get_favorites(user_id)
    if not favs:
        await update.message.reply_text(t("favorites_empty", lang), parse_mode="HTML")
        return
    text = ("⭐ <b>Sevimli kinolar:</b>" if lang == "uz" else "⭐ <b>Избранные фильмы:</b>") + "\n━━━━━━━━━━━━━━━━━━━━\n"
    for f in favs:
        text += f"🎬 {f['title']} — <code>{f['code']}</code>\n"
    await update.message.reply_text(text, parse_mode="HTML")


# ─── TOP ─────────────────────────────────────────────────────────────────────

async def show_top(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    top = db.get_top_movies()
    text = t("top_movies", lang) + "\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, m in enumerate(top, 1):
        text += f"{i}. {m['title']} — <code>{m['code']}</code> 👁 {m['views']}\n"
    await update.message.reply_text(text, parse_mode="HTML")


# ─── YANGI ───────────────────────────────────────────────────────────────────

async def show_new(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    new = db.get_new_movies()
    text = t("new_movies", lang) + "\n━━━━━━━━━━━━━━━━━━━━\n"
    for m in new:
        text += f"🎬 {m['title']} — <code>{m['code']}</code>\n"
    await update.message.reply_text(text, parse_mode="HTML")


# ─── TARIX ───────────────────────────────────────────────────────────────────

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    user_id = update.effective_user.id
    hist = db.get_history(user_id)
    if not hist:
        await update.message.reply_text(t("history_empty", lang), parse_mode="HTML")
        return
    label = "📜 <b>Oxirgi ko'rganlar:</b>" if lang == "uz" else "📜 <b>История просмотров:</b>"
    text = label + "\n━━━━━━━━━━━━━━━━━━━━\n"
    for h in hist:
        text += f"🎬 {h['title']} — <code>{h['code']}</code>\n"
    await update.message.reply_text(text, parse_mode="HTML")


# ─── SEVIMLI TUGMA CALLBACK ──────────────────────────────────────────────────

async def cb_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = _lang(user_id)
    data = query.data  # fav_add_123 yoki fav_remove_123
    parts = data.split("_")
    action = parts[1]   # add / remove
    movie_id = int(parts[2])

    if action == "add":
        db.add_favorite(user_id, movie_id)
        await query.answer(t("added_to_fav", lang), show_alert=True)
        new_kb = movie_keyboard(movie_id, True, lang)
    else:
        db.remove_favorite(user_id, movie_id)
        await query.answer(t("removed_from_fav", lang), show_alert=True)
        new_kb = movie_keyboard(movie_id, False, lang)

    try:
        await query.message.edit_reply_markup(reply_markup=new_kb)
    except Exception:
        pass
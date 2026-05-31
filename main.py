import logging
import sys
import os

# Handlers papkasini path ga qo'shish
sys.path.insert(0, os.path.dirname(__file__))

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

from config import Config
from database import Database
from handlers.user import (
    cmd_start, cb_lang, cb_check_sub, handle_text, cb_favorite
)
from handlers.admin import (
    cmd_admin, admin_callback, admin_state_handler
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

cfg = Config()
db  = Database(cfg.DB_PATH)


# ─── UNIVERSAL TEXT HANDLER ──────────────────────────────────────────────────

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin state borligini tekshiradi, yo'q bo'lsa user handleriga uzatadi"""
    if update.effective_user and update.effective_user.id in db.get_admin_ids() or \
       (update.effective_user and update.effective_user.id == cfg.OWNER_ID):
        handled = await admin_state_handler(update, context)
        if handled:
            return
    await handle_text(update, context)


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    logger.info("🚀 Bot ishga tushmoqda...")

    if cfg.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN o'rnatilmagan! config.py ni to'ldiring.")
        return

    app = Application.builder().token(cfg.BOT_TOKEN).build()

    # ── Buyruqlar ─────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))

    # ── Callback querylar ─────────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(cb_lang,      pattern=r"^lang_"))
    app.add_handler(CallbackQueryHandler(cb_check_sub, pattern=r"^check_sub$"))
    app.add_handler(CallbackQueryHandler(cb_favorite,  pattern=r"^fav_"))
    app.add_handler(CallbackQueryHandler(admin_callback))  # qolgan admin callback lar

    # ── Xabarlar ──────────────────────────────────────────────────────────────
    app.add_handler(MessageHandler(
        filters.TEXT | filters.VIDEO | filters.Document.ALL | filters.PHOTO,
        universal_handler
    ))

    logger.info("✅ Bot muvaffaqiyatli ishga tushdi!")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
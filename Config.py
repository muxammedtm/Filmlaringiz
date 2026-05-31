import os

class Config:
    # ============================================
    #  BOT ASOSIY SOZLAMALARI
    # ============================================
    BOT_TOKEN   = os.getenv("BOT_TOKEN", "8621461817:AAHT3HBWe7ljJ64uDE13U1eDPVjmdiw1hVg")
    OWNER_ID    = int(os.getenv("OWNER_ID", "610489050"))
    DB_PATH     = os.getenv("DB_PATH", "kinobot.db")

    # Kanal post uchun (kino qo'shilganda avtomatik post chiqadigan kanal)
    # Agar yo'q bo'lsa bo'sh qoldiring
    POST_CHANNEL = os.getenv("POST_CHANNEL", "")   # Masalan: "@kinolar_uz"

    # Bot username (deep link uchun)
    BOT_USERNAME = os.getenv("BOT_USERNAME", "filmlaringizbot")  # @ siz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# ─── TIL TANLASH ─────────────────────────────────────────────────────────────

def lang_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        ]
    ])

# ─── ASOSIY MENYU ────────────────────────────────────────────────────────────

def main_menu(lang="uz"):
    if lang == "ru":
        buttons = [
            [KeyboardButton("🎬 Поиск фильма"),   KeyboardButton("⭐ Избранное")],
            [KeyboardButton("🔥 ТОП фильмов"),    KeyboardButton("🆕 Новые")],
            [KeyboardButton("📜 История"),         KeyboardButton("🌐 Язык")],
            [KeyboardButton("ℹ️ Помощь")],
        ]
    else:
        buttons = [
            [KeyboardButton("🎬 Kino qidirish"),  KeyboardButton("⭐ Sevimlilar")],
            [KeyboardButton("🔥 TOP kinolar"),     KeyboardButton("🆕 Yangi kinolar")],
            [KeyboardButton("📜 Tarix"),           KeyboardButton("🌐 Til")],
            [KeyboardButton("ℹ️ Yordam")],
        ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ─── OBUNA ───────────────────────────────────────────────────────────────────

def subscription_keyboard(channels: list, lang="uz"):
    rows = []
    for ch in channels:
        rows.append([InlineKeyboardButton(
            f"📢 {ch['title']}",
            url=f"https://t.me/{ch['username'].lstrip('@')}"
        )])
    label = "✅ Tekshirish" if lang == "uz" else "✅ Проверить"
    rows.append([InlineKeyboardButton(label, callback_data="check_sub")])
    return InlineKeyboardMarkup(rows)

# ─── KINO TUGMALARI ──────────────────────────────────────────────────────────

def movie_keyboard(movie_id, is_fav=False, lang="uz"):
    fav_label = ("🗑 Sevimlilardan o'chir" if is_fav else "⭐ Sevimlilarga qo'sh") if lang == "uz" \
        else ("🗑 Удалить из избранного" if is_fav else "⭐ В избранное")
    fav_cb = f"fav_remove_{movie_id}" if is_fav else f"fav_add_{movie_id}"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(fav_label, callback_data=fav_cb)
    ]])

# ─── ADMIN PANEL ─────────────────────────────────────────────────────────────

def admin_main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 Kinolar",    callback_data="adm_movies"),
            InlineKeyboardButton("📢 Kanallar",   callback_data="adm_channels"),
        ],
        [
            InlineKeyboardButton("📨 Broadcast",  callback_data="adm_broadcast"),
            InlineKeyboardButton("👥 Users",      callback_data="adm_users"),
        ],
        [
            InlineKeyboardButton("👑 Adminlar",   callback_data="adm_admins"),
            InlineKeyboardButton("⚙️ Sozlamalar", callback_data="adm_settings"),
        ],
        [
            InlineKeyboardButton("📊 Statistika", callback_data="adm_stats"),
        ],
    ])

def admin_movies_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Qo'shish",   callback_data="mov_add"),
            InlineKeyboardButton("📋 Ro'yxat",    callback_data="mov_list_0"),
        ],
        [
            InlineKeyboardButton("🔍 Qidirish",   callback_data="mov_search"),
            InlineKeyboardButton("🔥 TOP",         callback_data="mov_top"),
        ],
        [InlineKeyboardButton("🔙 Orqaga",        callback_data="adm_back")],
    ])

def admin_channels_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Qo'shish",   callback_data="ch_add"),
            InlineKeyboardButton("📋 Ro'yxat",    callback_data="ch_list"),
        ],
        [
            InlineKeyboardButton("🔒 Obuna holati", callback_data="ch_toggle_sub"),
        ],
        [InlineKeyboardButton("🔙 Orqaga",        callback_data="adm_back")],
    ])

def admin_users_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 Ro'yxat",   callback_data="usr_list_0"),
            InlineKeyboardButton("🔍 Qidirish",  callback_data="usr_search"),
        ],
        [
            InlineKeyboardButton("📥 Export",    callback_data="usr_export"),
        ],
        [InlineKeyboardButton("🔙 Orqaga",       callback_data="adm_back")],
    ])

def admin_settings_keyboard(fwd_block, save_block):
    fwd_icon  = "✅" if fwd_block  == "1" else "❌"
    save_icon = "✅" if save_block == "1" else "❌"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{fwd_icon} Forward bloklash",  callback_data="set_toggle_forward")],
        [InlineKeyboardButton(f"{save_icon} Saqlash bloklash", callback_data="set_toggle_save")],
        [InlineKeyboardButton("🔙 Orqaga",                     callback_data="adm_back")],
    ])

def admin_admins_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Qo'shish",    callback_data="aadm_add"),
            InlineKeyboardButton("📋 Ro'yxat",     callback_data="aadm_list"),
        ],
        [InlineKeyboardButton("🔙 Orqaga",         callback_data="adm_back")],
    ])

def admin_broadcast_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 Barchaga",      callback_data="bc_all")],
        [InlineKeyboardButton("👥 Faol userlarga", callback_data="bc_active")],
        [InlineKeyboardButton("🔙 Orqaga",         callback_data="adm_back")],
    ])

def back_admin():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")]])

def movie_admin_actions(movie_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"medit_{movie_id}"),
            InlineKeyboardButton("❌ O'chirish",  callback_data=f"mdel_{movie_id}"),
        ],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="mov_list_0")],
    ])

def movie_edit_fields(movie_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Nom",       callback_data=f"mfield_title_{movie_id}")],
        [InlineKeyboardButton("📄 Tavsif",    callback_data=f"mfield_description_{movie_id}")],
        [InlineKeyboardButton("📅 Yil",       callback_data=f"mfield_year_{movie_id}")],
        [InlineKeyboardButton("🎭 Janr",      callback_data=f"mfield_genre_{movie_id}")],
        [InlineKeyboardButton("📂 Kategoriya",callback_data=f"mfield_category_{movie_id}")],
        [InlineKeyboardButton("🔢 Kod",       callback_data=f"mfield_code_{movie_id}")],
        [InlineKeyboardButton("🔙 Orqaga",    callback_data=f"minfo_{movie_id}")],
    ])
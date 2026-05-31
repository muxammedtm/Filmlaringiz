import asyncio
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from config import Config
from keyboards import (
    admin_main_keyboard, admin_movies_keyboard, admin_channels_keyboard,
    admin_users_keyboard, admin_settings_keyboard, admin_admins_keyboard,
    admin_broadcast_keyboard, back_admin, movie_admin_actions, movie_edit_fields
)

db  = Database()
cfg = Config()

ROLES = {
    "super_admin":    "👑 Super Admin",
    "moderator":      "🛡 Moderator",
    "content_admin":  "🎬 Kontent Admin",
    "ads_admin":      "📢 Reklama Admin",
}


def is_admin(user_id: int) -> bool:
    return user_id == cfg.OWNER_ID or user_id in db.get_admin_ids()

def has_role(user_id: int, *roles) -> bool:
    if user_id == cfg.OWNER_ID:
        return True
    role = db.get_admin_role(user_id)
    return role in roles


# ─── /admin ──────────────────────────────────────────────────────────────────

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Ruxsat yo'q!")
        return
    s = db.get_stats()
    text = (
        f"👑 <b>Admin Panel</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Foydalanuvchilar: <b>{s['users']}</b>\n"
        f"📈 Bugun qo'shilganlar: <b>{s['today_users']}</b>\n"
        f"🎬 Kinolar: <b>{s['movies']}</b>\n"
        f"📢 Kanallar: <b>{s['channels']}</b>\n"
        f"👑 Adminlar: <b>{s['admins']}</b>\n"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=admin_main_keyboard())


# ─── ADMIN CALLBACK DISPATCHER ───────────────────────────────────────────────

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.message.edit_text("❌ Ruxsat yo'q!")
        return

    data = query.data

    # ── Asosiy panel ──────────────────────────────────────────────────────────
    if data == "adm_back":
        s = db.get_stats()
        text = (
            f"👑 <b>Admin Panel</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Foydalanuvchilar: <b>{s['users']}</b>\n"
            f"📈 Bugun: <b>{s['today_users']}</b>\n"
            f"🎬 Kinolar: <b>{s['movies']}</b>\n"
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=admin_main_keyboard())

    # ── Statistika ────────────────────────────────────────────────────────────
    elif data == "adm_stats":
        s = db.get_stats()
        text = (
            f"📊 <b>Bot Statistikasi</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Jami foydalanuvchilar: <b>{s['users']}</b>\n"
            f"📈 Bugungi yangilar: <b>{s['today_users']}</b>\n"
            f"🎬 Jami kinolar: <b>{s['movies']}</b>\n"
            f"📢 Aktiv kanallar: <b>{s['channels']}</b>\n"
            f"👑 Adminlar: <b>{s['admins']}</b>\n"
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_admin())

    # ── KINOLAR ───────────────────────────────────────────────────────────────
    elif data == "adm_movies":
        await query.message.edit_text("🎬 <b>Kino boshqaruvi</b>", parse_mode="HTML",
                                       reply_markup=admin_movies_keyboard())

    elif data == "mov_add":
        context.user_data["adm_state"] = "mov_title"
        await query.message.edit_text(
            "🎬 <b>Kino qo'shish</b>\n\n1️⃣ Film nomini yuboring:",
            parse_mode="HTML", reply_markup=back_admin()
        )

    elif data.startswith("mov_list_"):
        offset = int(data.split("_")[-1])
        movies = db.get_all_movies(limit=10, offset=offset)
        if not movies:
            await query.message.edit_text("🎬 Kinolar yo'q.", reply_markup=back_admin())
            return
        text = f"🎬 <b>Kinolar ro'yxati</b> ({offset+1}–{offset+len(movies)}):\n━━━━━━━━━━━━━━━━━━━━\n"
        kb = []
        for m in movies:
            text += f"• <code>{m['code']}</code> — {m['title']} 👁{m['views']}\n"
            kb.append([InlineKeyboardButton(
                f"🎬 {m['title'][:25]}", callback_data=f"minfo_{m['id']}"
            )])
        nav = []
        if offset > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"mov_list_{offset-10}"))
        if len(movies) == 10:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"mov_list_{offset+10}"))
        if nav:
            kb.append(nav)
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_movies")])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("minfo_"):
        movie_id = int(data.split("_")[1])
        m = db.get_movie_by_id(movie_id)
        if not m:
            await query.message.edit_text("❌ Kino topilmadi.", reply_markup=back_admin())
            return
        text = (
            f"🎬 <b>{m['title']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Kod: <code>{m['code']}</code>\n"
            f"📅 Yil: {m.get('year') or '—'}\n"
            f"🎭 Janr: {m.get('genre') or '—'}\n"
            f"📂 Kategoriya: {m.get('category') or '—'}\n"
            f"👁 Ko'rilgan: {m['views']}\n"
            f"🗓 Qo'shilgan: {m.get('added_at','')[:10]}\n"
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=movie_admin_actions(movie_id))

    elif data.startswith("medit_"):
        movie_id = int(data.split("_")[1])
        await query.message.edit_text(
            "✏️ <b>Qaysi maydonni tahrirlash?</b>", parse_mode="HTML",
            reply_markup=movie_edit_fields(movie_id)
        )

    elif data.startswith("mfield_"):
        parts = data.split("_")
        field = parts[1]
        movie_id = int(parts[2])
        context.user_data["adm_state"] = f"mfield_{field}_{movie_id}"
        labels = {
            "title": "Yangi nomni", "description": "Yangi tavsifni",
            "year": "Yangi yilni", "genre": "Yangi janrni",
            "category": "Yangi kategoriyani", "code": "Yangi kodni"
        }
        await query.message.edit_text(
            f"✏️ {labels.get(field, field)} yuboring:", reply_markup=back_admin()
        )

    elif data.startswith("mdel_"):
        movie_id = int(data.split("_")[1])
        db.delete_movie(movie_id)
        await query.message.edit_text(
            "✅ Kino o'chirildi!", reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ro'yxat", callback_data="mov_list_0")
            ]])
        )

    elif data == "mov_search":
        context.user_data["adm_state"] = "mov_search"
        await query.message.edit_text("🔍 Kino nomi yoki kodini yuboring:", reply_markup=back_admin())

    elif data == "mov_top":
        top = db.get_top_movies(10)
        text = "🔥 <b>TOP 10 kinolar:</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        for i, m in enumerate(top, 1):
            text += f"{i}. {m['title']} <code>{m['code']}</code> 👁{m['views']}\n"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_admin())

    # ── KANALLAR ──────────────────────────────────────────────────────────────
    elif data == "adm_channels":
        await query.message.edit_text("📢 <b>Kanal boshqaruvi</b>", parse_mode="HTML",
                                       reply_markup=admin_channels_keyboard())

    elif data == "ch_add":
        context.user_data["adm_state"] = "ch_add"
        await query.message.edit_text(
            "📢 <b>Kanal qo'shish</b>\n\nKanal username'ini yuboring:\nMasalan: <code>@mychannelname</code>",
            parse_mode="HTML", reply_markup=back_admin()
        )

    elif data == "ch_list":
        channels = db.get_channels()
        if not channels:
            await query.message.edit_text("📢 Kanallar yo'q.", reply_markup=back_admin())
            return
        text = "📢 <b>Majburiy kanallar:</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        kb = []
        for ch in channels:
            text += f"• {ch['title']} ({ch['username']})\n"
            kb.append([InlineKeyboardButton(
                f"🗑 {ch['title'][:25]}", callback_data=f"ch_del_{ch['id']}"
            )])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_channels")])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("ch_del_"):
        ch_id = int(data.split("_")[-1])
        db.delete_channel(ch_id)
        await query.message.edit_text("✅ Kanal o'chirildi!", reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Kanallar", callback_data="ch_list")
        ]]))

    elif data == "ch_toggle_sub":
        cur = db.get_setting("sub_required")
        new = "0" if cur == "1" else "1"
        db.set_setting("sub_required", new)
        status = "✅ YOQILDI" if new == "1" else "❌ O'CHIRILDI"
        await query.message.edit_text(
            f"📢 Majburiy obuna: <b>{status}</b>", parse_mode="HTML",
            reply_markup=admin_channels_keyboard()
        )

    # ── BROADCAST ────────────────────────────────────────────────────────────
    elif data == "adm_broadcast":
        await query.message.edit_text(
            "📨 <b>Xabar yuborish</b>\n\nKimga yubormoqchisiz?",
            parse_mode="HTML", reply_markup=admin_broadcast_keyboard()
        )

    elif data in ("bc_all", "bc_active"):
        context.user_data["adm_state"] = f"broadcast_{data}"
        label = "Barcha foydalanuvchilarga" if data == "bc_all" else "So'nggi 7 kun faol userlarga"
        await query.message.edit_text(
            f"📨 <b>{label}</b> yuboriladigan xabarni yuboring:\n\n"
            f"<i>Matn, rasm, video yoki dokument bo'lishi mumkin.</i>\n"
            f"❌ Bekor qilish: /cancel",
            parse_mode="HTML", reply_markup=back_admin()
        )

    # ── USERS ────────────────────────────────────────────────────────────────
    elif data == "adm_users":
        await query.message.edit_text("👥 <b>Foydalanuvchilar</b>", parse_mode="HTML",
                                       reply_markup=admin_users_keyboard())

    elif data.startswith("usr_list_"):
        offset = int(data.split("_")[-1])
        users = db.get_all_users_info(limit=10, offset=offset)
        if not users:
            await query.message.edit_text("👥 Foydalanuvchilar yo'q.", reply_markup=back_admin())
            return
        text = f"👥 <b>Foydalanuvchilar</b> ({offset+1}–{offset+len(users)}):\n━━━━━━━━━━━━━━━━━━━━\n"
        kb = []
        for u in users:
            ban_icon = "🚫" if u["is_banned"] else "✅"
            uname = f"@{u['username']}" if u["username"] else u["first_name"]
            text += f"{ban_icon} {uname} (<code>{u['user_id']}</code>)\n"
            kb.append([InlineKeyboardButton(
                f"{ban_icon} {uname[:20]}", callback_data=f"uinfo_{u['user_id']}"
            )])
        nav = []
        if offset > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"usr_list_{offset-10}"))
        if len(users) == 10:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"usr_list_{offset+10}"))
        if nav:
            kb.append(nav)
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_users")])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("uinfo_"):
        uid = int(data.split("_")[1])
        u = db.get_user(uid)
        if not u:
            await query.message.edit_text("❌ Topilmadi.", reply_markup=back_admin())
            return
        ban_icon = "🚫 BAN" if u["is_banned"] else "✅ Aktiv"
        uname = f"@{u['username']}" if u["username"] else "—"
        text = (
            f"👤 <b>Foydalanuvchi</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: <code>{u['user_id']}</code>\n"
            f"👤 Ism: {u['first_name']}\n"
            f"📛 Username: {uname}\n"
            f"🌐 Til: {u['lang']}\n"
            f"📅 Qo'shilgan: {u['joined_at']}\n"
            f"⚡ Holat: {ban_icon}\n"
        )
        ban_cb = f"uunban_{uid}" if u["is_banned"] else f"uban_{uid}"
        ban_label = "✅ Unban" if u["is_banned"] else "🚫 Ban"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(ban_label, callback_data=ban_cb)],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="usr_list_0")],
        ]))

    elif data.startswith("uban_"):
        uid = int(data.split("_")[1])
        db.ban_user(uid)
        await query.message.edit_text(f"🚫 User <code>{uid}</code> ban qilindi.", parse_mode="HTML",
                                       reply_markup=back_admin())

    elif data.startswith("uunban_"):
        uid = int(data.split("_")[1])
        db.unban_user(uid)
        await query.message.edit_text(f"✅ User <code>{uid}</code> unban qilindi.", parse_mode="HTML",
                                       reply_markup=back_admin())

    elif data == "usr_search":
        context.user_data["adm_state"] = "usr_search"
        await query.message.edit_text("🔍 Foydalanuvchi ID, username yoki ismini yuboring:", reply_markup=back_admin())

    elif data == "usr_export":
        await _export_users(query, context)

    # ── SOZLAMALAR ───────────────────────────────────────────────────────────
    elif data == "adm_settings":
        fwd  = db.get_setting("forward_block")
        save = db.get_setting("save_block")
        await query.message.edit_text(
            "⚙️ <b>Sozlamalar</b>", parse_mode="HTML",
            reply_markup=admin_settings_keyboard(fwd, save)
        )

    elif data == "set_toggle_forward":
        cur = db.get_setting("forward_block")
        db.set_setting("forward_block", "0" if cur == "1" else "1")
        fwd  = db.get_setting("forward_block")
        save = db.get_setting("save_block")
        await query.message.edit_reply_markup(admin_settings_keyboard(fwd, save))

    elif data == "set_toggle_save":
        cur = db.get_setting("save_block")
        db.set_setting("save_block", "0" if cur == "1" else "1")
        fwd  = db.get_setting("forward_block")
        save = db.get_setting("save_block")
        await query.message.edit_reply_markup(admin_settings_keyboard(fwd, save))

    # ── ADMINLAR ─────────────────────────────────────────────────────────────
    elif data == "adm_admins":
        await query.message.edit_text("👑 <b>Adminlar</b>", parse_mode="HTML",
                                       reply_markup=admin_admins_keyboard())

    elif data == "aadm_add":
        context.user_data["adm_state"] = "aadm_add"
        await query.message.edit_text(
            "👑 <b>Admin qo'shish</b>\n\n"
            "Yangi admin Telegram ID sini yuboring.\n"
            "Keyin rolni tanlang:\n\n"
            "Rollar: <code>super_admin</code>, <code>moderator</code>, <code>content_admin</code>, <code>ads_admin</code>",
            parse_mode="HTML", reply_markup=back_admin()
        )

    elif data == "aadm_list":
        admins = db.get_admins()
        if not admins:
            await query.message.edit_text("👑 Adminlar yo'q.", reply_markup=back_admin())
            return
        text = "👑 <b>Adminlar ro'yxati:</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        kb = []
        for a in admins:
            role_label = ROLES.get(a["role"], a["role"])
            text += f"• <code>{a['user_id']}</code> — {role_label}\n"
            if a["user_id"] != cfg.OWNER_ID:
                kb.append([InlineKeyboardButton(
                    f"🗑 {a['user_id']}", callback_data=f"aadm_del_{a['user_id']}"
                )])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_admins")])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("aadm_del_"):
        uid = int(data.split("_")[-1])
        db.remove_admin(uid)
        await query.message.edit_text(f"✅ Admin <code>{uid}</code> o'chirildi.", parse_mode="HTML",
                                       reply_markup=InlineKeyboardMarkup([[
                                           InlineKeyboardButton("🔙 Adminlar", callback_data="aadm_list")
                                       ]]))

    elif data.startswith("aadm_role_"):
        parts = data.split("_")
        role = parts[2]
        uid  = int(parts[3])
        db.add_admin(uid, role)
        await query.message.edit_text(
            f"✅ Admin qo'shildi!\n🆔 <code>{uid}</code>\n🔐 Rol: {ROLES.get(role, role)}",
            parse_mode="HTML", reply_markup=back_admin()
        )


# ─── ADMIN STATE HANDLER ─────────────────────────────────────────────────────

async def admin_state_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    state = context.user_data.get("adm_state", "")
    if not state:
        return False  # boshqa handler ishlaydi

    msg   = update.message
    text  = msg.text.strip() if msg.text else ""

    # ─── KINO QO'SHISH ────────────────────────────────────────────────────────
    if state == "mov_title":
        context.user_data["new_movie"] = {"title": text, "description": "", "year": "", "genre": "", "category": ""}
        context.user_data["adm_state"] = "mov_desc"
        await msg.reply_text("2️⃣ Tavsif yuboring (yoki /skip):")
        return True

    elif state == "mov_desc":
        if text != "/skip":
            context.user_data["new_movie"]["description"] = text
        context.user_data["adm_state"] = "mov_year"
        await msg.reply_text("3️⃣ Yilni yuboring (yoki /skip):")
        return True

    elif state == "mov_year":
        if text != "/skip":
            context.user_data["new_movie"]["year"] = text
        context.user_data["adm_state"] = "mov_genre"
        await msg.reply_text("4️⃣ Janrni yuboring (yoki /skip):")
        return True

    elif state == "mov_genre":
        if text != "/skip":
            context.user_data["new_movie"]["genre"] = text
        context.user_data["adm_state"] = "mov_category"
        await msg.reply_text("5️⃣ Kategoriyani yuboring (yoki /skip):")
        return True

    elif state == "mov_category":
        if text != "/skip":
            context.user_data["new_movie"]["category"] = text
        context.user_data["adm_state"] = "mov_code"
        await msg.reply_text("6️⃣ Kino kodini kiriting (masalan: <code>001</code>):", parse_mode="HTML")
        return True

    elif state == "mov_code":
        if db.get_movie_by_code(text):
            await msg.reply_text(f"❌ Bu kod mavjud: <code>{text}</code>. Boshqa kod kiriting:", parse_mode="HTML")
            return True
        context.user_data["new_movie"]["code"] = text
        context.user_data["adm_state"] = "mov_file"
        await msg.reply_text("7️⃣ Kino faylini (video yoki dokument) yuboring:")
        return True

    elif state == "mov_file":
        file_id = None
        if msg.video:
            file_id = msg.video.file_id
        elif msg.document:
            file_id = msg.document.file_id
        if not file_id:
            await msg.reply_text("❌ Faqat video yoki dokument yuboring!")
            return True

        movie = context.user_data.pop("new_movie")
        movie["file_id"] = file_id
        context.user_data.pop("adm_state", None)
        db.add_movie(movie)

        # Kanalga post yuborish
        await _post_to_channel(context.bot, movie)

        await msg.reply_text(
            f"✅ <b>Kino qo'shildi!</b>\n"
            f"🎬 {movie['title']}\n"
            f"🆔 Kod: <code>{movie['code']}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 Kinolar ro'yxati", callback_data="mov_list_0")
            ]])
        )
        return True

    # ─── KINO TAHRIRLASH ──────────────────────────────────────────────────────
    elif state.startswith("mfield_"):
        parts   = state.split("_")
        field   = parts[1]
        movie_id = int(parts[2])
        db.update_movie(movie_id, field, text)
        context.user_data.pop("adm_state", None)
        m = db.get_movie_by_id(movie_id)
        await msg.reply_text(
            f"✅ {field} yangilandi!\n🎬 {m['title'] if m else ''}", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Kinoga qaytish", callback_data=f"minfo_{movie_id}")
            ]])
        )
        return True

    # ─── KINO QIDIRISH ────────────────────────────────────────────────────────
    elif state == "mov_search":
        context.user_data.pop("adm_state", None)
        results = db.search_movies(text)
        if not results:
            await msg.reply_text("❌ Natija topilmadi.", reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="adm_movies")
            ]]))
            return True
        kb = [[InlineKeyboardButton(
            f"🎬 {m['title'][:30]} [{m['code']}]", callback_data=f"minfo_{m['id']}"
        )] for m in results]
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_movies")])
        await msg.reply_text(
            f"🔍 <b>{len(results)} ta natija:</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return True

    # ─── KANAL QO'SHISH ───────────────────────────────────────────────────────
    elif state == "ch_add":
        username = text if text.startswith("@") else f"@{text}"
        try:
            chat = await context.bot.get_chat(username)
            db.add_channel(str(chat.id), username, chat.title or username)
            context.user_data.pop("adm_state", None)
            await msg.reply_text(
                f"✅ Kanal qo'shildi!\n📢 {chat.title}\n🔗 {username}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Kanallar", callback_data="ch_list")
                ]])
            )
        except Exception as e:
            await msg.reply_text(
                f"❌ Xatolik: {e}\n\n❗ Bot kanalga admin qilinganmi?"
            )
        return True

    # ─── USER QIDIRISH ────────────────────────────────────────────────────────
    elif state == "usr_search":
        context.user_data.pop("adm_state", None)
        results = db.search_user(text)
        if not results:
            await msg.reply_text("❌ Topilmadi.", reply_markup=back_admin())
            return True
        kb = [[InlineKeyboardButton(
            f"{'🚫' if u['is_banned'] else '✅'} {u['first_name'] or u['user_id']}",
            callback_data=f"uinfo_{u['user_id']}"
        )] for u in results]
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_users")])
        await msg.reply_text(
            f"🔍 <b>{len(results)} ta natija:</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return True

    # ─── BROADCAST ───────────────────────────────────────────────────────────
    elif state.startswith("broadcast_"):
        bc_type = state.split("_")[-1]
        context.user_data.pop("adm_state", None)
        user_ids = db.get_all_user_ids() if bc_type == "all" else db.get_active_user_ids()
        total = len(user_ids)
        status_msg = await msg.reply_text(f"📨 Yuborilmoqda... 0/{total}")
        sent = failed = 0
        for i, uid in enumerate(user_ids):
            try:
                if msg.text:
                    await context.bot.send_message(uid, msg.text, parse_mode="HTML")
                elif msg.photo:
                    await context.bot.send_photo(uid, msg.photo[-1].file_id,
                                                  caption=msg.caption or "", parse_mode="HTML")
                elif msg.video:
                    await context.bot.send_video(uid, msg.video.file_id,
                                                  caption=msg.caption or "", parse_mode="HTML")
                elif msg.document:
                    await context.bot.send_document(uid, msg.document.file_id,
                                                     caption=msg.caption or "", parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
            if (i + 1) % 50 == 0:
                try:
                    await status_msg.edit_text(f"📨 Yuborilmoqda... {i+1}/{total}")
                except Exception:
                    pass
            await asyncio.sleep(0.05)

        await status_msg.edit_text(
            f"✅ <b>Broadcast tugadi!</b>\n\n"
            f"📨 Yuborildi: <b>{sent}</b>\n"
            f"❌ Xato: <b>{failed}</b>\n"
            f"👥 Jami: <b>{total}</b>",
            parse_mode="HTML"
        )
        return True

    # ─── ADMIN QO'SHISH ───────────────────────────────────────────────────────
    elif state == "aadm_add":
        try:
            new_id = int(text.strip())
            context.user_data["aadm_pending_id"] = new_id
            context.user_data["adm_state"] = "aadm_role"
            kb = [[InlineKeyboardButton(label, callback_data=f"aadm_role_{role}_{new_id}")]
                  for role, label in ROLES.items()]
            kb.append([InlineKeyboardButton("🔙 Bekor qilish", callback_data="adm_admins")])
            await msg.reply_text(
                f"👑 ID: <code>{new_id}</code>\n\nRolni tanlang:",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb)
            )
        except ValueError:
            await msg.reply_text("❌ Noto'g'ri ID! Faqat raqam yuboring.")
        return True

    return False


# ─── KANALGA POST ────────────────────────────────────────────────────────────

async def _post_to_channel(bot, movie: dict):
    if not cfg.POST_CHANNEL:
        return
    text = (
        f"🎬 <b>{movie['title']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )
    if movie.get("year"):
        text += f"📅 Yil: {movie['year']}\n"
    if movie.get("genre"):
        text += f"🎭 Janr: {movie['genre']}\n"
    text += f"\n🆔 Kod: <code>{movie['code']}</code>\n🤖 Bot: @{cfg.BOT_USERNAME}"

    deep_link = f"https://t.me/{cfg.BOT_USERNAME}?start={movie['code']}"
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎥 Kinoni olish", url=deep_link)
    ]])
    try:
        await bot.send_message(cfg.POST_CHANNEL, text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        pass  # Kanal sozlanmagan bo'lishi mumkin


# ─── EXPORT USERS ────────────────────────────────────────────────────────────

async def _export_users(query, context):
    users = db.get_all_users_info(limit=10000)
    lines = ["ID,Username,Ism,Til,Ban,Sana"]
    for u in users:
        lines.append(f"{u['user_id']},{u['username']},{u['first_name']},{u['lang']},{u['is_banned']},{u['joined_at']}")
    csv_data = "\n".join(lines).encode("utf-8")
    buf = io.BytesIO(csv_data)
    buf.name = "users.csv"
    await context.bot.send_document(
        query.from_user.id,
        document=buf,
        filename="users.csv",
        caption=f"📥 Jami {len(users)} ta foydalanuvchi"
    )
# -*- coding: utf-8 -*-
"""
Single-file Telegram bot implementing:
... (оставил комментируемую часть без изменений)
"""

import os
import json
import time
import threading
import traceback
import math
from datetime import datetime, timedelta

import telebot
from telebot import types

# ---------------- CONFIG - ORTAMI DEĞİŞKENLERİNDEN OKU ----------------
# --- GÜVENLİK UYARISI: BU DEĞERLERİ DOĞRUDAN KODA YAZMAYIN! ---
# Railway veya yerel ortamınızda bu değişkenleri tanımlayın.
# Bot token'ınızı BotFather'dan alın.
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN ortam değişkeni ayarlanmamış! Lütfen bot token'ınızı tanımlayın.")

# Adminlerin Telegram kullanıcı ID'lerini virgülle ayırarak yazın (örn: "12345,67890").
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',') if admin_id.strip()}

# Veritabanı dosyasının yolu. Railway'de kalıcı depolama için '/data/' dizinini kullanmak önemlidir.
DB_PATH = os.getenv("DB_PATH", "/data/db.json") # Railway için varsayılan
# Eğer yerelde çalıştırıyorsanız ve '/data' dizini yoksa, mevcut dizine kaydeder.
if not os.path.isdir(os.path.dirname(DB_PATH)):
    print(f"Uyarı: '{os.path.dirname(DB_PATH)}' dizini bulunamadı. Veritabanı 'db.json' olarak mevcut dizine kaydedilecek.")
    DB_PATH = "db.json"

# Diğer ayarlar
FREE_TRIAL_DAYS = int(os.getenv("FREE_TRIAL_DAYS", 2))
DAILY_BONUS_STARS = float(os.getenv("DAILY_BONUS_STARS", 1.0))
ADMIN_NOTIFY_COST = float(os.getenv("ADMIN_NOTIFY_COST", 10.0))

# ---------------- BOT INIT ----------------
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ---------------- DEFAULT TEXTS & DB DEFAULTS ----------------
GUIDES_TEXT = (
    "📚 <b>Bot Kanunlary & Maglumat</b>\n\n"
    "1) 🤝 Boty diňe şahsy peýda üçin ulanyň.\n"
    "2) 🛠 Her bir ulanyjy diňe öz hasaby bilen post goýsun.\n"
    "3) 🚫 Spam ýa gadagan mazmunly postlar goýmak gadagan.\n"
    "4) 🏅 Gündelik bonus 24 sagatdan bir gezek alnar.\n"
    "5) 📢 Soraglar üçin: @Muradoff_09\n\n"
    "📘 🤖 BOT GOLLANMA / FAQ\n\n"
    "👋 Hoş geldiňiz! Bu bot size awtomat reklamany goýmak we dolandyrmak üçin döredildi.\n"
    "Aşakdaky maglumatlary üns bilen okaň:\n\n"
    "---\n\n"
    "⏳ 🎁 Free Trial\n\n"
    "✨ Her täze ulanyjy 2 gün mugt Free Trial alýar.\n"
    "✨ Mugt wagtynda islendik kanala post goýup synap bilersiňiz.\n\n"
    "---\n\n"
    "👥 🤝 Dostlaryňy çagyryp bonus al!\n\n"
    "🔗 Siziň aýratyn referal ssylkaňyz bar.\n"
    "👫 Dostlaryňyz ssylka arkaly bota girse, siz ⭐ Star gazanarsyňyz!\n\n"
    "💡 Mysal:\n\n"
    "1 dost = +1⭐\n\n"
    "---\n\n"
    "⭐ 🎯 Stars näme?\n\n"
    "⭐ Stars — bu botuň esasy bonus walýutasy.\n"
    "💱 Siz olary günlere çalyşyp bilersiňiz:\n\n"
    "5⭐ = 1 gün\n11⭐ = 2 gün\n27⭐ = 5 gün\n53⭐ = 10 gün\n130⭐ = 25 gün\n150⭐ = 30 gün\n\n"
    "---\n\n"
    "💎 🤩 VIP Paketler\n\n"
    "💎 3 gün = 5 mnt\n"
    "💎 10 gün = 14 mnt\n"
    "💎 25 gün = 25 mnt\n"
    "💎 30 gün = 30 mnt\n\n"
    "🎁 VIP bilen:\n"
    "✅ Köp kanala post goýup bilersiňiz (6 kanala çenli)\n"
    "✅ Post dolandyryş mümkinçilikleri giňelýär\n"
    "✅ Ýokary aýratyn bot\n\n"
    "📩 Satyn almak üçin: @Muradoff_09 bilen habarlaşyň\n"
)

DEFAULT_DB = {
    "users": {},
    "admins": [str(a) for a in ADMIN_IDS],
    "channels": [],
    "promos": {},
    "referrals": {},
    "scheduled": [],
    "channel_last": {},
    "referral_bonus": {"stars": 1.0, "hours": 0},
    "texts": {
        "welcome": "👋 <b>Hoş geldiňiz!</b>\n\nBaş menýudan birini saýlaň:",
        "guides": GUIDES_TEXT,
        "vip": "<b>💎 VIP Paketler</b>\n\n3 gün = 5 mnt\n10 gün = 14 mnt\n25 gün = 25 mnt\n30 gün = 30 mnt\n\nSatyn almak: @Muradoff_09"
    }
}

# ---------------- DB helpers ----------------
def load_db():
    if not os.path.exists(DB_PATH):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_DB, f, ensure_ascii=False, indent=2)
    with open(DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # ensure defaults & normalize
    for k, v in DEFAULT_DB.items():
        if k not in data:
            data[k] = v
    for a in ADMIN_IDS:
        if str(a) not in data.get("admins", []):
            data.setdefault("admins", []).append(str(a))
    data.setdefault("referral_bonus", DEFAULT_DB["referral_bonus"])
    data.setdefault("texts", DEFAULT_DB["texts"])
    for uid, u in data.get("users", {}).items():
        u.setdefault("temp_stars", [])
        u.setdefault("lang", "tk")
        u.setdefault("posts", [])
        u.setdefault("banned", False)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data

def save_db():
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_db()

def now_iso():
    return datetime.utcnow().isoformat()

def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

def is_admin(uid: int) -> bool:
    return str(uid) in db.get("admins", []) or uid in ADMIN_IDS

def ensure_user(uid: int, username: str = None):
    su = str(uid)
    u = db.get("users", {}).get(su)
    if not u:
        u = {
            "joined_at": now_iso(),
            "username": username or "",
            "ref_by": None,
            "banned": False,
            "stars": 0.0,
            "temp_stars": [],
            "trial_end": (datetime.utcnow() + timedelta(days=FREE_TRIAL_DAYS)).isoformat(),
            "posts": [],
            "last_daily_bonus": None,
            "lang": "tk"
        }
        db.setdefault("users", {})[su] = u
        save_db()
    else:
        changed = False
        if username and u.get("username") != username:
            u["username"] = username; changed = True
        if "temp_stars" not in u:
            u["temp_stars"] = []; changed = True
        if "posts" not in u:
            u["posts"] = []; changed = True
        if "lang" not in u:
            u["lang"] = "tk"; changed = True
        if changed:
            save_db()
    return db["users"][su]

def find_user_by_username(username: str):
    if not username:
        return None
    uname = username.lstrip("@").lower()
    for uid_str, u in db.get("users", {}).items():
        if (u.get("username") or "").lstrip("@").lower() == uname:
            return uid_str
    return None

def check_subs(uid: int) -> bool:
    chans = db.get("channels", [])
    if not chans:
        return True
    for ch in chans:
        try:
            member = bot.get_chat_member(ch, uid)
            if member.status in ("left", "kicked"):
                return False
        except Exception:
            return False
    return True

# ---------------- Utility send/edit wrappers ----------------
def sendf(chat_id, text, **kwargs):
    try:
        return bot.send_message(chat_id, text, parse_mode="HTML", **kwargs)
    except Exception:
        try:
            return bot.send_message(chat_id, text, **kwargs)
        except Exception as e:
            print("sendf fail:", e)
            return None

def editf(chat_id, message_id, text, **kwargs):
    try:
        return bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="HTML", **kwargs)
    except Exception:
        try:
            return bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, **kwargs)
        except Exception as e:
            print("editf fail:", e)
            return None

# ---------------- Stars handling ----------------
def cleanup_temp_stars_for_user(u: dict):
    now = datetime.utcnow()
    new_temp = []
    for ent in u.get("temp_stars", []):
        exp = parse_iso(ent.get("expires_at"))
        if exp and exp > now:
            new_temp.append(ent)
    if len(new_temp) != len(u.get("temp_stars", [])):
        u["temp_stars"] = new_temp

def get_user_star_details(uid: int):
    u = db.get("users", {}).get(str(uid))
    if not u:
        return (0.0, 0.0, 0.0)
    cleanup_temp_stars_for_user(u)
    persistent = float(u.get("stars", 0.0))
    temp_total = sum(float(x.get("amount", 0.0)) for x in u.get("temp_stars", []))
    total = round(persistent + temp_total, 2)
    return (round(persistent, 2), round(temp_total, 2), total)

def deduct_stars(uid: int, amount: float) -> bool:
    if amount <= 0:
        return True
    u = db.get("users", {}).get(str(uid))
    if not u:
        return False
    cleanup_temp_stars_for_user(u)
    persistent = float(u.get("stars", 0.0))
    temp_list = sorted(u.get("temp_stars", []), key=lambda x: parse_iso(x.get("expires_at")) or datetime.max)
    total_available = persistent + sum(float(x.get("amount", 0.0)) for x in temp_list)
    if total_available + 1e-9 < amount:
        return False
    remaining = amount
    if persistent >= remaining:
        u["stars"] = round(persistent - remaining, 2)
        save_db()
        return True
    else:
        remaining -= persistent
        u["stars"] = 0.0
    new_temp = []
    for ent in temp_list:
        amt = float(ent.get("amount", 0.0))
        if remaining <= 0:
            new_temp.append(ent)
            continue
        if amt > remaining:
            ent["amount"] = round(amt - remaining, 2)
            remaining = 0
            new_temp.append(ent)
        else:
            remaining -= amt
    u["temp_stars"] = new_temp
    save_db()
    return True

# ---------------- Translations & Keyboards ----------------
TRANSLATIONS = {
    "tk": {
        "post": "📮 Post",
        "my_posts": "📁 Postlarym",
        "profile": "👤 Profil",
        "promocode": "🎁 Promocode giriz",
        "top_ref": "👥 Top Referral",
        "guides_btn": "Guides / FAQ",
        "star_exchange": "⭐ Günler bn obmen",
        "vip": "💎 VIP Paketler",
        "daily_bonus": "🎁 Her Günki Bonus",
        "admin_panel": "🛠 Admin paneli",
        "language": "🌐 Dil",
        "lang_tk": "Türkmençe",
        "lang_ru": "Русский",
        "admin_notify": "Admine habar ugrat 📣",
    },
    "ru": {
        "post": "📮 Пост",
        "my_posts": "📁 Мои посты",
        "profile": "👤 Профиль",
        "promocode": "🎁 Ввести промокод",
        "top_ref": "👥 Топ Рефералов",
        "guides_btn": "Guides / FAQ",
        "star_exchange": "⭐ Обмен на дни",
        "vip": "💎 VIP Пакеты",
        "daily_bonus": "🎁 Ежедневный бонус",
        "admin_panel": "🛠 Панель админа",
        "language": "🌐 Язык",
        "lang_tk": "Türkmençe",
        "lang_ru": "Русский",
        "admin_notify": "Отправить админу 📣",
    }
}

def get_user_lang(uid: int) -> str:
    u = db.get("users", {}).get(str(uid))
    return u.get("lang", "tk") if u else "tk"

def t(uid: int, key: str) -> str:
    lang = get_user_lang(uid)
    return TRANSLATIONS.get(lang, TRANSLATIONS["tk"]).get(key, key)

def main_menu_keyboard(uid: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(t(uid, "post"), t(uid, "my_posts"))
    kb.row(t(uid, "profile"), t(uid, "promocode"))
    kb.row(t(uid, "top_ref"), t(uid, "star_exchange"))
    kb.row(t(uid, "vip"), t(uid, "daily_bonus"))
    kb.row("Guides / FAQ")  # exact label required
    kb.row(t(uid, "admin_notify"), t(uid, "language"))
    if is_admin(uid):
        kb.row(t(uid, "admin_panel"))
    return kb

def admin_menu_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 Statistika", "📡 Kanallar")
    kb.row("➕ Kanal goş", "➖ Kanal aýyr")
    kb.row("➕ Admin goş", "➖ Admin aýyr")
    kb.row("🎯 Promo döret", "📃 Promo sanaw")
    kb.row("🚫 Ulanyjy Ban", "✅ Ulanyjy Unban")
    kb.row("⭐ Referal bonus", "📢 Broadcast")
    kb.row("✏️ Yazgy Uytget", "Star doldur")
    kb.row("⬅️ Yza")
    return kb

def language_inline_keyboard(uid: int):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(TRANSLATIONS[get_user_lang(uid)]["lang_tk"], callback_data="set_lang_tk"))
    kb.add(types.InlineKeyboardButton(TRANSLATIONS[get_user_lang(uid)]["lang_ru"], callback_data="set_lang_ru"))
    return kb

def star_exchange_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("5 ⭐ = 1 gün", callback_data="buy_1day"))
    kb.add(types.InlineKeyboardButton("11 ⭐ = 2 gün", callback_data="buy_2day"))
    kb.add(types.InlineKeyboardButton("27 ⭐ = 5 gün", callback_data="buy_5day"))
    kb.add(types.InlineKeyboardButton("53 ⭐ = 10 gün", callback_data="buy_10day"))
    kb.add(types.InlineKeyboardButton("130 ⭐ = 25 gün", callback_data="buy_25day"))
    kb.add(types.InlineKeyboardButton("150 ⭐ = 30 gün", callback_data="buy_30day"))
    return kb

# ---------------- Ban guard ----------------
BAN_MESSAGE = "❌ Siziň hasabyňyz ban edildi."

def banned_guard(uid: int, chat_id: int) -> bool:
    u = db.get("users", {}).get(str(uid))
    if u and u.get("banned"):
        try:
            sendf(chat_id, BAN_MESSAGE)
        except Exception:
            pass
        return True
    return False

# ---------------- Scheduler ----------------
sched_lock = threading.Lock()

def delete_channel_last_if_matches(channel, post_id):
    cl = db.get("channel_last", {})
    info = cl.get(channel)
    if info and info.get("post_id") == post_id:
        try:
            bot.delete_message(channel, info.get("message_id"))
        except Exception:
            pass
        cl.pop(channel, None)
        db["channel_last"] = cl
        save_db()

def scheduler_loop():
    while True:
        try:
            now_ts = time.time()
            with sched_lock:
                for post in list(db.get("scheduled", [])):
                    if post.get("paused"):
                        continue
                    owner = str(post.get("owner"))
                    owner_data = db.get("users", {}).get(owner)
                    if not owner_data:
                        try:
                            db["scheduled"].remove(post)
                            save_db()
                        except Exception:
                            pass
                        continue
                    if owner_data.get("banned"):
                        delete_channel_last_if_matches(post["channel"], post["id"])
                        try:
                            db["scheduled"].remove(post)
                            save_db()
                        except Exception:
                            pass
                        continue
                    trial_end = parse_iso(owner_data.get("trial_end"))
                    if trial_end and datetime.utcnow() > trial_end and not is_admin(int(owner)):
                        delete_channel_last_if_matches(post["channel"], post["id"])
                        try:
                            db["scheduled"].remove(post)
                            save_db()
                        except Exception:
                            pass
                        try:
                            sendf(int(owner), "⏳ Siziň free trial wagtyňyz gutardy — şol post awtomatiki pozuldy.")
                        except Exception:
                            pass
                        continue
                    if now_ts >= post.get("next_time", 0):
                        try:
                            prev = db.get("channel_last", {}).get(post["channel"])
                            if prev:
                                try:
                                    bot.delete_message(post["channel"], prev.get("message_id"))
                                except Exception:
                                    pass
                            if post["type"] == "photo":
                                msg = bot.send_photo(post["channel"], post["photo"], caption=post.get("caption",""), parse_mode="HTML")
                            else:
                                msg = bot.send_message(post["channel"], post.get("text",""), parse_mode="HTML")
                            db.setdefault("channel_last", {})[post["channel"]] = {"post_id": post["id"], "message_id": msg.message_id}
                            post["last_message_id"] = msg.message_id
                            post["next_time"] = now_ts + int(post.get("minute", 60)) * 60
                            save_db()
                        except Exception as e:
                            try:
                                post["paused"] = True
                                save_db()
                                sendf(int(post["owner"]), f"⚠️ Post kanalga ugradylmady: {e}. Post pauza edildi.")
                            except Exception:
                                pass
            time.sleep(5)
        except Exception as e:
            print("Scheduler exception:", e)
            traceback.print_exc()
            time.sleep(5)

threading.Thread(target=scheduler_loop, daemon=True).start()

# ---------------- State holders ----------------
user_states = {}  # ephemeral per-user posting/admin flows
admin_states = {}


# ---------------- Callback handlers ----------------

# Post callbacks (delete / toggle) - MOVED HERE TO FIX HANDLER ORDER
@bot.callback_query_handler(func=lambda c: c.data and (c.data.startswith("delete_") or c.data.startswith("toggle_")))
def post_item_callbacks(c: types.CallbackQuery):
    uid = c.from_user.id
    if banned_guard(uid, uid):
        try: bot.answer_callback_query(c.id, "🚫")
        except: pass
        return
    data = c.data
    if data.startswith("delete_"):
        pid = data.split("delete_", 1)[1]
        p = next((x for x in db.get("scheduled", []) if x.get("id") == pid), None)
        if not p:
            bot.answer_callback_query(c.id, "⚠️ Post tapylmady."); return
        if str(p.get("owner")) != str(uid) and not is_admin(uid):
            bot.answer_callback_query(c.id, "⚠️ Rugsat ýok."); return
        delete_channel_last_if_matches(p["channel"], p["id"])
        try: db["scheduled"].remove(p)
        except: pass
        owner = p.get("owner")
        urec = db.get("users", {}).get(str(owner))
        if urec and pid in urec.get("posts", []):
            urec["posts"].remove(pid)
        save_db()
        bot.answer_callback_query(c.id, "✅ Post pozuldy")
        try: editf(c.message.chat.id, c.message.message_id, "✅ Post pozuldy")
        except Exception:
            pass
        try: sendf(int(owner), "✅ Siziň postiňiz pozuldy")
        except Exception:
            pass
        return
    if data.startswith("toggle_"):
        pid = data.split("toggle_", 1)[1]
        p = next((x for x in db.get("scheduled", []) if x.get("id") == pid), None)
        if not p:
            bot.answer_callback_query(c.id, "⚠️ Post tapylmady."); return
        if str(p.get("owner")) != str(uid) and not is_admin(uid):
            bot.answer_callback_query(c.id, "⚠️ Rugsat ýok."); return
        p["paused"] = not bool(p.get("paused"))
        save_db()
        bot.answer_callback_query(c.id, "⏸ Duruz edildi" if p["paused"] else "▶ Dowam etdi")
        try: editf(c.message.chat.id, c.message.message_id, "⏸ Duruz edildi" if p["paused"] else "▶ Dowam etdi")
        except: pass
        return

# General callback handler
@bot.callback_query_handler(func=lambda c: True)
def handle_callback(c: types.CallbackQuery):
    uid = c.from_user.id
    if banned_guard(uid, uid):
        try:
            bot.answer_callback_query(c.id, "🚫")
        except Exception:
            pass
        return
    data = c.data or ""

    if data == "check_subs":
        if check_subs(uid):
            bot.answer_callback_query(c.id, "✅ Agza bolundyňyz!")
            try: editf(c.message.chat.id, c.message.message_id, "✅ Barlandy")
            except: pass
            sendf(uid, db.get("texts", {}).get("welcome"), reply_markup=main_menu_keyboard(uid))
        else:
            bot.answer_callback_query(c.id, "❌ Entäk käbir kanala goşulmadyňyz.")
        return

    if data == "set_lang_tk":
        ensure_user(uid)
        db["users"][str(uid)]["lang"] = "tk"; save_db()
        bot.answer_callback_query(c.id, "✅ Dil: Türkmençe")
        sendf(uid, db.get("texts", {}).get("welcome"), reply_markup=main_menu_keyboard(uid))
        return

    if data == "set_lang_ru":
        ensure_user(uid)
        db["users"][str(uid)]["lang"] = "ru"; save_db()
        bot.answer_callback_query(c.id, "✅ Язык: Русский")
        sendf(uid, db.get("texts", {}).get("welcome"), reply_markup=main_menu_keyboard(uid))
        return

    if data.startswith("buy_"):
        mapping = {"buy_1day": (5, 1), "buy_2day": (11, 2), "buy_5day": (27, 5), "buy_10day": (53, 10), "buy_25day": (130, 25), "buy_30day": (150, 30)}
        item = mapping.get(data)
        if item:
            cost, days = item
            _, _, total = get_user_star_details(uid)
            if total < cost:
                bot.answer_callback_query(c.id, "⚠️ Ýeterlik ⭐ ýok.")
                return
            ok = deduct_stars(uid, cost)
            if not ok:
                bot.answer_callback_query(c.id, "⚠️ Deduction başarısız.")
                return
            u = ensure_user(uid)
            cur_end = parse_iso(u.get("trial_end"))
            start_from = max(cur_end, datetime.utcnow()) if cur_end else datetime.utcnow()
            u["trial_end"] = (start_from + timedelta(days=days)).isoformat(); save_db()
            bot.answer_callback_query(c.id, f"✅ Siz {days} gün satyn aldyňyz.")
            sendf(uid, "✅ Ugradyldy.", reply_markup=main_menu_keyboard(uid))
        return

    # ---------- Admin notify callbacks ----------
    if data == "admin_notify_buy":
        # Enter awaiting_admin_msg state and prompt user to send message
        ensure_user(uid)
        # we don't deduct yet — do deduction at send time to allow media/text
        user_states[uid] = {"awaiting_admin_msg": True}
        try: bot.answer_callback_query(c.id, "✉️ Habарыñyzy ugradyň.")
        except: pass
        sendf(uid, "📨 <b>Habary tekst ýa-da surat görnüşinde ugradyň.</b>\n\n🌟 <i>Administratorlara habar ugratmak üçin 10 ⭐ talap edilýär. Habary ugradanyňyzda 10 ⭐ awtomatiki tutulýar.</i>", reply_markup=types.ReplyKeyboardRemove())
        return

    if data == "admin_notify_back":
        try: bot.answer_callback_query(c.id, "◀️ Yza")
        except: pass
        sendf(uid, db.get("texts", {}).get("welcome"), reply_markup=main_menu_keyboard(uid))
        return

    bot.answer_callback_query(c.id, "ℹ️ Eskidi ýa-da näbelli düwme.")

# ---------------- Message handlers ----------------
@bot.message_handler(commands=["start"])
def cmd_start(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid): return
    username = m.from_user.username or (m.from_user.first_name or "")
    ensure_user(uid, username)

    parts = (m.text or "").split(maxsplit=1)
    ref = parts[1].strip() if len(parts) == 2 else None
    if ref and ref.isdigit() and ref != str(uid):
        inviter = str(ref)
        if db["users"].get(str(uid), {}).get("ref_by") is None:
            db["users"][str(uid)]["ref_by"] = int(inviter)
            lst = db.get("referrals", {}).get(inviter, [])
            if str(uid) not in lst:
                lst.append(str(uid))
            db.setdefault("referrals", {})[inviter] = lst
            if inviter not in db["users"]:
                db["users"][inviter] = {
                    "joined_at": now_iso(),
                    "username": "",
                    "ref_by": None,
                    "banned": False,
                    "stars": 0.0,
                    "temp_stars": [],
                    "trial_end": (datetime.utcnow() + timedelta(days=FREE_TRIAL_DAYS)).isoformat(),
                    "posts": [],
                    "last_daily_bonus": None,
                    "lang": "tk"
                }
            rb = db.get("referral_bonus", {"stars": 1.0, "hours": 0})
            add_stars = float(rb.get("stars", 1.0)); add_hours = int(rb.get("hours", 0))
            inv_user = db["users"][inviter]
            if add_hours > 0:
                expires_at = (datetime.utcnow() + timedelta(hours=add_hours)).isoformat()
                inv_user.setdefault("temp_stars", []).append({"amount": add_stars, "expires_at": expires_at})
                cur_end = parse_iso(inv_user.get("trial_end"))
                start_from = max(cur_end, datetime.utcnow()) if cur_end else datetime.utcnow()
                inv_user["trial_end"] = (start_from + timedelta(hours=add_hours)).isoformat()
            else:
                inv_user["stars"] = round(inv_user.get("stars", 0.0) + add_stars, 2)
            save_db()
            try:
                sendf(int(inviter), f"🎉 Referral: +{add_stars:.0f} ⭐, +{add_hours} sagat trial!")
            except Exception:
                pass

    if not check_subs(uid):
        kb = types.InlineKeyboardMarkup()
        for ch in db.get("channels", []):
            kb.add(types.InlineKeyboardButton(ch, url=f"https://t.me/{ch.replace('@','')}"))
        kb.add(types.InlineKeyboardButton("✅ Barlandy", callback_data="check_subs"))
        sendf(uid, "📢 Hoş geldiňiz! Boty doly ulanmak üçin aşakdaky kanallara goşulyň we \"✅ Barlandy\" düwmesine basyň:", reply_markup=kb)
        return

    sendf(uid, db.get("texts", {}).get("welcome"), reply_markup=main_menu_keyboard(uid))

# Language menu
@bot.message_handler(func=lambda m: (m.text or "") in ("🌐 Dil", "🌐 Язык"))
def cmd_language(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid):
        return
    sendf(uid, "🌐 Dil saýlaň / Выберите язык", reply_markup=language_inline_keyboard(uid))

# Profile
@bot.message_handler(func=lambda m: (m.text or "") in (TRANSLATIONS["tk"]["profile"], TRANSLATIONS["ru"]["profile"]))
def cmd_profile(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid):
        return
    u = ensure_user(uid, m.from_user.username or m.from_user.first_name)
    persistent, temp_total, total = get_user_star_details(uid)
    invited = len(db.get("referrals", {}).get(str(uid), []))
    trial_end = parse_iso(u.get("trial_end"))
    days_left = 0
    if trial_end:
        delta = trial_end - datetime.utcnow()
        secs = max(delta.total_seconds(), 0)
        days_left = math.ceil(secs / 86400) if secs > 0 else 0
    last_bonus = u.get("last_daily_bonus") or "—"
    txt = (f"👤 <b>Profil</b>\n\n"
           f"ID: <code>{uid}</code>\n"
           f"📛 Ulanyjy: @{u.get('username','')}\n"
           f"🚫 Ban: {'Hawa' if u.get('banned') else 'Ýok'}\n"
           f"👥 Referral: {invited}\n"
           f"⭐ Stars: {total:.2f} (🔒 {persistent:.2f} + ⏳ {temp_total:.2f})\n"
           f"🕒 Free trial galan: {days_left} gün\n"
           f"🎁 Soňky günlik bonus: {last_bonus}\n\n"
           f"🔗 Referal link: <code>https://t.me/{bot.get_me().username}?start={uid}</code>")
    sendf(uid, txt)

# Promocode
@bot.message_handler(func=lambda m: (m.text or "") in (TRANSLATIONS["tk"]["promocode"], TRANSLATIONS["ru"]["promocode"]))
def cmd_promocode(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid):
        return
    msg = sendf(uid, "🎯 Promocode giriziň (mysal: NEW12):")
    bot.register_next_step_handler(msg, handle_promocode_entry)

def handle_promocode_entry(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid):
        return
    code = (m.text or "").strip().upper()
    if not code:
        sendf(uid, "⚠️ Boş."); return
    promo = db.get("promos", {}).get(code)
    if not promo:
        sendf(uid, "❌ Ýalňyş ýa gutardy."); return
    if promo.get("limit") is not None and promo.get("used", 0) >= promo.get("limit", 0):
        sendf(uid, "❌ Bu kod üçin limit gutardy."); return
    promo["used"] = promo.get("used", 0) + 1
    add = float(promo.get("stars", 1.0))
    ensure_user(uid)
    db["users"][str(uid)]["stars"] = round(db["users"][str(uid)].get("stars", 0.0) + add, 2)
    save_db()
    sendf(uid, f"✅ +{add} ⭐ goşuldy! 🎉")

# Top referral
@bot.message_handler(func=lambda m: (m.text or "") in (TRANSLATIONS["tk"]["top_ref"], TRANSLATIONS["ru"]["top_ref"]))
def cmd_top_ref(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid):
        return
    items = [(inv, len(lst)) for inv, lst in db.get("referrals", {}).items()]
    if not items:
        sendf(uid, "ℹ️ Entäk referral ýok."); return
    items.sort(key=lambda x: x[1], reverse=True)
    txt = "<b>🏆 Iň köp çagyranlar:</b>\n\n"
    for i, (inv, cnt) in enumerate(items[:10], start=1):
        usr = db.get("users", {}).get(inv, {})
        uname = f"@{usr.get('username')}" if usr.get('username') else inv
        txt += f"{i}. {uname} — {cnt} 👥\n"
    sendf(uid, txt)

# Star exchange
@bot.message_handler(func=lambda m: (m.text or "") in (TRANSLATIONS["tk"]["star_exchange"], TRANSLATIONS["ru"]["star_exchange"]))
def cmd_star_exchange(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid):
        return
    _, _, total = get_user_star_details(uid)
    sendf(uid, f"🎯 Siziň staryňyz: <b>{total:.2f}</b> ⭐\nAşakdaky bahalardan birini saýlaň:", reply_markup=star_exchange_keyboard())

# Daily bonus
@bot.message_handler(func=lambda m: (m.text or "") in (TRANSLATIONS["tk"]["daily_bonus"], TRANSLATIONS["ru"]["daily_bonus"]))
def cmd_daily(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid):
        return
    u = ensure_user(uid, m.from_user.username or m.from_user.first_name)
    now = datetime.utcnow(); last = parse_iso(u.get("last_daily_bonus"))
    if last and (now - last) < timedelta(hours=24):
        re = timedelta(hours=24) - (now - last)
        sendf(uid, f"⏳ {re.seconds//3600} sagat { (re.seconds%3600)//60 } minut galýar."); return
    u["stars"] = round(u.get("stars", 0.0) + DAILY_BONUS_STARS, 2); u["last_daily_bonus"] = now.isoformat(); save_db()
    sendf(uid, f"🎉 +{DAILY_BONUS_STARS:.2f} ⭐ aldyňyz!")

# VIP
@bot.message_handler(func=lambda m: (m.text or "") in (TRANSLATIONS["tk"]["vip"], TRANSLATIONS["ru"]["vip"]))
def cmd_vip(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid):
        return
    sendf(uid, db.get("texts", {}).get("vip"))

# Guides / FAQ (exact)
@bot.message_handler(func=lambda m: (m.text or "") == "Guides / FAQ")
def cmd_guides(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid):
        return
    sendf(uid, db.get("texts", {}).get("guides"), reply_markup=main_menu_keyboard(uid))

# ---------------- NEW: Handler for reply-keyboard Admin Notify ----------------
@bot.message_handler(func=lambda m: (m.text or "") in (TRANSLATIONS["tk"]["admin_notify"], TRANSLATIONS["ru"]["admin_notify"]))
def cmd_admin_notify(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid): return
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Admine habar ugratmak ucin 10 yyldyz gerek ⭐", callback_data="admin_notify_buy"))
    kb.add(types.InlineKeyboardButton("Yza ◀️", callback_data="admin_notify_back"))
    sendf(uid, "📨 <b>Admine habar ugratmak — saýlaň:</b>\n\n❗ Habary ugratmak üçin 10 ⭐ gerek. Habary ugradanyňyzda 10 ⭐ tutulýar.", reply_markup=kb)

# ---------------- Posting flow ----------------
@bot.message_handler(func=lambda m: (m.text or "") in (TRANSLATIONS["tk"]["post"], TRANSLATIONS["ru"]["post"]))
def cmd_post(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid): return
    u = ensure_user(uid, m.from_user.username or m.from_user.first_name)
    end = parse_iso(u.get("trial_end"))
    if end and datetime.utcnow() > end and not is_admin(uid):
        sendf(uid, "⏳ Free trial gutardy. ⭐ bilen gün alyň ýa-da promo ulanyň."); return
    if not is_admin(uid) and len(u.get("posts", [])) >= 3:
        sendf(uid, "⚠️ Maks: 3 post."); return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("✏ Tekst", "🖼 Surat")
    kb.row("⬅️ Yza")
    msg = sendf(uid, "📤 Post görnüşini saýlaň:", reply_markup=kb)
    bot.register_next_step_handler(msg, post_choose_type)

def post_choose_type(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid): return
    txt = (m.text or "").strip()
    if txt == "⬅️ Yza": sendf(uid, "⬅️ Baş menýu", reply_markup=main_menu_keyboard(uid)); return
    if txt not in ("✏ Tekst", "🖼 Surat"): sendf(uid, "⚠️ Saýlaň."); return
    user_states[uid] = {"type": "text" if txt == "✏ Tekst" else "photo"}
    if user_states[uid]["type"] == "text":
        msg = sendf(uid, "✍ Teksti giriziň:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, post_receive_text)
    else:
        msg = sendf(uid, "📎 Surat iberiň:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, post_receive_photo)

def post_receive_text(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid): return
    user_states.get(uid, {})["text"] = m.text or ""
    msg = sendf(uid, "🕒 Minut giriziň (mysal: 5):")
    bot.register_next_step_handler(msg, post_receive_minute)

def post_receive_photo(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid): return
    if not m.photo: sendf(uid, "⚠️ Surat tapylmady."); return
    user_states.get(uid, {})["photo"] = m.photo[-1].file_id
    msg = sendf(uid, "✍ Caption (opsional):")
    bot.register_next_step_handler(msg, post_receive_caption)

def post_receive_caption(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid): return
    user_states.get(uid, {})["caption"] = m.text or ""
    msg = sendf(uid, "🕒 Minut giriziň (mysal: 5):")
    bot.register_next_step_handler(msg, post_receive_minute)

def post_receive_minute(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid): return
    try:
        minute = int((m.text or "").strip()); assert minute > 0
    except Exception:
        sendf(uid, "⚠️ San giriziň."); return
    user_states.get(uid, {})["minute"] = minute
    msg = sendf(uid, "📢 Kanal: @username ýa-da ID giriziň:")
    bot.register_next_step_handler(msg, post_receive_channel)

def post_receive_channel(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid): return
    channel = (m.text or "").strip()
    if not channel:
        sendf(uid, "⚠️ Kanal boş."); user_states.pop(uid, None); return
    # check user is admin of the channel
    try:
        member = bot.get_chat_member(channel, uid)
        if member.status not in ("administrator", "creator"):
            sendf(uid, "⚠️ Siz şu kanalda admin dälsiňiz. Kanalyň admini bolup ýada admin statusy alyň we soňra gaýtadan synanyşyň.")
            user_states.pop(uid, None)
            return
    except Exception:
        sendf(uid, "⚠️ Kanal barlanmady ýa-da nädogry ad. Iňlis: @channel şeklinde dogry giriziň."); user_states.pop(uid, None)
        return
    # check bot is admin
    try:
        me = bot.get_me(); bmem = bot.get_chat_member(channel, me.id)
        if bmem.status not in ("administrator", "creator"):
            sendf(uid, "⚠️ Meni kanala admin ediň, soň gaýtadan synanyşyň."); user_states.pop(uid, None); return
    except Exception:
        sendf(uid, "⚠️ Kanal barlanmady. Boty admin ediň."); user_states.pop(uid, None); return

    st = user_states.pop(uid)
    post = {
        "id": str(int(time.time()*1000)),
        "owner": str(uid),
        "type": st["type"],
        "channel": channel,
        "minute": int(st["minute"]),
        "next_time": time.time() + int(st["minute"]) * 60,
        "paused": False,
        "created_at": now_iso()
    }
    if st["type"] == "text":
        post["text"] = st.get("text", "")
    else:
        post["photo"] = st.get("photo"); post["caption"] = st.get("caption", "")
    u = ensure_user(uid, m.from_user.username or m.from_user.first_name)
    u.setdefault("posts", []).append(post["id"]); db.setdefault("scheduled", []).append(post); save_db()
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("❌ Poz", callback_data=f"delete_{post['id']}"))
    kb.add(types.InlineKeyboardButton("⏸ Duruz / ▶ Dowam et", callback_data=f"toggle_{post['id']}"))
    sendf(uid, f"✅ Post döredildi — ID: <code>{post['id']}</code>\n⏱ Her {post['minute']} minutda gaýtalanar.", reply_markup=kb)

# My posts
@bot.message_handler(func=lambda m: (m.text or "") in (TRANSLATIONS["tk"]["my_posts"], TRANSLATIONS["ru"]["my_posts"]))
def cmd_my_posts(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, uid): return
    u = ensure_user(uid, m.from_user.username or m.from_user.first_name)
    posts_ids = u.get("posts", [])
    if not posts_ids:
        sendf(uid, "📭 Post ýok.", reply_markup=main_menu_keyboard(uid)); return
    sendf(uid, "📂 <b>Siziň postlaryňyz:</b>")
    for pid in posts_ids:
        p = next((x for x in db.get("scheduled", []) if x.get("id") == pid), None)
        if p:
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("❌ Poz", callback_data=f"delete_{p['id']}"))
            kb.add(types.InlineKeyboardButton("⏸ Duruz" if not p.get("paused") else "▶ Dowam et", callback_data=f"toggle_{p['id']}"))
            sendf(uid, f"• <code>{p['id']}</code> — kanal: {p['channel']} — minut: {p['minute']} — created: {p['created_at']}", reply_markup=kb)
        else:
            sendf(uid, f"• <code>{pid}</code> — (pozulan)")
    sendf(uid, "🔙 Baş menýu", reply_markup=main_menu_keyboard(uid))

# ---------------- Admin panel handlers ----------------
@bot.message_handler(func=lambda m: (m.text or "") in (TRANSLATIONS["tk"]["admin_panel"], TRANSLATIONS["ru"]["admin_panel"]))
def admin_panel(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, m.chat.id): return
    if not is_admin(uid): return
    sendf(m.chat.id, "🛠 <b>Admin paneli</b> — bölüm saýlaň:", reply_markup=admin_menu_keyboard())

# === Statistika handler ===
@bot.message_handler(func=lambda m: (m.text or "") == "📊 Statistika")
def admin_statistics(m: types.Message):
    uid = m.from_user.id
    if banned_guard(uid, m.chat.id): return
    if not is_admin(uid):
        return
    try:
        total_users = len(db.get("users", {}))
        total_admins = len(db.get("admins", []))
        total_channels = len(db.get("channels", []))
        scheduled = db.get("scheduled", [])
        total_scheduled = len(scheduled)
        active = sum(1 for p in scheduled if not p.get("paused"))
        paused = total_scheduled - active

        # posts per channel
        per_channel = {}
        for p in scheduled:
            ch = p.get("channel")
            per_channel[ch] = per_channel.get(ch, 0) + 1

        if per_channel:
            channels_text = ""
            for ch, cnt in sorted(per_channel.items(), key=lambda x: (-x[1], x[0])):
                channels_text += f"{ch} — {cnt} post\n"
        else:
            channels_text = "Entäk post ýok kanallarda."

        # configured but unused channels
        configured = db.get("channels", [])
        unused = [ch for ch in configured if ch not in per_channel]
        unused_text = ""
        if unused:
            unused_text = "\n\n📡 Konfigirlenen kanallar (post ýok):\n" + "\n".join(unused)

        # top posting users
        user_post_counts = []
        for uid_str, u in db.get("users", {}).items():
            user_post_counts.append((uid_str, len(u.get("posts", []))))
        user_post_counts.sort(key=lambda x: x[1], reverse=True)
        top = ""
        for i, (uid_s, cnt) in enumerate(user_post_counts[:10], 1):
            usr = db.get("users", {}).get(uid_s, {})
            uname = usr.get("username") or uid_s
            top += f"{i}. @{uname} — {cnt} post\n"
        if not top:
            top = "Entäk top poster ýok."

        text = (f"📊 <b>Statistika</b>\n\n"
                f"👥 Ulanyjylar: <b>{total_users}</b>\n"
                f"🛡 Adminlar: <b>{total_admins}</b>\n"
                f"📡 Konfigirlenen kanallar: <b>{total_channels}</b>\n"
                f"🗂 Jemi postlar: <b>{total_scheduled}</b> (Active: <b>{active}</b>, Paused: <b>{paused}</b>)\n\n"
                f"📌 Post sanawy by kanal:\n{channels_text}"
                f"{unused_text}\n\n"
                f"🏆 Iň köp post goýýan ulanyjylar:\n{top}\n")
        sendf(m.chat.id, text, reply_markup=admin_menu_keyboard())
    except Exception as e:
        sendf(m.chat.id, f"⚠️ Statistika alnylanda hata: {e}", reply_markup=admin_menu_keyboard())

# Channels management
@bot.message_handler(func=lambda m: (m.text or "") == "📡 Kanallar")
def admin_channels(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    chans = db.get("channels", [])
    txt = "<b>📡 Kanallar:</b>\n\n" + ("\n".join(chans) if chans else "Entäk kanal ýok.")
    sendf(m.chat.id, txt, reply_markup=admin_menu_keyboard())

@bot.message_handler(func=lambda m: (m.text or "") == "➕ Kanal goş")
def admin_channel_add_prompt(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    msg = sendf(m.chat.id, "📎 Kanal adyny giriziň (mysal: @kanaly):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_channel_add_step)

def admin_channel_add_step(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    ch = (m.text or "").strip()
    if not ch:
        sendf(m.chat.id, "⚠️ Kanal boş"); return
    if ch not in db.get("channels", []):
        db.setdefault("channels", []).append(ch); save_db()
        sendf(m.chat.id, f"✅ Kanal goşuldy: {ch}", reply_markup=admin_menu_keyboard())
    else:
        sendf(m.chat.id, "ℹ️ Bu kanal eýýäm bar.", reply_markup=admin_menu_keyboard())

@bot.message_handler(func=lambda m: (m.text or "") == "➖ Kanal aýyr")
def admin_channel_remove_prompt(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    msg = sendf(m.chat.id, "❌ Pozmak isleýän kanalyň adyny giriziň:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_channel_remove_step)

def admin_channel_remove_step(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    ch = (m.text or "").strip()
    if ch in db.get("channels", []):
        db["channels"].remove(ch); save_db()
        sendf(m.chat.id, f"✅ Kanal pozuldy: {ch}", reply_markup=admin_menu_keyboard())
    else:
        sendf(m.chat.id, "⚠️ Munuň ýaly kanal tapylmady.", reply_markup=admin_menu_keyboard())

# Admin add/remove
@bot.message_handler(func=lambda m: (m.text or "") == "➕ Admin goş")
def admin_add_prompt(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    msg = sendf(m.chat.id, "➕ Admin ID-ni giriziň:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_add_step)

def admin_add_step(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    try: aid = int((m.text or "").strip())
    except:
        sendf(m.chat.id, "⚠️ ID sany bolmaly."); return
    if str(aid) not in db.get("admins", []):
        db.setdefault("admins", []).append(str(aid)); save_db()
        sendf(m.chat.id, f"✅ Admin goşuldy: <code>{aid}</code>", reply_markup=admin_menu_keyboard())
    else:
        sendf(m.chat.id, "ℹ️ Bu ID eýýäm admin.", reply_markup=admin_menu_keyboard())

@bot.message_handler(func=lambda m: (m.text or "") == "➖ Admin aýyr")
def admin_remove_prompt(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    msg = sendf(m.chat.id, "➖ Admin ID-ni giriziň:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_remove_step)

def admin_remove_step(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    try: aid = int((m.text or "").strip())
    except:
        sendf(m.chat.id, "⚠️ ID sany bolmaly."); return
    if str(aid) in db.get("admins", []):
        db["admins"].remove(str(aid)); save_db()
        sendf(m.chat.id, f"✅ Admin aýryldy: <code>{aid}</code>", reply_markup=admin_menu_keyboard())
    else:
        sendf(m.chat.id, "⚠️ Munuň ýaly admin ýok.", reply_markup=admin_menu_keyboard())

# Promo create/list
@bot.message_handler(func=lambda m: (m.text or "") == "🎯 Promo döret")
def admin_promo_create_prompt(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    msg = sendf(m.chat.id, "Format: KOD STARLAR LIMIT(0 üçin hiç)\nMysal: NEW2025 5 10", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_promo_create_step)

def admin_promo_create_step(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    parts = (m.text or "").strip().split()
    if len(parts) < 2:
        sendf(m.chat.id, "⚠️ Format ýalňyş."); return
    code = parts[0].upper()
    try: stars = float(parts[1])
    except:
        sendf(m.chat.id, "⚠️ Star sany ýalňyş."); return
    limit = None
    if len(parts) >= 3:
        try:
            l = int(parts[2]); limit = l if l>0 else None
        except:
            limit = None
    db.setdefault("promos", {})[code] = {"stars": stars, "limit": limit, "used": 0}
    save_db()
    sendf(m.chat.id, f"✅ Promocode döredildi: <code>{code}</code> — {stars} ⭐ — limit: {limit if limit is not None else 'heç'}", reply_markup=admin_menu_keyboard())

@bot.message_handler(func=lambda m: (m.text or "") == "📃 Promo sanaw")
def admin_promo_list(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    promos = db.get("promos", {})
    if not promos:
        sendf(m.chat.id, "📭 Promocode ýok.", reply_markup=admin_menu_keyboard()); return
    txt = "<b>📃 Promocodlar:</b>\n\n"
    for code,info in promos.items():
        txt += f"{code} — {info.get('stars',0)} ⭐ — used: {info.get('used',0)} — limit: {info.get('limit')}\n"
    sendf(m.chat.id, txt, reply_markup=admin_menu_keyboard())

# Referral bonus config
@bot.message_handler(func=lambda m: (m.text or "") == "⭐ Referal bonus")
def admin_set_referral_bonus_prompt(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    rb = db.get("referral_bonus", {"stars":1.0,"hours":0})
    cur = f"⚙️ Häzirki sazlama: <b>{rb.get('stars')} ⭐</b>, <b>{rb.get('hours')} sagat</b>.\n\nFormat: STARLAR HOURS (mysal: 1 24)\n"
    msg = sendf(m.chat.id, cur, reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_set_referral_bonus_step)

def admin_set_referral_bonus_step(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    parts = (m.text or "").strip().split()
    if len(parts) < 1:
        sendf(m.chat.id, "⚠️ Format ýalňyş."); return
    try: stars = float(parts[0])
    except: sendf(m.chat.id, "⚠️ Star sany ýalňyş."); return
    hours = 0
    if len(parts) >= 2:
        try: hours = int(parts[1])
        except: hours = 0
    db["referral_bonus"] = {"stars": stars, "hours": hours}; save_db()
    sendf(m.chat.id, f"✅ Referral bonus sazlandy: <b>{stars} ⭐</b> we <b>{hours} sagat</b> 🎉", reply_markup=admin_menu_keyboard())

# Broadcast
@bot.message_handler(func=lambda m: (m.text or "") == "📢 Broadcast")
def admin_broadcast_prompt(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    msg = sendf(m.chat.id, "📣 Broadcast üçin tekst giriziň:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_broadcast_step)

def admin_broadcast_step(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    text = m.text or ""
    cnt = 0
    for uid_str,u in db.get("users", {}).items():
        try:
            if u.get("banned"): continue
            sendf(int(uid_str), text); cnt += 1
        except: pass
    sendf(m.chat.id, f"✅ Broadcast ugradyldy: {cnt} ulanyjy", reply_markup=admin_menu_keyboard())

# Edit texts (Welcome, Guides/FAQ, VIP)
@bot.message_handler(func=lambda m: (m.text or "") == "✏️ Yazgy Uytget")
def admin_edit_text_prompt(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Welcome (Start mesajy)", "Guides/FAQ"); kb.row("VIP paket", "⬅️ Yza")
    msg = sendf(m.chat.id, "Haysy teksti üýtgedäýşiňiz:", reply_markup=kb)
    bot.register_next_step_handler(msg, admin_edit_text_choose)

def admin_edit_text_choose(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    choice = (m.text or "").strip()
    key_map = {"Welcome (Start mesajy)":"welcome", "Guides/FAQ":"guides", "VIP paket":"vip"}
    if choice not in key_map:
        sendf(m.chat.id, "⚠️ Dogry saýlama giriziň.", reply_markup=admin_menu_keyboard()); return
    db.setdefault("temp_admin_edit", {})["editing_key"] = key_map[choice]; save_db()
    msg = sendf(m.chat.id, "Taze teskti girizin (HTML kabul edilýär):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_edit_text_receive)

def admin_edit_text_receive(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    st = db.get("temp_admin_edit", {})
    key = st.get("editing_key")
    if not key:
        sendf(m.chat.id, "⚠️ Ýalňyş"); return
    new_text = m.text or ""
    db.setdefault("texts", {})[key] = new_text
    save_db()
    sendf(m.chat.id, "✅ Tekst ustunlikli girizildi.", reply_markup=admin_menu_keyboard())
    db.pop("temp_admin", None); save_db()

# Star doldur (admin -> user)
@bot.message_handler(func=lambda m: (m.text or "") == "Star doldur")
def admin_star_fill_prompt(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    msg = sendf(m.chat.id, "🔢 Hasabyny doldurjak ulanyjynyň ID-ni ýa-da @username-i giriziň:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_star_fill_target)

def admin_star_fill_target(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    target = (m.text or "").strip()
    if not target:
        sendf(m.chat.id, "⚠️ ID ýa-da @username giriziň."); return
    target_uid = None
    if target.isdigit():
        if str(int(target)) in db.get("users", {}):
            target_uid = str(int(target))
    else:
        found = find_user_by_username(target)
        if found:
            target_uid = found
    if not target_uid:
        sendf(m.chat.id, "⚠️ Ulanyjy tapylmady."); return
    db.setdefault("temp_admin", {})["star_target"] = target_uid; save_db()
    msg = sendf(m.chat.id, "Nace star geçsin? (mysal: 100):")
    bot.register_next_step_handler(msg, admin_star_fill_amount)

def admin_star_fill_amount(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    st = db.get("temp_admin", {})
    target_uid = st.get("star_target")
    if not target_uid:
        sendf(m.chat.id, "⚠️ Target tapylmady."); return
    try:
        amount = float((m.text or "").strip())
    except:
        sendf(m.chat.id, "⚠️ Star sany nädogry."); db.pop("temp_admin", None); save_db(); return
    u = db.get("users", {}).get(str(target_uid))
    if not u:
        sendf(m.chat.id, "⚠️ Ulanyjy DB-de ýok."); db.pop("temp_admin", None); save_db(); return
    u["stars"] = round(u.get("stars", 0.0) + amount, 2); save_db()
    pretty = int(amount) if float(amount).is_integer() else amount
    sendf(m.chat.id, f"✅ {pretty} ⭐ ugradyldy", reply_markup=admin_menu_keyboard())
    try: sendf(int(target_uid), f"🔔 Siziň hasabyňyza admin tarapyndan {pretty} ⭐ geldi ✨")
    except: pass
    db.pop("temp_admin", None); save_db()

# Ban/Unban
@bot.message_handler(func=lambda m: (m.text or "") == "🚫 Ulanyjy Ban")
def admin_ban_prompt(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    msg = sendf(m.chat.id, "❗ Ban etjek ulanyjynyň ID-ni ýa-da @username-ni giriziň:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_ban_step)

def admin_ban_step(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    target_raw = (m.text or "").strip()
    if not target_raw:
        sendf(m.chat.id, "⚠️ ID ýa-da @username giriziň."); return

    target_uid = None
    # if digit -> direct id
    if target_raw.isdigit():
        target_uid = int(target_raw)
    else:
        uname = target_raw.lstrip("@")
        # try db first
        found = find_user_by_username(uname)
        if found:
            target_uid = int(found)
        else:
            # try bot.get_chat() as fallback to resolve public username
            try:
                chatobj = bot.get_chat(target_raw if target_raw.startswith("@") else f"@{uname}")
                # only accept private users (type == 'private') or numeric id
                if chatobj and getattr(chatobj, "type", "") == "private":
                    target_uid = chatobj.id
            except Exception:
                target_uid = None

    if not target_uid:
        sendf(m.chat.id, "⚠️ Ulanyjy tapylmady (DB-de ýa-da Telegram-de ýok).", reply_markup=admin_menu_keyboard()); return

    su = str(target_uid)
    if su not in db.get("users", {}):
        # create minimal user record so ban flag can be stored
        db.setdefault("users", {})[su] = {
            "joined_at": now_iso(),
            "username": ("@" + uname) if not target_raw.isdigit() else "",
            "ref_by": None,
            "banned": True,
            "stars": 0.0,
            "temp_stars": [],
            "trial_end": (datetime.utcnow() + timedelta(days=FREE_TRIAL_DAYS)).isoformat(),
            "posts": [],
            "last_daily_bonus": None,
            "lang": "tk"
        }
    else:
        db["users"][su]["banned"] = True
    save_db()
    # notify banned user
    try: sendf(target_uid, BAN_MESSAGE)
    except: pass
    # notify all admins
    info = (f"🚨 <b>Ulanyjy ban edildi</b>\nID: <code>{target_uid}</code>\n"
            f"By admin: <code>{uid}</code>\n\n{BAN_MESSAGE}")
    for aid in db.get("admins", []):
        try:
            sendf(int(aid), info)
        except: pass
    sendf(m.chat.id, f"🔒 ✅ Ulanyjy ban edildi: <code>{target_uid}</code>", reply_markup=admin_menu_keyboard())

@bot.message_handler(func=lambda m: (m.text or "") == "✅ Ulanyjy Unban")
def admin_unban_prompt(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    msg = sendf(m.chat.id, "✅ Unban etjek ulanyjynyň ID-ny ýa-da @username-ni giriziň:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_unban_step)

def admin_unban_step(m: types.Message):
    uid = m.from_user.id
    if not is_admin(uid): return
    target_raw = (m.text or "").strip()
    if not target_raw:
        sendf(m.chat.id, "⚠️ ID ýa-da @username giriziň."); return

    target_uid = None
    if target_raw.isdigit():
        target_uid = int(target_raw)
    else:
        uname = target_raw.lstrip("@")
        found = find_user_by_username(uname)
        if found:
            target_uid = int(found)
        else:
            # try to resolve via get_chat
            try:
                chatobj = bot.get_chat(target_raw if target_raw.startswith("@") else f"@{uname}")
                if chatobj and getattr(chatobj, "type", "") == "private":
                    target_uid = chatobj.id
            except Exception:
                target_uid = None

    if not target_uid:
        sendf(m.chat.id, "⚠️ Ulanyjy tapylmady.", reply_markup=admin_menu_keyboard()); return

    su = str(target_uid)
    u = db.get("users", {}).get(su)
    if not u:
        sendf(m.chat.id, "⚠️ Ulanyjy DB-de ýok.", reply_markup=admin_menu_keyboard()); return
    u["banned"] = False; save_db()
    sendf(m.chat.id, f"✅ Ulanyjy unban edildi: <code>{target_uid}</code>", reply_markup=admin_menu_keyboard())
    try: sendf(target_uid, "✅ Siziň ban-ňyz aýryldy. Hoş geldiňiz!")
    except: pass

# ---------------- Catch-all (admin notify + other) ----------------
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "document", "audio", "video"])
def catch_all(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid, m.from_user.username or m.from_user.first_name)
    if banned_guard(uid, uid):
        u = db.get("users", {}).get(str(uid), {})
        if u and u.get("banned"):
            info = f"🔔 Banned user tried interacting: <code>{uid}</code>\n{BAN_MESSAGE}"
            for aid in db.get("admins", []):
                try: sendf(int(aid), info)
                except: pass
        return
    st = user_states.get(uid, {})
    if st.get("awaiting_admin_msg"):
        # user is about to send message to admins
        _, _, total = get_user_star_details(uid)
        if total < ADMIN_NOTIFY_COST:
            sendf(uid, "⚠️ Ýeterlik ⭐ ýok. (10 ⭐ gerek)")
            user_states.pop(uid, None)
            return
        ok = deduct_stars(uid, ADMIN_NOTIFY_COST)
        if not ok:
            sendf(uid, "⚠️ Deduction başarısız.")
            user_states.pop(uid, None)
            return
        u = db["users"].get(str(uid), {})
        referrals = len(db.get("referrals", {}).get(str(uid), []))
        posts_count = len(u.get("posts", []))
        stars_now = get_user_star_details(uid)[2]
        header = (f"📨 <b>Admine habar</b>\n"
                  f"Kim: @{u.get('username','')} (ID: <code>{uid}</code>)\n"
                  f"Çaýran dostlar: {referrals}\n"
                  f"Post sany: {posts_count}\n"
                  f"Star: {stars_now:.2f}\n\n")
        for aid in db.get("admins", []):
            try:
                aid_i = int(aid)
                if m.photo:
                    # send header and forward photo
                    sendf(aid_i, header + (m.caption or ""))
                    bot.send_photo(aid_i, m.photo[-1].file_id, caption="— Habaryň suraty —")
                elif m.document:
                    sendf(aid_i, header + (m.caption or ""))
                    bot.send_document(aid_i, m.document.file_id, caption="— Habaryň file —")
                else:
                    sendf(aid_i, header + (m.text or ""))
            except Exception:
                pass
        sendf(uid, "✅ Habaryňyz adminlara ugradyldy.", reply_markup=main_menu_keyboard(uid))
        user_states.pop(uid, None)
        return
    # nothing else to do here

# ---------------- Startup message ----------------
if __name__ == "__main__":
    print("Bot başlatılıyor...")
    print(f"Admin ID'leri: {ADMIN_IDS}")
    print(f"Veritabanı yolu: {DB_PATH}")
    bot.infinity_polling(skip_pending=True, timeout=60)

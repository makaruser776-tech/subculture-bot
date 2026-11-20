import json
import os
import random
import sqlite3
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or os.getenv("TOKEN")
    or ""
).strip()

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

ADMIN_USERNAME = "oi_petersburg"
START_COINS = 100
DAILY_BONUS = 60
DAILY_COOLDOWN = 86400
WORK_COOLDOWN = 3600

WORK_EVENTS = (
    "Помог таскать колонки перед локальным гигом",
    "Продал пару лишних значков на входе в клуб",
    "Раздавал флаеры на андеграунд-концерт",
    "Нашел мелочь возле старой реп-точки",
    "Помог бармену после закрытия рок-бара",
    "Перепродал старую кассету коллекционеру",
)

CASES = {
    "street": {
        "name": "📦 Уличный кейс",
        "price": 20,
        "desc": "Базовый набор с улицы. Высокий шанс поймать классику вроде панков, металлистов или скейтеров.",
        "weights": (65, 25, 8, 2),
    },
    "club": {
        "name": "🎸 Клубный кейс",
        "price": 45,
        "desc": "С закрытых гигов и тусовок. Повышенный шанс на нишевые тусовки: эмо, готов, хардкорщиков и гранж.",
        "weights": (30, 45, 20, 5),
    },
    "vintage": {
        "name": "📻 Винтажный кейс",
        "price": 80,
        "desc": "Для ценителей олдскула. Отличный шанс выбить редких трад-скинхедов, рокабилли и киберготов.",
        "weights": (10, 30, 45, 15),
    },
    "legend": {
        "name": "👑 Архивный кейс",
        "price": 150,
        "desc": "Элитный кейс с почти исчезнувшими легендами: модами, хиппи, стимпанком и тедди-боями.",
        "weights": (0, 15, 45, 40),
    },
}

CARDS = {
    "Обычная": (
        {"id": "metal", "name": "Металлист", "desc": "Косухи, мерч тяжелых групп, длинные волосы, тяжелый рок и метал."},
        {"id": "punk", "name": "Панк", "desc": "Протест, нонконформизм, панк-рок, булавки, кожанки и ирокезы."},
        {"id": "casual", "name": "Кежуалс", "desc": "Околофутбольная культура, брендовая повседневная одежда (Stone Island, Fred Perry)."},
        {"id": "skater", "name": "Скейтер", "desc": "Уличная культура катания, кеды (Vans, DC), широкие штаны и худи."},
        {"id": "rapper", "name": "Рэпер / Хип-хоп", "desc": "Уличный стиль (оверсайз, кроссовки, кепки), рэп-музыка и брейк-данс."},
    ),
    "Редкая": (
        {"id": "goth", "name": "Гот", "desc": "Мрачная романтика, пост-панк, черный цвет, серебро и готический макияж."},
        {"id": "emo", "name": "Эмо", "desc": "Эмо-кор, открытое выражение чувств, косые челки, черно-розовая гамма и кеды."},
        {"id": "hardcore", "name": "Хардкорщик", "desc": "Агрессивный панк, DIY-этика, локальные гиги, часто ЗОЖ (straight edge)."},
        {"id": "grunge", "name": "Гранж", "desc": "Небрежность, фланелевые рубашки в клетку, рваные джинсы и звук Сиэтла 90-х."},
        {"id": "biker", "name": "Байкер", "desc": "Братство мотоциклистов, кожаные жилеты с нашивками, чопперы и рок-н-ролл."},
    ),
    "Эпическая": (
        {"id": "skinhead", "name": "Скинхед (Трад)", "desc": "Рабочий класс 60-х, ска и регги, подтяжки, тяжелые ботинки, клетчатые рубашки и Spirit of '69."},
        {"id": "rasta", "name": "Растаман", "desc": "Философия регги, духовная свобода, дреды и цвета эфиопского флага."},
        {"id": "cybergoth", "name": "Кибергот", "desc": "Смесь готики и рейва: кислотные цвета, респираторы, очки-гогглы и электроника."},
        {"id": "rockabilly", "name": "Рокабилли", "desc": "Эстетика 50-х, рок-н-ролл, прически-коки, кожаные куртки и ретро-стиль."},
    ),
    "Легендарная": (
        {"id": "hippie", "name": "Хиппи", "desc": "«Дети цветов» 60-х, пацифизм, единство с природой, фенечки и клеш."},
        {"id": "mod", "name": "Мод", "desc": "Британские стиляги 60-х: строгие костюмы, парки, мотороллеры и соул-музыка."},
        {"id": "steampunk", "name": "Стимпанк", "desc": "Эстетика викторианской эпохи и паровых машин: цилиндры, корсеты и шестеренки."},
        {"id": "teddyboy", "name": "Тедди-бой", "desc": "Британские бунтари 50-х в длинных сюртуках в эдвардианском стиле."},
    ),
}

RARITY_ORDER = ("Обычная", "Редкая", "Эпическая", "Легендарная")
RARITY_EMOJI = {"Обычная": "⚪️", "Редкая": "🔵", "Эпическая": "🟣", "Легендарная": "🟡"}


def init_db():
    conn = sqlite3.connect("game.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, coins INTEGER, cards TEXT, last_daily INTEGER DEFAULT 0, last_work INTEGER DEFAULT 0)")
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_work INTEGER DEFAULT 0")
    except Exception:
        pass
    conn.commit()
    conn.close()


init_db()


def is_admin(user):
    if user and user.username and user.username.lower() == ADMIN_USERNAME:
        return True
    return False


def get_user(user):
    user_id = user.id
    admin = is_admin(user)
    conn = sqlite3.connect("game.db")
    cursor = conn.cursor()
    cursor.execute("SELECT coins, cards, last_daily, last_work FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        coins = 99999 if admin else START_COINS
        cursor.execute("INSERT INTO users (user_id, coins, cards, last_daily, last_work) VALUES (?, ?, ?, ?, ?)", (user_id, coins, "{}", 0, 0))
        conn.commit()
        conn.close()
        return coins, {}, 0, 0
    coins, cards_json, last_daily, last_work = row
    if admin and coins != 99999:
        coins = 99999
        cursor.execute("UPDATE users SET coins = ? WHERE user_id = ?", (coins, user_id))
        conn.commit()
    conn.close()
    return coins, json.loads(cards_json), last_daily, (last_work or 0)


def save_user(user, coins, cards, last_daily, last_work):
    if is_admin(user):
        coins = 99999
    conn = sqlite3.connect("game.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET coins = ?, cards = ?, last_daily = ?, last_work = ? WHERE user_id = ?", (coins, json.dumps(cards), last_daily, last_work, user.id))
    conn.commit()
    conn.close()
def get_menu_text(name, coins):
    lines = list()
    lines.append(f"🎲 <b>Кейсы субкультур</b> | Игрок: <b>{name}</b>")
    lines.append(f"💰 Твой баланс: <b>{coins} 🪙</b>\n")
    for c in CASES.values():
        w0, w1, w2, w3 = c["weights"]
        lines.append(f"<b>{c['name']} — {c['price']} 🪙</b>\n<i>{c['desc']}</i>\nШансы: ⚪️{w0}% | 🔵{w1}% | 🟣{w2}% | 🟡{w3}%\n")
    return "\n".join(lines)


def main_menu_kb(user_id):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(f"📦 Уличный ({CASES['street']['price']} 🪙)", callback_data=f"o|street|{user_id}"),
        InlineKeyboardButton(f"🎸 Клубный ({CASES['club']['price']} 🪙)", callback_data=f"o|club|{user_id}"),
    )
    kb.row(
        InlineKeyboardButton(f"📻 Винтажный ({CASES['vintage']['price']} 🪙)", callback_data=f"o|vintage|{user_id}"),
        InlineKeyboardButton(f"👑 Архивный ({CASES['legend']['price']} 🪙)", callback_data=f"o|legend|{user_id}"),
    )
    kb.row(
        InlineKeyboardButton("🗄 Мой шкаф", callback_data=f"s|{user_id}"),
        InlineKeyboardButton("🎁 Бонус дня", callback_data=f"d|{user_id}"),
    )
    kb.row(
        InlineKeyboardButton("🎸 Потусить на районе (+15..25 🪙)", callback_data=f"w|{user_id}"),
    )
    return kb


def after_open_kb(case_key, user_id):
    case = CASES[case_key]
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton(f"🔄 Открыть еще ({case['price']} 🪙)", callback_data=f"o|{case_key}|{user_id}"))
    kb.row(
        InlineKeyboardButton("🗄 Мой шкаф", callback_data=f"s|{user_id}"),
        InlineKeyboardButton("🔙 Все кейсы", callback_data=f"m|{user_id}"),
    )
    return kb


def back_kb(user_id):
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("🔙 Назад к кейсам", callback_data=f"m|{user_id}"))
    return kb


@bot.message_handler(commands=("start", "game", "chest", "case"))
def cmd_menu(message):
    user = message.from_user
    coins, _, _, _ = get_user(user)
    bot.send_message(message.chat.id, get_menu_text(user.first_name, coins), reply_markup=main_menu_kb(user.id))


@bot.message_handler(commands=("rich",))
def cmd_rich(message):
    user = message.from_user
    if is_admin(user):
        _, cards, last_daily, last_work = get_user(user)
        save_user(user, 99999, cards, last_daily, last_work)
        bot.reply_to(message, "💰 Админ-баланс активирован: <b>99999 🪙</b>")


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    parts = call.data.split("|")
    action = parts.pop(0)
    owner_id = int(parts.pop(-1))
    user = call.from_user

    if user.id != owner_id:
        bot.answer_callback_query(call.id, "❌ Это не твое меню! Напиши /case чтобы открыть свое.", show_alert=True)
        return

    if action == "m":
        coins, _, _, _ = get_user(user)
        try:
            bot.edit_message_text(get_menu_text(user.first_name, coins), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu_kb(owner_id))
        except Exception:
            pass

    elif action == "o":
        case_key = parts.pop(0)
        case = CASES[case_key]
        coins, cards, last_daily, last_work = get_user(user)

        if coins < case["price"]:
            bot.answer_callback_query(call.id, f"❌ Не хватает монет! Нужно {case['price']} 🪙, а у тебя {coins} 🪙.", show_alert=True)
            return

        new_coins = 99999 if is_admin(user) else (coins - case["price"])
        rarity = random.choices(RARITY_ORDER, weights=case["weights"], k=1).pop()
        card = random.choice(CARDS[rarity])

        card_id = card["id"]
        is_new = card_id not in cards
        cards[card_id] = cards.get(card_id, 0) + 1
        save_user(user, new_coins, cards, last_daily, last_work)

        status_text = "🆕 <b>НОВАЯ КАРТОЧКА!</b>" if is_new else f"♻️ Дубликат (в шкафу: {cards[card_id]} шт.)"
        emoji = RARITY_EMOJI[rarity]

        bot.edit_message_text(
            f"Ты открыл <b>{case['name']}</b>!\n\n{status_text}\n{emoji} Редкость: <b>{rarity}</b>\n🃏 Карточка: <b>{card['name']}</b>\n📖 <i>{card['desc']}</i>\n\nОстаток на балансе: <b>{new_coins} 🪙</b>",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=after_open_kb(case_key, owner_id),
        )

    elif action == "s":
        coins, cards, _, _ = get_user(user)
        total_cards = sum(len(group) for group in CARDS.values())
        opened_count = len(cards)

        lines = list()
        lines.append(f"🗄 <b>Коллекционный шкаф ({user.first_name})</b>")
        lines.append(f"Собрано: <b>{opened_count} из {total_cards}</b> | Баланс: <b>{coins} 🪙</b>\n")

        for rarity in RARITY_ORDER:
            emoji = RARITY_EMOJI[rarity]
            lines.append(f"<b>{emoji} — {rarity} —</b>")
            for card in CARDS[rarity]:
                count = cards.get(card["id"], 0)
                if count > 0:
                    lines.append(f"✅ {card['name']} (x{count})")
                else:
                    lines.append("🔒 ???")
            lines.append("")

        bot.edit_message_text("\n".join(lines), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=back_kb(owner_id))

    elif action == "d":
        coins, cards, last_daily, last_work = get_user(user)
        now = int(time.time())

        if now - last_daily < DAILY_COOLDOWN:
            left_hours = round((DAILY_COOLDOWN - (now - last_daily)) / 3600, 1)
            bot.answer_callback_query(call.id, f"⏳ Бонус уже получен! Приходи через {left_hours} ч.", show_alert=True)
            return

        new_coins = 99999 if is_admin(user) else (coins + DAILY_BONUS)
        save_user(user, new_coins, cards, now, last_work)
        bot.answer_callback_query(call.id, f"🎁 Получено +{DAILY_BONUS} 🪙! Теперь у тебя {new_coins} 🪙.", show_alert=True)

        try:
            bot.edit_message_text(get_menu_text(user.first_name, new_coins), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu_kb(owner_id))
        except Exception:
            pass

    elif action == "w":
        coins, cards, last_daily, last_work = get_user(user)
        now = int(time.time())

        if now - last_work < WORK_COOLDOWN:
            left_mins = int((WORK_COOLDOWN - (now - last_work)) / 60) + 1
            hours = left_mins // 60
            mins = left_mins % 60
            wait_str = f"{hours} ч. {mins} мин." if hours > 0 else f"{mins} мин."
            bot.answer_callback_query(call.id, f"⏳ Ты уже потусил! Отдохни еще {wait_str}", show_alert=True)
            return

        earned = random.randint(15, 25)
        event = random.choice(WORK_EVENTS)
        new_coins = 99999 if is_admin(user) else (coins + earned)
        save_user(user, new_coins, cards, last_daily, now)
        bot.answer_callback_query(call.id, f"🎸 {event}!\nЗаработано: +{earned} 🪙", show_alert=True)

        try:
            bot.edit_message_text(get_menu_text(user.first_name, new_coins), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu_kb(owner_id))
        except Exception:
            pass


if __name__ == "__main__":
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)

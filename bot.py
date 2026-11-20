import asyncio
import json
import os
import random
import sqlite3
import time
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or os.getenv("TOKEN")
    or os.getenv("API_TOKEN")
    or ""
).strip()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- НАСТРОЙКИ ИГРЫ ---

START_COINS = 100
DAILY_BONUS = 60
DAILY_COOLDOWN = 86400

# 4 вида кейсов: цена, описание и шансы (Обычная, Редкая, Эпическая, Легендарная)
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

# 18 карточек по 4 редкостям
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
RARITY_EMOJI = {
    "Обычная": "⚪️",
    "Редкая": "🔵",
    "Эпическая": "🟣",
    "Легендарная": "🟡",
}

# --- БАЗА ДАННЫХ ---

conn = sqlite3.connect("game.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        coins INTEGER,
        cards TEXT,
        last_daily INTEGER DEFAULT 0
    )
""")
conn.commit()


def get_user(user_id: int):
    cursor.execute("SELECT coins, cards, last_daily FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute(
            "INSERT INTO users (user_id, coins, cards, last_daily) VALUES (?, ?, ?, ?)",
            (user_id, START_COINS, "{}", 0),
        )
        conn.commit()
        return START_COINS, {}, 0
    coins, cards_json, last_daily = row
    return coins, json.loads(cards_json), last_daily


def save_user(user_id: int, coins: int, cards: dict, last_daily: int):
    cursor.execute(
        "UPDATE users SET coins = ?, cards = ?, last_daily = ? WHERE user_id = ?",
        (coins, json.dumps(cards), last_daily, user_id),
    )
    conn.commit()


# --- КЛАВИАТУРЫ И ТЕКСТЫ ---

def get_menu_text(name: str, coins: int) -> str:
    lines = list()
    lines.append(f"🎲 <b>Кейсы субкультур</b> | Игрок: <b>{name}</b>")
    lines.append(f"💰 Твой баланс: <b>{coins} 🪙</b>\n")
    for c in CASES.values():
        w0, w1, w2, w3 = c["weights"]
        lines.append(
            f"<b>{c['name']} — {c['price']} 🪙</b>\n"
            f"<i>{c['desc']}</i>\n"
            f"Шансы: ⚪️{w0}% | 🔵{w1}% | 🟣{w2}% | 🟡{w3}%\n"
        )
    return "\n".join(lines)


def main_menu_kb(user_id: int):
    rows = list()
    rows.append((
        InlineKeyboardButton(text=f"📦 Уличный ({CASES['street']['price']} 🪙)", callback_data=f"open:street:{user_id}"),
        InlineKeyboardButton(text=f"🎸 Клубный ({CASES['club']['price']} 🪙)", callback_data=f"open:club:{user_id}"),
    ))
    rows.append((
        InlineKeyboardButton(text=f"📻 Винтажный ({CASES['vintage']['price']} 🪙)", callback_data=f"open:vintage:{user_id}"),
        InlineKeyboardButton(text=f"👑 Архивный ({CASES['legend']['price']} 🪙)", callback_data=f"open:legend:{user_id}"),
    ))
    rows.append((
        InlineKeyboardButton(text="🗄 Мой шкаф", callback_data=f"shelf:{user_id}"),
        InlineKeyboardButton(text="🎁 Бонус дня", callback_data=f"daily:{user_id}"),
    ))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_open_kb(case_key: str, user_id: int):
    case = CASES[case_key]
    rows = list()
    rows.append((
        InlineKeyboardButton(text=f"🔄 Открыть еще ({case['price']} 🪙)", callback_data=f"open:{case_key}:{user_id}"),
    ))
    rows.append((
        InlineKeyboardButton(text="🗄 Мой шкаф", callback_data=f"shelf:{user_id}"),
        InlineKeyboardButton(text="🔙 Все кейсы", callback_data=f"menu:{user_id}"),
    ))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_kb(user_id: int):
    rows = list()
    rows.append((
        InlineKeyboardButton(text="🔙 Назад к кейсам", callback_data=f"menu:{user_id}"),
    ))
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start", "game", "chest", "case"))
async def cmd_menu(message: types.Message):
    user_id = message.from_user.id
    coins, _, _ = get_user(user_id)
    await message.answer(
        get_menu_text(message.from_user.first_name, coins),
        reply_markup=main_menu_kb(user_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("menu:"))
async def cb_menu(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    owner_id = int(parts.pop())
    if callback.from_user.id != owner_id:
        return await callback.answer("❌ Это не твое меню! Напиши /case чтобы открыть свое.", show_alert=True)

    coins, _, _ = get_user(owner_id)
    await callback.message.edit_text(
        get_menu_text(callback.from_user.first_name, coins),
        reply_markup=main_menu_kb(owner_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("open:"))
async def cb_open_case(callback: types.CallbackQuery):
    _, case_key, owner_id_str = callback.data.split(":")
    owner_id = int(owner_id_str)

    if callback.from_user.id != owner_id:
        return await callback.answer("❌ Не трогай чужой кейс! Вызови свой командой /case", show_alert=True)

    case = CASES[case_key]
    coins, cards, last_daily = get_user(owner_id)

    if coins < case["price"]:
        return await callback.answer(f"❌ Не хватает монет! Нужно {case['price']} 🪙, а у тебя {coins} 🪙.", show_alert=True)

    coins -= case["price"]

    rarity = random.choices(RARITY_ORDER, weights=case["weights"], k=1).pop()
    card = random.choice(CARDS[rarity])

    card_id = card["id"]
    is_new = card_id not in cards
    cards[card_id] = cards.get(card_id, 0) + 1
    save_user(owner_id, coins, cards, last_daily)

    status_text = "🆕 <b>НОВАЯ КАРТОЧКА!</b>" if is_new else f"♻️ Дубликат (в шкафу: {cards[card_id]} шт.)"
    emoji = RARITY_EMOJI[rarity]

    await callback.message.edit_text(
        f"Ты открыл <b>{case['name']}</b>!\n\n"
        f"{status_text}\n"
        f"{emoji} Редкость: <b>{rarity}</b>\n"
        f"🃏 Карточка: <b>{card['name']}</b>\n"
        f"📖 <i>{card['desc']}</i>\n\n"
        f"Остаток на балансе: <b>{coins} 🪙</b>",
        reply_markup=after_open_kb(case_key, owner_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("shelf:"))
async def cb_shelf(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    owner_id = int(parts.pop())
    if callback.from_user.id != owner_id:
        return await callback.answer("❌ Это чужой шкаф! Открой свой через /case", show_alert=True)

    coins, cards, _ = get_user(owner_id)
    total_cards = sum(len(group) for group in CARDS.values())

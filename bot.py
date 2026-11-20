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
        "name": "📦 Уличный",
        "price": 20,
        "desc": "Классика улицы: панки, металлисты, скейтер и др.",
        "weights": (65, 25, 8, 2),
    },
    "club": {
        "name": "🎸 Клубный",
        "price": 45,
        "desc": "Нишевые тусовки: эмо, готы, хардкорщики, краст, андеры.",
        "weights": (30, 45, 20, 5),
    },
    "vintage": {
        "name": "📻 Винтажный",
        "price": 80,
        "desc": "Олдскул: трад- и троян-скинхеды, хард-моды, рокабилли.",
        "weights": (10, 30, 45, 15),
    },
    "legend": {
        "name": "👑 Архивный",
        "price": 150,
        "desc": "Редкие легенды: моды, сьюдхеды, хиппи, тедди-бои.",
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
        {"id": "raver", "name": "Рейвер", "desc": "Ночные электронные вечеринки, техно, очки-маски и яркий спортивный стиль."},
        {"id": "workouter", "name": "Воркаутер", "desc": "Уличные турники, брусья, спортивный режим и тренировки на площадках."},
        {"id": "animeshnik", "name": "Анимешник", "desc": "Японская анимация, манга, косплей-фестивали и значки на рюкзаке."},
        {"id": "rocker", "name": "Рокер", "desc": "Классический рок-н-ролл, джинсовки с нашивками, гитары и живые концерты."},
    ),
    "Редкая": (
        {"id": "goth", "name": "Гот", "desc": "Мрачная романтика, пост-панк, черный цвет, серебро и готический макияж."},
        {"id": "emo", "name": "Эмо", "desc": "Эмо-кор, открытое выражение чувств, косые челки, черно-розовая гамма и кеды."},
        {"id": "hardcore", "name": "Хардкорщик", "desc": "Агрессивный панк, DIY-этика, локальные гиги и бешеный слэм."},
        {"id": "grunge", "name": "Гранж", "desc": "Небрежность, фланелевые рубашки в клетку, рваные джинсы и звук Сиэтла 90-х."},
        {"id": "biker", "name": "Байкер", "desc": "Братство мотоциклистов, кожаные жилеты с нашивками, чопперы и рок-н-ролл."},
        {"id": "crust", "name": "Краст-панк", "desc": "Мрачный DIY-панк, нашивки нитками-зубной нитью, анархо-символика и дибит."},
        {"id": "madboy", "name": "Мэдбой", "desc": "Человек, не скупящийся никчемной жизнью. Аскет, освобождающий пространство от лишнего, мизантроп, что его не подпускает, и хозяин жизни, которую он меняет под обстоятельства."},
        {"id": "under", "name": "Андер", "desc": "Уличный андеграунд, бум-бэп и грязный звук подвалов, оверсайз, кроссовки и независимость от мейнстрима."},
        {"id": "postpunk", "name": "Пост-панк / Думер", "desc": "Холодный бас, драм-машины, черные пальто, панельки и ночные прогулки."},
        {"id": "sxe", "name": "Стрейт-эджер (sXe)", "desc": "Черные кресты на тыльной стороне ладоней, полный отказ от алкоголя и табака."},
        {"id": "trap", "name": "Нью-скул / Трэп", "desc": "Современный уличный звук, дрилл, балаклавы, массивные кроссовки и андеграунд."},
    ),
    "Эпическая": (
        {"id": "skinhead", "name": "Скинхед (Трад)", "desc": "Рабочий класс 60-х, ска и регги, подтяжки, тяжелые ботинки, клетчатые рубашки и Spirit of '69."},
        {"id": "trojan", "name": "Троян-скинхед", "desc": "Первая волна скинхедов конца 60-х, выросшая на ямайском ска, рокстеди, раннем регги и релизах лейбла Trojan Records."},
        {"id": "hardmod", "name": "Хард-мод", "desc": "Уличная ветвь модов конца 60-х: короткие стрижки, рабочая одежда, тяжелые ботинки и переход к ранним скинхедам."},
        {"id": "rasta", "name": "Растаман", "desc": "Философия регги, духовная свобода, дреды и цвета эфиопского флага."},
        {"id": "cybergoth", "name": "Кибергот", "desc": "Смесь готики и рейва: кислотные цвета, респираторы, очки-гогглы и электроника."},
        {"id": "rockabilly", "name": "Рокабилли", "desc": "Эстетика 50-х, рок-н-ролл, прически-коки, кожаные куртки и ретро-стиль."},
        {"id": "psychobilly", "name": "Психобилли", "desc": "Гремучая смесь рокабилли и панка: контрабас, хоррор-эстетика и высокий квифф."},
        {"id": "rudeboy", "name": "Руд-бой", "desc": "Ямайские стиляги 60-х: узкие костюмы, шляпы-трилби, ска и рокстеди."},
        {"id": "oiskin", "name": "Oi!-скинхед", "desc": "Уличный панк рабочего класса конца 70-х, харрингтоны, поло и громкие хоры на гигах."},
        {"id": "visualkei", "name": "Визуал-кей", "desc": "Японский авангардный рок с ярким гримом, сложными прическами и эпатажными костюмами."},
        {"id": "dieselpunk", "name": "Дизельпанк", "desc": "Ретрофутуризм эпохи 20–40-х годов: авиаторские куртки, гогглы и эстетика моторов."},
    ),
    "Легендарная": (
        {"id": "hippie", "name": "Хиппи", "desc": "«Дети цветов» 60-х, пацифизм, единство с природой, фенечки и клеш."},
        {"id": "mod", "name": "Мод", "desc": "Британские стиляги 60-х: строгие костюмы, парки, мотороллеры и соул-музыка."},
        {"id": "suedehead", "name": "Сьюдхед", "desc": "Эволюция скинхедов начала 70-х: чуть более длинные волосы с пробором, строгие костюмы-двойки, лоферы, броги и кэжуал-шик."},
        {"id": "steampunk", "name": "Стимпанк", "desc": "Эстетика викторианской эпохи и паровых машин: цилиндры, корсеты и шестеренки."},
        {"id": "teddyboy", "name": "Тедди-бой", "desc": "Британские бунтари 50-х в длинных сюртуках в эдвардианском стиле."},
        {"id": "beatnik", "name": "Битник", "desc": "Бунтари-интеллектуалы 50-х: черные водолазки, береты, джаз и андеграундная поэзия."},
        {"id": "newwave", "name": "Нью-вейв / Синти", "desc": "Авангард 80-х: синтезаторы, геометричные прически, неон и холодная электроника."},
        {"id": "cyberpunk", "name": "Киберпанк", "desc": "Хай-тек и низкий уровень жизни: неон, техно-одежда и эстетика будущего."},
        {"id": "swingkid", "name": "Свинг-кид", "desc": "Подпольные любители джаза и свинга 30–40-х: широкие костюмы-зуты и шляпы."},
        {"id": "glamrock", "name": "Глэм-рокер", "desc": "Театральный рок 70-х: блестки, обувь на высокой платформе и яркий сценический образ."},
    ),
}

RARITY_ORDER = ("Обычная", "Редкая", "Эпическая", "Легендарная")
RARITY_EMOJI = {"Обычная": "⚪️", "Редкая": "🔵", "Эпическая": "🟣", "Легендарная": "🟡"}

DUP_PRICES = {"Обычная": 5, "Редкая": 12, "Эпическая": 25, "Легендарная": 50}
SINGLE_PRICES = {"Обычная": 2, "Редкая": 6, "Эпическая": 12, "Легендарная": 25}


def find_card_info(card_id):
    for rarity, group in CARDS.items():
        for card in group:
            if card["id"] == card_id:
                return rarity, card["name"]
    return "Обычная", card_id


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
    return (
        f"🎲 <b>Кейсы субкультур</b> | {name}\n"
        f"💰 Баланс: <b>{coins} 🪙</b>\n"
        f"<i>Выбери кейс ниже или загляни в шкаф:</i>"
    )


def get_info_text():
    lines = list()
    lines.append("ℹ️ <b>Шансы и скупка карточек:</b>\n")
    for c in CASES.values():
        w0, w1, w2, w3 = c["weights"]
lines.append(f"{c['name']} ({c['price']} 🪙) — {c['desc']}\n⚪️{w0}% | 🔵{w1}% | 🟣{w2}% | 🟡{w3}%\n")
lines.append("♻️ Дубли: ⚪️5 🪙 | 🔵12 🪙 | 🟣25 🪙 | 🟡50 🪙")
lines.append("💸 Обычная продажа: ⚪️2 🪙 | 🔵6 🪙 | 🟣12 🪙 | 🟡25 🪙")
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
InlineKeyboardButton("🗄 Шкаф", callback_data=f"s|{user_id}"),
InlineKeyboardButton("🎁 Бонус", callback_data=f"d|{user_id}"),
InlineKeyboardButton("ℹ️ Шансы", callback_data=f"i|{user_id}"),
)
kb.row(
InlineKeyboardButton("🎸 Потусить (+15..25 🪙)", callback_data=f"w|{user_id}"),
InlineKeyboardButton("♻️ Продать дубли", callback_data=f"x|{user_id}"),
)
return kb
def after_open_kb(case_key, user_id):
case = CASES[case_key]
kb = InlineKeyboardMarkup()
kb.row(InlineKeyboardButton(f"🔄 Еще ({case['price']} 🪙)", callback_data=f"o|{case_key}|{user_id}"))
kb.row(
InlineKeyboardButton("🗄 Шкаф", callback_data=f"s|{user_id}"),
InlineKeyboardButton("🔙 Меню", callback_data=f"m|{user_id}"),
)
return kb
def back_kb(user_id):
kb = InlineKeyboardMarkup()
kb.row(InlineKeyboardButton("🔙 Назад", callback_data=f"m|{user_id}"))
return kb
def shelf_kb(user_id):
kb = InlineKeyboardMarkup()
kb.row(InlineKeyboardButton("🏷 Поставить тег в чате", callback_data=f"t|0|{user_id}"))
kb.row(
InlineKeyboardButton("♻️ Продать дубли", callback_data=f"x|{user_id}"),
InlineKeyboardButton("💸 Продать карту", callback_data=f"p|0|{user_id}"),
)
kb.row(InlineKeyboardButton("🔙 Назад в меню", callback_data=f"m|{user_id}"))
return kb
def tag_list_kb(cards, page, user_id):
kb = InlineKeyboardMarkup()
owned_ids = list(cards.keys())
per_page = 6
total_pages = max(1, (len(owned_ids) + per_page - 1) // per_page)
page = max(0, min(page, total_pages - 1))
chunk = owned_ids[page * per_page : (page + 1) * per_page]
for cid in chunk:
rarity, name = find_card_info(cid)
emoji = RARITY_EMOJI[rarity]
kb.row(InlineKeyboardButton(f"{emoji} {name}", callback_data=f"g|{cid}|{user_id}"))
nav = list()
if page > 0:
nav.append(InlineKeyboardButton("⬅️", callback_data=f"t|{page - 1}|{user_id}"))
if page < total_pages - 1:
nav.append(InlineKeyboardButton("➡️", callback_data=f"t|{page + 1}|{user_id}"))
if nav:
kb.row(*nav)
kb.row(InlineKeyboardButton("🔙 В шкаф", callback_data=f"s|{user_id}"))
return kb
def sell_list_kb(cards, page, user_id):
kb = InlineKeyboardMarkup()
owned_ids = list(cards.keys())
per_page = 6
total_pages = max(1, (len(owned_ids) + per_page - 1) // per_page)
page = max(0, min(page, total_pages - 1))
chunk = owned_ids[page * per_page : (page + 1) * per_page]
for cid in chunk:
rarity, name = find_card_info(cid)
emoji = RARITY_EMOJI[rarity]
count = cards[cid]
price = DUP_PRICES[rarity] if count > 1 else SINGLE_PRICES[rarity]
tag = "дубль" if count > 1 else "последняя"
kb.row(InlineKeyboardButton(f"{emoji} {name} (x{count}, {tag}) — +{price} 🪙", callback_data=f"c|{cid}|{page}|{user_id}"))
nav = list()
if page > 0:
nav.append(InlineKeyboardButton("⬅️", callback_data=f"p|{page - 1}|{user_id}"))
if page < total_pages - 1:
nav.append(InlineKeyboardButton("➡️", callback_data=f"p|{page + 1}|{user_id}"))
if nav:
kb.row(*nav)
kb.row(InlineKeyboardButton("🔙 В шкаф", callback_data=f"s|{user_id}"))
return kb
@bot.message_handler(commands=list(("start", "game", "chest", "case")))
def cmd_menu(message):
user = message.from_user
if message.chat.type != "private":
try:
bot.delete_message(message.chat.id, message.message_id)
except Exception:
pass
coins, _, _, _ = get_user(user)
bot.send_message(message.chat.id, get_menu_text(user.first_name, coins), reply_markup=main_menu_kb(user.id))
@bot.message_handler(commands=list(("rich",)))
def cmd_rich(message):
user = message.from_user
if is_admin(user):
_, cards, last_daily, last_work = get_user(user)
save_user(user, 99999, cards, last_daily, last_work)
bot.reply_to(message, "💰 Админ-баланс: 99999 🪙")
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
elif action == "i":
try:
bot.edit_message_text(get_info_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=back_kb(owner_id))
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
status_text = "🆕 НОВАЯ!" if is_new else f"♻️ Дубль (x{cards[card_id]})"
emoji = RARITY_EMOJI[rarity]
bot.edit_message_text(
f"{case['name']} | {status_text}\n"
f"{emoji} {rarity}: {card['name']}\n"
f"{card['desc']}\n"
f"💰 Баланс: {new_coins} 🪙",
chat_id=call.message.chat.id,
message_id=call.message.message_id,
reply_markup=after_open_kb(case_key, owner_id),
)
elif action == "s":
coins, cards, _, _ = get_user(user)
total_cards = sum(len(group) for group in CARDS.values())
opened_count = len(cards)
lines = list()
lines.append(f"🗄 Шкаф {user.first_name} ({opened_count}/{total_cards}) | 💰 {coins} 🪙\n")
if opened_count == 0:
lines.append("Пока пусто — открой первый кейс!")
else:
for rarity in RARITY_ORDER:
emoji = RARITY_EMOJI[rarity]
opened_in_rarity = list()
for card in CARDS[rarity]:
count = cards.get(card["id"], 0)
if count > 0:
opened_in_rarity.append(f"{card['name']} (x{count})")
if opened_in_rarity:
lines.append(f"{emoji} {rarity}: " + ", ".join(opened_in_rarity))
bot.edit_message_text("\n".join(lines), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=shelf_kb(owner_id))
elif action == "t":
page = int(parts.pop(0))
_, cards, _, _ = get_user(user)
if not cards:
bot.answer_callback_query(call.id, "🗄 Сначала выбей хотя бы одну субкультуру!", show_alert=True)
return
bot.edit_message_text(
"🏷 Выбор тега участника\nНажми на выбитую субкультуру, чтобы поставить её себе в тег в этом чате:",
chat_id=call.message.chat.id,
message_id=call.message.message_id,
reply_markup=tag_list_kb(cards, page, owner_id),
)
elif action == "g":
cid = parts.pop(0)
_, cards, _, _ = get_user(user)
if cid not in cards or cards[cid] <= 0:
bot.answer_callback_query(call.id, "❌ Эта карточка еще не открыта!", show_alert=True)
return
if call.message.chat.type == "private":
bot.answer_callback_query(call.id, "❌ Тег можно поставить только в общем чате!", show_alert=True)
return
_, name = find_card_info(cid)
tag_text = name[:16]
chat_id = call.message.chat.id
try:
member = bot.get_chat_member(chat_id, user.id)
if member.status == "creator":
bot.answer_callback_query(call.id, "👑 Владельцу чата бот не может менять тег — впиши его себе вручную в настройках админов!", show_alert=True)
return
if member.status != "administrator":
bot.promote_chat_member(chat_id, user.id, can_manage_chat=True)
bot.set_chat_administrator_custom_title(chat_id, user.id, tag_text)
bot.answer_callback_query(call.id, f"🏷 Готово! Твой новый тег в чате: {tag_text}", show_alert=True)
except Exception:
bot.answer_callback_query(call.id, "❌ Не вышло поставить тег. Проверь, что группа — супергруппа, а у бота включено право «Добавление админов»!", show_alert=True)
elif action == "p":
page = int(parts.pop(0))
coins, cards, _, _ = get_user(user)
if not cards:
bot.answer_callback_query(call.id, "🗄 В шкафу пока нет ни одной карточки!", show_alert=True)
return
bot.edit_message_text(
f"💸 Продажа карточек | 💰 {coins} 🪙\n"
f"Дубли идут по полной цене, последняя карта в коллекции — дешевле:",
chat_id=call.message.chat.id,
message_id=call.message.message_id,
reply_markup=sell_list_kb(cards, page, owner_id),
)
elif action == "c":
cid = parts.pop(0)
page = int(parts.pop(0))
coins, cards, last_daily, last_work = get_user(user)
if cid not in cards or cards[cid] <= 0:
bot.answer_callback_query(call.id, "❌ Такой карточки уже нет!", show_alert=True)
return
rarity, name = find_card_info(cid)
count = cards[cid]
price = DUP_PRICES[rarity] if count > 1 else SINGLE_PRICES[rarity]
if count > 1:
cards[cid] = count - 1
else:
del cards[cid]
new_coins = 99999 if is_admin(user) else (coins + price)
save_user(user, new_coins, cards, last_daily, last_work)
bot.answer_callback_query(call.id, f"💸 Продано: {name} (+{price} 🪙)", show_alert=True)
if not cards:
bot.edit_message_text(get_menu_text(user.first_name, new_coins), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu_kb(owner_id))
else:
bot.edit_message_text(
f"💸 Продажа карточек | 💰 {new_coins} 🪙\n"
f"Дубли идут по полной цене, последняя карта в коллекции — дешевле:",
chat_id=call.message.chat.id,
message_id=call.message.message_id,
reply_markup=sell_list_kb(cards, page, owner_id),
)
elif action == "x":
coins, cards, last_daily, last_work = get_user(user)
sold_count = 0
earned = 0
for card_id, count in list(cards.items()):
if count > 1:
dups = count - 1
rarity, _ = find_card_info(card_id)
earned += dups * DUP_PRICES.get(rarity, 5)
sold_count += dups
cards[card_id] = 1
if sold_count == 0:
bot.answer_callback_query(call.id, "♻️ Повторок нет! Если хочешь продать обычную карту, нажми «💸 Продать карту» в шкафу.", show_alert=True)
return
new_coins = 99999 if is_admin(user) else (coins + earned)
save_user(user, new_coins, cards, last_daily, last_work)
bot.answer_callback_query(call.id, f"♻️ Продано повторок: {sold_count} шт. (+{earned} 🪙)", show_alert=True)
try:
bot.edit_message_text(get_menu_text(user.first_name, new_coins), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu_kb(owner_id))
except Exception:
pass
elif action == "d":
coins, cards, last_daily, last_work = get_user(user)
now = int(time.time())
if now - last_daily < DAILY_COOLDOWN:
left_hours = round((DAILY_COOLDOWN - (now - last_daily)) / 3600, 1)
bot.answer_callback_query(call.id, f"⏳ Бонус уже получен! Приходи через {left_hours} ч.", show_alert=True)
return
new_coins = 99999 if is_admin(user) else (coins + DAILY_BONUS)
save_user(user, new_coins, cards, now, last_work)
bot.answer_callback_query(call.id, f"🎁 +{DAILY_BONUS} 🪙! Баланс: {new_coins} 🪙.", show_alert=True)
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
bot.answer_callback_query(call.id, f"⏳ Отдохни еще {wait_str}", show_alert=True)
return
earned = random.randint(15, 25)
event = random.choice(WORK_EVENTS)
new_coins = 99999 if is_admin(user) else (coins + earned)
save_user(user, new_coins, cards, last_daily, now)
bot.answer_callback_query(call.id, f"🎸 {event}!\n+{earned} 🪙", show_alert=True)
try:
bot.edit_message_text(get_menu_text(user.first_name, new_coins), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu_kb(owner_id))
except Exception:
pass
if name == "main":
bot.remove_webhook()
bot.infinity_polling(skip_pending=True)

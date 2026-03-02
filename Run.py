import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8641739870:AAFDcXh2mBnslqkb3usC80u7nEUJx1njkoI'  # <-- Вставьте токен

AURELIA_CALENDAR = [
    {"name": "Хлад", "days": 31, "season": "Сезон Застывших Вод"},
    {"name": "Вьюг", "days": 28, "season": "Сезон Застывших Вод"},
    {"name": "Таль", "days": 31, "season": "Сезон Пробуждения"},
    {"name": "Капель", "days": 31, "season": "Сезон Пробуждения"},
    {"name": "Цвет", "days": 31, "season": "Сезон Пробуждения"},
    {"name": "Свет", "days": 31, "season": "Сезон Высокого Солнца"},
    {"name": "Зной", "days": 31, "season": "Сезон Высокого Солнца"},
    {"name": "Гроза", "days": 31, "season": "Сезон Очищения"},
    {"name": "Злато", "days": 31, "season": "Сезон Угасания"},
    {"name": "Мгла", "days": 31, "season": "Сезон Угасания"},
    {"name": "Иней", "days": 31, "season": "Сезон Угасания"},
]

# 5 реальных дней (432 000 сек) делим на 338 игровых дней
SECONDS_PER_GAME_DAY = 1 / 338 
DB_FILE = "calendar_data.json"

# --- ЛОГИКА ---

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Глобальное состояние
state = {
    "year": 2061,
    "month_idx": 0, 
    "day": 1,
    "running": False,
    "channel_id": None,
    "thread_id": None  # <--- Поддержка ТЕМ (Topics)
}

def load_data():
    global state
    try:
        with open(DB_FILE, "r") as f:
            saved_data = json.load(f)
            state.update(saved_data)
    except FileNotFoundError:
        save_data()

def save_data():
    with open(DB_FILE, "w") as f:
        json.dump(state, f)

def get_current_date_str():
    month_info = AURELIA_CALENDAR[state["month_idx"]]
    return (f"📅 **{state['day']} {month_info['name']}**\n"
            f"🍂 {month_info['season']}\n"
            f"📜 Год: {state['year']}")

def get_time_left_str():
    # Считаем сколько дней в году всего и сколько уже прошло
    total_days_in_year = sum(m["days"] for m in AURELIA_CALENDAR)
    days_passed = sum(AURELIA_CALENDAR[i]["days"] for i in range(state["month_idx"])) + state["day"]
    days_left = total_days_in_year - days_passed
    
    # Переводим оставшиеся игровые дни в реальные секунды
    seconds_left = days_left * SECONDS_PER_GAME_DAY
    
    real_days = int(seconds_left // 86400)
    real_hours = int((seconds_left % 86400) // 3600)
    real_minutes = int((seconds_left % 3600) // 60)
    
    return f"⏳ До смены года:\n{real_days} дн. {real_hours} ч. {real_minutes} мин."

def get_admin_keyboard():
    status = "🟢 ИДЕТ" if state["running"] else "🔴 СТОП"
    kb = [
        [InlineKeyboardButton(text=f"Статус: {status}", callback_data="ignore")],
        [
            InlineKeyboardButton(text="▶️ Старт", callback_data="cmd_start_time"),
            InlineKeyboardButton(text="⏸ Стоп", callback_data="cmd_stop_time")
        ],
        [InlineKeyboardButton(text="📢 Назначить ЭТОТ чат/тему", callback_data="cmd_set_channel")],
        [InlineKeyboardButton(text="⏩ +1 день", callback_data="cmd_skip_day")],
        [InlineKeyboardButton(text="⏳ Сколько до Нового Года?", callback_data="cmd_time_left")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ЦИКЛ ВРЕМЕНИ ---

async def time_loop():
    while True:
        if state["running"]:
            await asyncio.sleep(SECONDS_PER_GAME_DAY)
            if state["running"]:
                await advance_day()
        else:
            await asyncio.sleep(5)

async def advance_day():
    month_info = AURELIA_CALENDAR[state["month_idx"]]
    state["day"] += 1
    
    if state["day"] > month_info["days"]:
        state["day"] = 1
        state["month_idx"] += 1
        if state["month_idx"] >= len(AURELIA_CALENDAR):
            state["month_idx"] = 0
            state["year"] += 1
            
    save_data()
    
    # Отправка уведомления
    if state["channel_id"]:
        try:
            current_month = AURELIA_CALENDAR[state['month_idx']]
            msg = (f"❤️ **Новый пенис в Аурелии!**\n\n"
                   f"📅 {state['day']} {current_month['name']}, {state['year']} год\n"
                   f"_{current_month['season']}_")
            
            if state.get("thread_id"):
                await bot.send_message(state["channel_id"], msg, message_thread_id=state["thread_id"], parse_mode="Markdown")
            else:
                await bot.send_message(state["channel_id"], msg, parse_mode="Markdown")
                
        except Exception as e:
            logging.error(f"Ошибка отправки: {e}")

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("panel"))
async def cmd_panel(message: types.Message):
    await message.answer(
        f"⚙️ **Календарь Аурелии**\n\n{get_current_date_str()}", 
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "cmd_start_time")
async def btn_start(callback: CallbackQuery):
    state["running"] = True
    save_data()
    await callback.message.edit_text(
        f"⚙️ **Календарь Аурелии**\n\n{get_current_date_str()}",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("Время пошло!")

@dp.callback_query(F.data == "cmd_stop_time")
async def btn_stop(callback: CallbackQuery):
    state["running"] = False
    save_data()
    await callback.message.edit_text(
        f"⚙️ **Календарь Аурелии**\n\n{get_current_date_str()}",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("Пауза.")

@dp.callback_query(F.data == "cmd_set_channel")
async def btn_set_channel(callback: CallbackQuery):
    state["channel_id"] = callback.message.chat.id
    state["thread_id"] = callback.message.message_thread_id
    
    save_data()
    await callback.answer("Канал и тема привязаны!")
    
    msg_text = "✅ Даты будут приходить сюда."
    if state["thread_id"]:
        await bot.send_message(state["channel_id"], msg_text, message_thread_id=state["thread_id"])
    else:
        await bot.send_message(state["channel_id"], msg_text)

@dp.callback_query(F.data == "cmd_skip_day")
async def btn_skip(callback: CallbackQuery):
    await advance_day()
    await callback.message.edit_text(
        f"⚙️ **Календарь Аурелии**\n\n{get_current_date_str()}",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("День пропущен.")

@dp.callback_query(F.data == "cmd_time_left")
async def btn_time_left(callback: CallbackQuery):
    # Показываем уведомление (alert) с оставшимся временем
    await callback.answer(get_time_left_str(), show_alert=True)

@dp.callback_query(F.data == "ignore")
async def btn_ignore(callback: CallbackQuery):
    await callback.answer()

async def main():
    load_data()
    asyncio.create_task(time_loop())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

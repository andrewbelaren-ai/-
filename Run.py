import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8641739870:AAFDcXh2mBnslqkb3usC80u7nEUJx1njkoI'  # <-- Вставьте токен сюда

# Названия месяцев и количество дней
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

# Расчет скорости времени
# 1 игровой месяц = 2 реальных дня (48 часов)
# Средний месяц ~30.7 дней.
# 48 часов * 3600 секунд / 30.7 = ~5628 секунд на 1 игровой день.
# Для тестов ставьте число ниже (например, 10 секунд).
SECONDS_PER_GAME_DAY = 0.5

# Файл для сохранения прогресса
DB_FILE = "calendar_data.json"

# --- ЛОГИКА ---

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Глобальное состояние
state = {
    "year": 2061,   # <--- ИЗМЕНЕНО: Стартовый год 2061
    "month_idx": 0, # 0 = Хлад
    "day": 1,
    "running": False,
    "channel_id": None
}

def load_data():
    global state
    try:
        with open(DB_FILE, "r") as f:
            saved_data = json.load(f)
            # Обновляем состояние, если файл существует
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

# Клавиатура управления
def get_admin_keyboard():
    status = "🟢 ИДЕТ" if state["running"] else "🔴 СТОП"
    kb = [
        [InlineKeyboardButton(text=f"Статус: {status}", callback_data="ignore")],
        [
            InlineKeyboardButton(text="▶️ Старт", callback_data="cmd_start_time"),
            InlineKeyboardButton(text="⏸ Стоп", callback_data="cmd_stop_time")
        ],
        [InlineKeyboardButton(text="📢 Назначить этот канал", callback_data="cmd_set_channel")],
        [InlineKeyboardButton(text="⏩ +1 день", callback_data="cmd_skip_day")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ФУНКЦИЯ ВРЕМЕНИ (ФОНОВАЯ ЗАДАЧА) ---

async def time_loop():
    while True:
        if state["running"]:
            await asyncio.sleep(SECONDS_PER_GAME_DAY)
            
            # Если бот все еще запущен после паузы
            if state["running"]:
                await advance_day()
        else:
            await asyncio.sleep(5) # Просто ждем, если таймер на паузе

async def advance_day():
    month_info = AURELIA_CALENDAR[state["month_idx"]]
    
    state["day"] += 1
    
    # Проверка конца месяца
    if state["day"] > month_info["days"]:
        state["day"] = 1
        state["month_idx"] += 1
        
        # Проверка конца года
        if state["month_idx"] >= len(AURELIA_CALENDAR):
            state["month_idx"] = 0
            state["year"] += 1
            
    save_data()
    
    # Отправка уведомления в канал
    if state["channel_id"]:
        try:
            current_month = AURELIA_CALENDAR[state['month_idx']]
            msg = (f"🌅 **Новый день в Аурелии!**\n\n"
                   f"📅 {state['day']} {current_month['name']}, {state['year']} год\n"
                   f"_{current_month['season']}_")
            await bot.send_message(state["channel_id"], msg, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение в канал: {e}")

# --- ОБРАБОТЧИКИ TELEGRAM ---

@dp.message(Command("panel"))
async def cmd_panel(message: types.Message):
    # Команда для вызова панели управления
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
    await callback.answer("Время запущено!")

@dp.callback_query(F.data == "cmd_stop_time")
async def btn_stop(callback: CallbackQuery):
    state["running"] = False
    save_data()
    await callback.message.edit_text(
        f"⚙️ **Календарь Аурелии**\n\n{get_current_date_str()}",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("Время остановлено.")

@dp.callback_query(F.data == "cmd_set_channel")
async def btn_set_channel(callback: CallbackQuery):
    state["channel_id"] = callback.message.chat.id
    save_data()
    await callback.answer("Канал привязан!")
    await bot.send_message(callback.message.chat.id, "✅ Канал установлен для уведомлений о датах.")

@dp.callback_query(F.data == "cmd_skip_day")
async def btn_skip(callback: CallbackQuery):
    await advance_day()
    # Обновляем текст сообщения
    await callback.message.edit_text(
        f"⚙️ **Календарь Аурелии**\n\n{get_current_date_str()}",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("День пропущен вручную.")

@dp.callback_query(F.data == "ignore")
async def btn_ignore(callback: CallbackQuery):
    await callback.answer()

async def main():
    load_data()
    # Запускаем цикл времени параллельно с ботом
    asyncio.create_task(time_loop())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

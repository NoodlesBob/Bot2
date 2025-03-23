import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = "YOUR_BOT_TOKEN"
HIDDEN_CHANNEL_ID = -1002570163026  # ID прихованого каналу
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)

class EditState(StatesGroup):
    waiting_for_new_text = State()

pending_messages = {}

INSTRUCTION_TEXT = (
    "📋 <b>Інструкція з використання бота:</b>\n\n"
    "🔹 <b>Куди потрапляє новина:</b> Ваші новини можуть бути опубліковані у каналі ChatGPT Ukraine.\n"
    "1️⃣ Надішліть текст, фото, відео або документ, щоб запропонувати свою новину.\n"
    "2️⃣ Адміністратор розгляне вашу пропозицію та вирішить, чи публікувати її.\n"
    "3️⃣ Якщо новина затверджена, вона буде опублікована у каналі.\n\n"
    "📌 <b>Правила:</b>\n"
    "- Максимальний обсяг новини — 1000 знаків. Якщо текст довший, він буде розміщений у кількох повідомленнях.\n"
    "- Форматування (жирний, курсив) та анкори не збережуться.\n"
    "- Посилання надсилайте у вигляді тексту (наприклад, https://example.com).\n\n"
    "🔒 <b>Ваше ім'я буде анонімним.</b> Якщо хочете, щоб вас згадали, додайте своє ім'я у тексті.\n\n"
    "🛠 <b>Основні команди:</b>\n"
    "/start - Привітання та інструкція\n"
    "/help - Опис системи тригерів\n"
)

@dp.message(commands=['start'])
async def start(message: types.Message):
    await message.answer(
        "👋 <b>Вітаємо у боті ChatGPT Ukraine!</b>\n\n" + INSTRUCTION_TEXT,
        parse_mode="HTML",
        reply_markup=get_edit_keyboard()
    )

@dp.message(commands=['help'])
async def help_command(message: types.Message):
    await message.answer(
        "🛠 <b>Як користуватися ботом:</b>\n\n" + INSTRUCTION_TEXT,
        parse_mode="HTML"
    )

def get_edit_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редагувати новину", callback_data="edit")
    return builder.as_markup()

@dp.callback_query(lambda c: c.data == 'edit')
async def edit_news(callback: types.CallbackQuery):
    await callback.message.answer("✍️ Введи новий текст для новини:")
    await dp.storage.set_state(callback.from_user.id, EditState.waiting_for_new_text)

@dp.message(EditState.waiting_for_new_text)
async def save_edited_news(message: types.Message, state):
    pending_messages[message.chat.id] = message.text
    await message.answer("✅ Новину відредаговано!")
    await state.clear()

async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("🚀 Бот запущено!")

async def on_shutdown():
    await bot.session.close()
    logging.info("🛑 Бот зупинено.")

if __name__ == "__main__":
    try:
        asyncio.run(dp.start_polling(bot, on_startup=on_startup, on_shutdown=on_shutdown))
    except (KeyboardInterrupt, SystemExit):
        logging.error("❌ Бот зупинено вручну.")

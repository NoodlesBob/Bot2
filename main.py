import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.bot import DefaultBotProperties
from flask import Flask
import threading
import os

# Логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфігурація
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Токен бота
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # ID адміністратора
HIDDEN_CHANNEL_ID = -1002570163026  # ID вашого каналу

# Ініціалізація бота
bot = Bot(
    token=BOT_TOKEN,
    session=AiohttpSession(),
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# Flask сервер для підтримки роботи порту
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=5000)

# Текст, який додається до кожного повідомлення
FOOTER_TEXT = "\n\n📩 <b><a href='https://t.me/НазваВашогоБота'>Надіслати Новину</a></b>"

# Інструкція для бота
INSTRUCTION_TEXT = (
    "📋 <b>Інструкція з використання бота:</b>\n\n"
    "🔹 <b>Куди потрапляє новина:</b> Ваші новини можуть бути опубліковані у каналі ChatGPT Ukraine.\n"
    "1️⃣ Надішліть текст, фото, відео або документ, щоб запропонувати свою новину.\n"
    "2️⃣ Адміністратор розгляне вашу пропозицію та вирішить, чи публікувати її.\n"
    "3️⃣ Якщо новина затверджена, вона буде опублікована у каналі.\n\n"
    "📌 <b>Правила:</b>\n"
    "- Максимальний обсяг новини — 1000 знаків. Якщо текст довший, він буде розділений на кілька повідомлень.\n"
    "- Форматування (жирний, курсив) та анкори не збережуться.\n"
    "- Посилання надсилайте у вигляді тексту (наприклад, https://example.com).\n\n"
    "🔒 <b>Ваше ім'я буде анонімним.</b> Якщо хочете, щоб вас згадали, додайте своє ім'я у тексті.\n\n"
    "🛠 <b>Основні команди:</b>\n"
    "/start - Привітання та інструкція\n"
    "/help - Опис системи тригерів\n"
)

# Кнопки для адміністратора
def generate_approve_keyboard(message_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Затвердити", callback_data=f"approve:{message_id}")],
            [InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject:{message_id}")],
            [InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit:{message_id}")]
        ]
    )

# Привітання при команді /start
@dp.message(Command("start"))
async def send_welcome(message: Message):
    await message.answer(
        "👋 <b>Вітаємо у боті ChatGPT Ukraine!</b>\n\n"
        + INSTRUCTION_TEXT,
        parse_mode="HTML"
    )

# Відображення інструкції при команді /help
@dp.message(Command("help"))
async def show_help(message: Message):
    await message.answer(
        "🛠 <b>Як користуватися ботом:</b>\n\n" + INSTRUCTION_TEXT,
        parse_mode="HTML"
    )

# Обробка новин від користувачів
@dp.message(F.content_type.in_({ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT}))
async def handle_news(message: Message):
    pending_messages = {}

    pending_messages[message.message_id] = {
        "message": message,
        "media_type": message.content_type,
        "file_id": (
            message.photo[-1].file_id if message.photo else
            message.video.file_id if message.video else
            message.document.file_id if message.document else None
        ),
        "caption": message.text or message.caption or "📩 Повідомлення без тексту"
    }

    # Перевірка довжини тексту
    if len(pending_messages[message.message_id]["caption"]) > 1000:
        await message.answer("⚠️ Текст новини перевищує 1000 знаків. Він буде розділений на кілька повідомлень.")
    else:
        await message.answer("✅ Твоя новина надіслана на модерацію!")

    try:
        admin_message = f"📝 Новина від @{message.from_user.username or 'аноніма'}:\n{pending_messages[message.message_id]['caption']}"
        if message.photo:
            await bot.send_photo(
                ADMIN_ID,
                photo=message.photo[-1].file_id,
                caption=admin_message,
                reply_markup=generate_approve_keyboard(message.message_id)
            )
        elif message.video:
            await bot.send_video(
                ADMIN_ID,
                video=message.video.file_id,
                caption=admin_message,
                reply_markup=generate_approve_keyboard(message.message_id)
            )
        elif message.document:
            await bot.send_document(
                ADMIN_ID,
                document=message.document.file_id,
                caption=admin_message,
                reply_markup=generate_approve_keyboard(message.message_id)
            )
        else:
            await bot.send_message(
                ADMIN_ID,
                admin_message,
                reply_markup=generate_approve_keyboard(message.message_id)
            )
    except Exception as e:
        logger.error(f"Помилка при відправці адміністратору: {e}")

# Основна функція бота
async def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

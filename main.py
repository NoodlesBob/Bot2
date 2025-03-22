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

# Список для зберігання новин, які очікують модерації
pending_messages = {}

# Інструкція
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

# Текст, який додається до кожного повідомлення
FOOTER_TEXT = "\n\n📩 <b><a href='https://t.me/НазваВашогоБота'>Надіслати Новину</a></b>"

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
    global pending_messages
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

# Затвердження новини
@dp.callback_query(F.data.startswith("approve"))
async def approve_news(callback: CallbackQuery):
    global pending_messages
    _, message_id = callback.data.split(":")
    message_data = pending_messages.pop(int(message_id), None)

    if message_data:
        try:
            if message_data["media_type"] == ContentType.PHOTO:
                await bot.send_photo(
                    HIDDEN_CHANNEL_ID,
                    photo=message_data["file_id"],
                    caption=message_data["caption"] + FOOTER_TEXT
                )
            elif message_data["media_type"] == ContentType.VIDEO:
                await bot.send_video(
                    HIDDEN_CHANNEL_ID,
                    video=message_data["file_id"],
                    caption=message_data["caption"] + FOOTER_TEXT
                )
            elif message_data["media_type"] == ContentType.DOCUMENT:
                await bot.send_document(
                    HIDDEN_CHANNEL_ID,
                    document=message_data["file_id"],
                    caption=message_data["caption"] + FOOTER_TEXT
                )
            else:
                await bot.send_message(
                    HIDDEN_CHANNEL_ID,
                    text=message_data["caption"] + FOOTER_TEXT
                )
            await callback.answer("✅ Новину опубліковано!")
        except Exception as e:
            logger.error(f"Помилка публікації новини: {e}")
            await callback.answer("❌ Помилка при публікації.")
    else:
        await callback.answer("❌ Новина не знайдена або вже оброблена!")

# Відхилення новини
@dp.callback_query(F.data.startswith("reject"))
async def reject_news(callback: CallbackQuery):
    global pending_messages
    _, message_id = callback.data.split(":")
    if pending_messages.pop(int(message_id), None):
        await callback.answer("❌ Новина відхилена.")
        await callback.message.edit_text("❌ Ця новина була відхилена.")
    else:
        await callback.answer("❌ Новина не знайдена або вже оброблена!")

# Редагування новини
@dp.callback_query(F.data.startswith("edit"))
async def edit_news(callback: CallbackQuery):
    global pending_messages
    _, message_id = callback.data.split(":")
    message_data = pending_messages.get(int(message_id))

    if message_data:
        await callback.message.answer("✏️ Введіть новий текст для новини. Медійний файл залишиться без змін.")

        @dp.message(F.text)
        async def handle_edit_response(new_message: Message):
            updated_text = new_message.text
            message_data

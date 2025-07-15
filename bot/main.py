import os
import uuid
import threading
import random
from datetime import datetime
import pytz
from dotenv import load_dotenv
from flask import Flask
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6434717615  # Replace with your Telegram ID

if not TOKEN:
    raise ValueError("BOT_TOKEN is not set in the .env file")

LANGUAGE, ASK_NAME, ASK_PHONE = range(3)
file_lock = threading.Lock()

# Flask to keep bot alive
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "USMON OTA bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    thread = threading.Thread(target=run_flask)
    thread.start()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("logo.jpg", "rb") as photo:
            await update.message.reply_photo(photo, caption="🎉 USMON OTA sovrinli o'yini botiga xush kelibsiz!")
    except FileNotFoundError:
        await update.message.reply_text("🎉 USMON OTA sovrinli o'yini botiga xush kelibsiz!")

    keyboard = [[KeyboardButton("🇺🇿 O'zbekcha"), KeyboardButton("🇷🇺 Русский")]]
    await update.message.reply_text(
        "Tilni tanlang / Выберите язык:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return LANGUAGE

# Language
async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "🇺🇿" in text or "O'zbek" in text:
        context.user_data["lang"] = "uz"
        await update.message.reply_text("Iltimos, ism va familiyangizni kiriting:", reply_markup=ReplyKeyboardRemove())
    elif "🇷🇺" in text:
        context.user_data["lang"] = "ru"
        await update.message.reply_text("Пожалуйста, введите ваше имя и фамилию:", reply_markup=ReplyKeyboardRemove())
    else:
        return LANGUAGE
    return ASK_NAME

# Name
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    contact_btn = KeyboardButton("📞 Raqamni yuborish / Отправить номер", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)

    if context.user_data["lang"] == "uz":
        await update.message.reply_text("Endi telefon raqamingizni yuboring:", reply_markup=markup)
    else:
        await update.message.reply_text("Теперь отправьте ваш номер телефона:", reply_markup=markup)
    return ASK_PHONE

# Phone
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    phone = contact.phone_number if contact else update.message.text
    name = context.user_data.get("name")
    lang = context.user_data.get("lang", "uz")
    code = f"USMON{str(uuid.uuid4())[:8].upper()}"

    tz = pytz.timezone("Asia/Tashkent")
    reg_date = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    try:
        with file_lock:
            with open("registrations.csv", "a", encoding='utf-8') as f:
                f.write(f"{update.effective_user.id},{name},{phone},{code},{reg_date}\n")
    except Exception as e:
        print(f"Error saving: {e}")

    msg = (
        f"✅ Siz ro'yxatdan o'tdingiz!\nSizning unikal kodingiz: *{code}*\n"
        "Ushbu kodni restoranda ko'rsating va sovrin yutish imkoniyatiga ega bo'ling! 🎁"
        if lang == "uz" else
        f"✅ Вы успешно зарегистрированы!\nВаш уникальный код: *{code}*\n"
        "Покажите этот код в ресторане и получите шанс выиграть приз! 🎁"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Jarayon bekor qilindi / Процесс отменен.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# /list
async def list_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda ruxsat yo'q.")
        return

    if not os.path.exists("registrations.csv"):
        await update.message.reply_text("⚠️ Ro'yxat hali yo'q.")
        return

    try:
        with open("registrations.csv", "r", encoding="utf-8") as f:
            lines = [line.strip().split(",") for line in f if line.strip()]
        if not lines:
            await update.message.reply_text("📭 Hozircha hech kim ro'yxatdan o'tmagan.")
            return

        pc_output = "No | Ism | Telefon | Kod | Sana\n"
        pc_output += "---|-----|---------|-----|-----\n"
        for i, (_, name, phone, code, date) in enumerate(lines, start=1):
            pc_output += f"{i} | {name} | {phone} | {code} | {date}\n"

        with open("list_pc.txt", "w", encoding="utf-8") as f:
            f.write(pc_output)

        mobile_output = ""
        for i, (_, name, phone, code, date) in enumerate(lines, start=1):
            mobile_output += (
                f"👤 {i}.\n"
                f"🧑‍💼 Ism: *{name}*\n"
                f"📞 Tel: `{phone}`\n"
                f"🆔 Kod: `{code}`\n"
                f"📅 Sana: {date}\n\n"
            )
        with open("list_mobile.txt", "w", encoding="utf-8") as f:
            f.write(mobile_output)

        with open("list_pc.txt", "rb") as doc1, open("list_mobile.txt", "rb") as doc2:
            await update.message.reply_document(doc1, filename="PC_format.txt", caption="🖥 PC version")
            await update.message.reply_document(doc2, filename="Mobile_format.txt", caption="📱 Mobile version")

        os.remove("list_pc.txt")
        os.remove("list_mobile.txt")

    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik yuz berdi: {str(e)}")

# /remove
async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda ruxsat yo'q.")
        return

    if not os.path.exists("registrations.csv"):
        await update.message.reply_text("⚠️ Ro'yxat topilmadi.")
        return

    if not context.args:
        await update.message.reply_text("🗑 Kodni yoki `all` yozing:\nMisol: `/remove USMONXXXX` yoki `/remove all`", parse_mode="Markdown")
        return

    target = context.args[0].strip().upper()

    try:
        with file_lock:
            with open("registrations.csv", "r", encoding="utf-8") as f:
                lines = f.readlines()

            if target == "ALL":
                os.remove("registrations.csv")
                await update.message.reply_text("✅ Barcha foydalanuvchilar o'chirildi.")
            else:
                new_lines = [line for line in lines if target not in line]
                if len(new_lines) == len(lines):
                    await update.message.reply_text("❌ Kod topilmadi.")
                else:
                    with open("registrations.csv", "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                    await update.message.reply_text(f"🗑 Kod `{target}` o'chirildi.", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {str(e)}")

# /winner
async def pick_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda ruxsat yo'q.")
        return

    if not os.path.exists("registrations.csv"):
        await update.message.reply_text("⚠️ Ro'yxat topilmadi.")
        return

    with file_lock:
        with open("registrations.csv", "r", encoding="utf-8") as f:
            lines = [line.strip().split(",") for line in f if line.strip()]

    if not lines:
        await update.message.reply_text("⚠️ Ro'yxatda hech kim yo'q.")
        return

    winner = random.choice(lines)
    _, name, phone, code, date = winner

    await update.message.reply_text(
        f"🎉 G'olib:\n\n"
        f"🧑‍💼 Ism: *{name}*\n"
        f"📞 Tel: `{phone}`\n"
        f"🆔 Kod: `{code}`\n"
        f"📅 Sana: {date}",
        parse_mode="Markdown"
    )

# Main
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASK_PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, get_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list", list_participants))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("winner", pick_winner))

    keep_alive()
    print("✅ Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()

import asyncio
import json
import logging
import os
from typing import Final, List

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters,
)

from .db_connection import close_db_pool, init_db_pool
from .send_anaylsis import send_image_analyze
from .user_data_handler import get_allergies, get_api_key, set_api_key, update_allergies

TELEGRAM_TOKEN: Final = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_USERNAME: Final = os.getenv("TELEGRAM_BOT_USERNAME")

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

if not TELEGRAM_TOKEN or not TELEGRAM_BOT_USERNAME:
    logger.error("TELEGRAM_TOKEN or TELEGRAM_BOT_USERNAME is not set")
    exit(1)

# Conversation states
SET_APIKEY_INPUT = 1
SET_ALLERGY_INPUT = 2

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_text = (
        "我是智能過敏菜單助理（AllergyMenu Assistant）\n"
        "是一個能幫助你快速判斷餐廳菜色是否含有過敏原的智慧助手。\n"
        "\n"
        "✨ 主要功能：\n"
        "上傳餐廳菜單圖片即可自動辨識文字（OCR）\n"
        "由 AI 分析每道菜可能含有的過敏原\n"
        "根據你個人的過敏資訊，分類成：\n"
        "✅ 可食用\n"
        "❌ 不可食用\n"
        "⚠️ 需注意\n"
        "\n"
        "🔄 過敏資訊可隨時設定與更新\n"
        "🗂 支援多重過敏源比對（如花生、乳製品、海鮮、蛋類等）\n"
        "\n"
        "🧠 本系統透過 OCR + LLM 組合分析，提供快速、直覺、個人化的菜單過敏判定。\n\n"
        "首先請您用 /setallergy 設定您的過敏原，\n"
        "並利用 /setapikey 設定您的 Gemini API Key，以處理您的請求"
    )

    await set_api_key(update.effective_user.id, None)
    await update_allergies(update.effective_user.id, [])

    await update.message.reply_text(
        f"{update.effective_user.first_name}，您好！\n\n{start_text}"
    )

# ---- SET APIKEY CONVERSATION ----

async def setapikey_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "請輸入您的 Gemini API Key\n\n輸入 /clear 清除 API Key\n輸入 /cancel 取消"
    )
    return SET_APIKEY_INPUT

async def setapikey_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    await set_api_key(update.effective_user.id, text)
    await update.message.reply_text("已成功設定 Gemini API Key")
    return ConversationHandler.END

async def setapikey_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_api_key(update.effective_user.id, None)
    await update.message.reply_text("已清除 Gemini API Key")
    return ConversationHandler.END

async def setapikey_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("已取消設定")
    return ConversationHandler.END

# ---- SET ALLERGY CONVERSATION ----

async def setallergy_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_allergies = await get_allergies(update.effective_user.id)
    await update.message.reply_text(
        "請輸入您對什麼過敏，以逗號(,)分隔\n"
        + (f"目前已設定過敏原:\n{'、'.join(user_allergies)}\n" if user_allergies else "")
        + "\n"
        "輸入 /cancel 取消\n"
        "輸入 /clear 清除"
    )
    return SET_ALLERGY_INPUT

async def handle_input_allergy_format(allergy: str):
    if allergy.strip():
        allergy_list = [
            allergy_item.strip()
            for allergy_item in allergy.split(",")
            if allergy_item.strip()
        ]
        return allergy_list
    else:
        raise ValueError

async def setallergy_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        allergies_list: List[str] = await handle_input_allergy_format(text)
        await update_allergies(update.effective_user.id, allergies_list)
        await update.message.reply_text(
            f"已成功設定過敏原：\n{'、'.join(allergies_list)}\n"
        )
        return ConversationHandler.END
    except ValueError:
        user_allergies = await get_allergies(update.effective_user.id)
        await update.message.reply_text(
            "不好意思，您輸入的格式不正確\n"
            "請輸入您對什麼過敏，以逗號(,)分隔\n"
            + (f"目前已設定過敏原:\n{'、'.join(user_allergies)}\n" if user_allergies else "")
            + "\n"
            "輸入 /cancel 取消\n"
            "輸入 /clear 清除"
        )
        return SET_ALLERGY_INPUT

async def setallergy_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update_allergies(update.effective_user.id, [])
    await update.message.reply_text("已清除過敏原")
    return ConversationHandler.END

async def setallergy_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("已取消設定")
    return ConversationHandler.END

# ---- END CONVERSATION ----

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "我是智能過敏菜單助理（AllergyMenu Assistant）\n"
        "是一個能幫助你快速判斷餐廳菜色是否含有過敏原的智慧助手。\n"
        "\n"
        "✨ 主要功能：\n"
        "上傳餐廳菜單圖片即可自動辨識文字（OCR）\n"
        "由 AI 分析每道菜可能含有的過敏原\n"
        "根據你個人的過敏資訊，分類成：\n"
        "✅ 可食用\n"
        "❌ 不可食用\n"
        "⚠️ 需注意\n"
        "\n"
        "🔄 過敏資訊可隨時設定與更新\n"
        "🗂 支援多重過敏源比對（如花生、乳製品、海鮮、蛋類等）\n"
        "\n"
        "🧠 本系統透過 OCR + LLM 組合分析，提供快速、直覺、個人化的菜單過敏判定。\n\n"
        "請您用 /setallergy 設定您的過敏原，\n"
        "並利用 /setapikey 設定您的 Gemini API Key，此API Key 會被加密儲存，並只用來處理您的請求，您可以隨時清除"
    )
    await update.message.reply_text(help_text)

async def dev_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_dict = json.dumps(update.to_dict(), indent=2)
    await update.message.reply_text(
        f"Hello, {update.effective_user.first_name}!\n\n{update_dict}\n\n{context.user_data}\n\n{context.chat_data}\n\n{context.bot_data}"
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    if message_type == "group":
        if TELEGRAM_BOT_USERNAME in text:
            text = text.replace(TELEGRAM_BOT_USERNAME, "")

    if text:
        await update.message.reply_text(text)

async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.photo[-1].file_id
    file = await context.bot.get_file(file_id)
    image = await file.download_as_bytearray()

    if await get_api_key(update.effective_user.id) is None:
        await update.message.reply_text("請先使用 /setapikey 指令設定 Gemini API Key")
        return

    reply_text = "已收到請求，請稍候..."
    allergic_list = await get_allergies(update.effective_user.id)

    if allergic_list:
        reply_text += (
            f"\n我會依據您的過敏原：（{'、'.join(allergic_list)}）給您餐點建議。"
        )
    else:
        reply_text += "\n(目前尚未設定過敏原，可以用 /setallergy 進行設定)"

    await update.message.reply_text(
        reply_text, reply_to_message_id=update.message.message_id
    )

    result = await send_image_analyze(
        image_bytes=image,
        allergic_list=allergic_list,
        platform_user_id=update.effective_user.id,
    )

    await update.message.reply_text(
        result, reply_to_message_id=update.message.message_id
    )

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")
    try:
        await update.message.reply_text(
            "Sorry, something went wrong.\n"
            f"\n{context.error}",
            reply_to_message_id=update.message.message_id,
        )
    except Exception:
        pass

def main() -> None:
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .concurrent_updates(True)
        .post_init(init_db_pool)
        .post_shutdown(close_db_pool)
        .build()
    )

    # Conversation handler for /setapikey
    setapikey_conv = ConversationHandler(
        entry_points=[CommandHandler("setapikey", setapikey_command_entry)],
        states={
            SET_APIKEY_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, setapikey_receive
                ),
                CommandHandler("clear", setapikey_clear),
                CommandHandler("cancel", setapikey_cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", setapikey_cancel)],
    )
    application.add_handler(setapikey_conv)

    # Conversation handler for /setallergy
    setallergy_conv = ConversationHandler(
        entry_points=[CommandHandler("setallergy", setallergy_command_entry)],
        states={
            SET_ALLERGY_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, setallergy_receive
                ),
                CommandHandler("clear", setallergy_clear),
                CommandHandler("cancel", setallergy_cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", setallergy_cancel)],
    )
    application.add_handler(setallergy_conv)

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("dev", dev_command))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )
    application.add_handler(
        MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_image_message)
    )
    application.add_error_handler(error)

    logging.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

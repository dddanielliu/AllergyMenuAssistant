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
    filters,
)

from .db_connection import close_db_pool, init_db_pool
from .send_anaylsis import send_image_analyze
from .user_data_handler import get_allergies, set_api_key, get_api_key, update_allergies

TELEGRAM_TOKEN: Final = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_USERNAME: Final = os.getenv("TELEGRAM_BOT_USERNAME")

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


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
        "🧠 本系統透過 OCR + LLM 組合分析，提供快速、直覺、個人化的菜單過敏判定。"
    )

    await set_api_key(update.effective_user.id, None)
    await update_allergies(update.effective_user.id, [])

    await update.message.reply_text(
        f"{update.effective_user.first_name}，您好！\n\n{start_text}"
    )


async def dev_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_dict = json.dumps(update.to_dict(), indent=2)
    await update.message.reply_text(
        f"Hello, {update.effective_user.first_name}!\n\n{update_dict}\n\n{context.user_data}\n\n{context.chat_data}\n\n{context.bot_data}"
    )


async def setapitoken_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["in_command"] = "setapitoken_command"
    await update.message.reply_text(
        "請輸入您的 Gemini API Key\n\n輸入 /clear 清除 API Key\n輸入 /cancel 取消"
    )


async def setallergy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["in_command"] = "setallergy_command"
    if update.effective_user.id:
        user_allergies = await get_allergies(update.effective_user.id)
        await update.message.reply_text(
            "請輸入您對什麼過敏，以逗號(,)分隔\n"
            + (
                f"目前已設定過敏原:\n{'、'.join(user_allergies)}\n"
                if user_allergies
                else ""
            )
            + "\n"
            "輸入 /cancel 取消\n"
            "輸入 /clear 清除"
        )


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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Help!")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("in_command"):
        context.user_data["in_command"] == "setapitoken_command"
        await set_api_key(update.effective_user.id, None)
        await update.message.reply_text("已清除 Gemini API Key")
    elif context.user_data.get("in_command"):
        context.user_data["in_command"] == "setallergy_command"
        await update_allergies(update.effective_user.id, [])
        await update.message.reply_text("已清除過敏原")
    context.user_data["in_command"] = None


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["in_command"] = None


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    if message_type == "group":
        if TELEGRAM_BOT_USERNAME in text:
            text = text.replace(TELEGRAM_BOT_USERNAME, "")

    if context.user_data.get("in_command"):
        if context.user_data["in_command"] == "setapitoken_command":
            context.user_data["in_command"] = None
            await set_api_key(update.effective_user.id, text.strip())
            await update.message.reply_text("已成功設定 Gemini API Key")
        elif context.user_data["in_command"] == "setallergy_command":
            try:
                allergies_list: List[str] = await handle_input_allergy_format(text)
                await update_allergies(update.effective_user.id, allergies_list)
                await update.message.reply_text(
                    f"已成功設定過敏原：\n{'、'.join(allergies_list)}\n"
                )
                context.user_data["in_command"] = None
            except ValueError:
                user_allergies = await get_allergies(update.effective_user.id)
                await update.message.reply_text(
                    "不好意思，您輸入的格式不正確\n"
                    "請輸入您對什麼過敏，以逗號(,)分隔\n"
                    + (
                        f"目前已設定過敏原:\n{'、'.join(user_allergies)}\n"
                        if user_allergies
                        else ""
                    )
                    + "\n"
                    "輸入 /cancel 取消\n"
                    "輸入 /clear 清除"
                )
        return

    if text:
        await update.message.reply_text(text)


async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.photo[-1].file_id
    # fetch photo
    file = await context.bot.get_file(file_id)

    # save to python bytes
    image = await file.download_as_bytearray()

    if await get_api_key(update.effective_user.id) is None:
        await update.message.reply_text("請先使用 /setapitoken 指令設定 Gemini API Key")
        return

    result = await send_image_analyze(
        image_bytes=image,
        allergic_list=await get_allergies(update.effective_user.id),
        platform_user_id=update.effective_user.id
    )

    await update.message.reply_text(
        result, reply_to_message_id=update.message.message_id
    )


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")
    try:
        await update.message.reply_text(
            "Sorry, something went wrong.\n"
            f"Update \n{update} \n\ncaused error\n{context.error}",
            reply_to_message_id=update.message.message_id,
        )
    except Exception:
        pass


def main() -> None:
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(init_db_pool)
        .post_shutdown(close_db_pool)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("dev", dev_command))
    application.add_handler(CommandHandler("setapitoken", setapitoken_command))
    application.add_handler(CommandHandler("setallergy", setallergy_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("help", help_command))

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

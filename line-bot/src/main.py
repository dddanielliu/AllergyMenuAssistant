import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage,
)
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
)

from .db_connection import close_db_pool, init_db_pool
from .send_anaylsis import send_image_analyze
from .user_data_handler import get_allergies, get_api_key, set_api_key, update_allergies

# Logging setup
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# LINE Bot configuration
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    logger.error("LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_SECRET is not set")
    exit(1)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

user_states = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()
    yield
    await close_db_pool()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try:
        handler.handle(body.decode(), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"


@handler.add(FollowEvent)
def handle_follow(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        welcome_message = (
            "我是智能過敏菜單助理（AllergyMenu Assistant）\n"
            "是一個能幫助你快速判断餐廳菜色是否含有過敏原的智慧助手。\n\n"
            "✨ 主要功能：\n"
            "上傳餐廳菜單圖片即可自動辨識文字（OCR）\n"
            "由 AI 分析每道菜可能含有的過敏原\n"
            "根據你個人的過敏資訊，分類成：\n"
            "✅ 可食用\n"
            "❌ 不可食用\n"
            "⚠️ 需注意\n\n"
            "🔄 過敏資訊可隨時設定與更新\n"
            "🗂 支援多重過敏源比對（如花生、乳製品、海鮮、蛋類等）\n\n"
            "🧠 本系統透過 OCR + LLM 組合分析，提供快速、直覺、個人化的菜單過敏判定。\n\n"
            "首先請您用 /setallergy 設定您的過敏原，\n"
            "並利用 /setapikey 設定您的 Gemini API Key，以處理您的請求"
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=welcome_message)],
            )
        )
        asyncio.run(set_api_key(event.source.user_id, None))
        asyncio.run(update_allergies(event.source.user_id, []))


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id

    if user_id in user_states:
        state = user_states.pop(user_id)
        if state == "setapikey":
            if text.lower() == "/cancel":
                reply_text = "已取消設定。"
            elif text.lower() == "/clear":
                asyncio.run(set_api_key(user_id, None))
                reply_text = "已清除 Gemini API Key。"
            else:
                asyncio.run(set_api_key(user_id, text))
                reply_text = "已成功設定 Gemini API Key。"
        elif state == "setallergy":
            if text.lower() == "/cancel":
                reply_text = "已取消設定。"
            elif text.lower() == "/clear":
                asyncio.run(update_allergies(user_id, []))
                reply_text = "已清除過敏原。"
            else:
                allergies = [a.strip() for a in text.split(",") if a.strip()]
                asyncio.run(update_allergies(user_id, allergies))
                reply_text = f"已成功設定過敏原：\n{', '.join(allergies)}"
    elif text.lower() == "/setapikey":
        user_states[user_id] = "setapikey"
        reply_text = "請輸入您的 Gemini API Key\n\n輸入 /clear 清除 API Key\n輸入 /cancel 取消"
    elif text.lower() == "/setallergy":
        user_states[user_id] = "setallergy"
        user_allergies = asyncio.run(get_allergies(user_id))
        reply_text = "請輸入您對什麼過敏，以逗號(,)分隔\n"
        if user_allergies:
            reply_text += f"目前已設定過敏原:\n{', '.join(user_allergies)}\n"
        reply_text += "輸入 /cancel 取消\n輸入 /clear 清除"
    elif text.lower() in ["/help", "/start"]:
        reply_text = (
            "我是智能過敏菜單助理（AllergyMenuAssistant）\n"
            "是一個能幫助你快速判断餐廳菜色是否含有過敏原的智慧助手。\n\n"
            "✨ 主要功能：\n"
            "上傳餐廳菜單圖片即可自動辨識文字（OCR）\n"
            "由 AI 分析每道菜可能含有的過敏原\n"
            "根據你個人的過敏資訊，分類成：\n"
            "✅ 可食用\n"
            "❌ 不可食用\n"
            "⚠️ 需注意\n\n"
            "🔄 過敏資訊可隨時設定與更新\n"
            "🗂 支援多重過敏源比對（如花生、乳製品、海鮮、蛋類等）\n\n"
            "🧠 本系統透過 OCR + LLM 組合分析，提供快速、直覺、個人化的菜單過敏判定。\n\n"
            "首先請您用 /setallergy 設定您的過敏原，\n"
            "並利用 /setapikey 設定您的 Gemini API Key，以處理您的請求"
        )
    else:
        reply_text = text

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)],
            )
        )

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    user_id = event.source.user_id
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        if asyncio.run(get_api_key(user_id)) is None:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="請先使用 /setapikey 指令設定 Gemini API Key")],
                )
            )
            return

        message_content = line_bot_api.get_message_content(message_id=event.message.id)
        image_bytes = message_content.read()

        allergic_list = asyncio.run(get_allergies(user_id))
        
        reply_text = "已收到請求，請稍候..."
        if allergic_list:
            reply_text += f"\n我會依據您的過敏原：（{', '.join(allergic_list)}）給您餐點建議。"
        else:
            reply_text += "\n(目前尚未設定過敏原，可以用 /setallergy 進行設定)"

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)],
            )
        )

        result = asyncio.run(send_image_analyze(
            image_bytes=image_bytes,
            allergic_list=allergic_list,
            platform_user_id=user_id,
        ))

        line_bot_api.push_message(user_id, messages=[TextMessage(text=result)])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
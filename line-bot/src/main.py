import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from linebot.v3.exceptions import InvalidSignatureError

# 3. Async Messaging API
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    ButtonsTemplate,
    Configuration,
    MessageAction,
    PushMessageRequest,
    ReplyMessageRequest,
    TemplateMessage,
    TextMessage,
)

# 1. Parsing & Validation
from linebot.v3.webhook import WebhookParser

# 2. Event Models
from linebot.v3.webhooks import (
    FollowEvent,
    ImageMessageContent,
    MessageEvent,
    TextMessageContent,
    UnfollowEvent,
)

from .db_connection import close_db_pool, init_db_pool
from .send_anaylsis import send_image_analyze
from .user_data_handler import (
    delete_user,
    get_allergies,
    get_api_key,
    set_api_key,
    update_allergies,
)

# Logging setup
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Configuration ---
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    logger.error("LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_SECRET is not set")
    sys.exit(1)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

# --- Globals (Initialized in lifespan) ---
# We cannot initialize these here because the Event Loop isn't running yet.
async_api_client = None
line_bot_api = None

# Parser is safe to init here (no async needed)
parser = WebhookParser(LINE_CHANNEL_SECRET)
user_states = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global async_api_client, line_bot_api

    # 1. Start DB
    await init_db_pool()

    # 2. Start Async LINE Client (Now the loop is running!)
    async_api_client = AsyncApiClient(configuration)
    line_bot_api = AsyncMessagingApi(async_api_client)

    yield

    # 3. Cleanup
    await close_db_pool()
    if async_api_client:
        await async_api_client.close()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    """
    Main Async Webhook Endpoint
    """
    if line_bot_api is None:
        raise HTTPException(status_code=503, detail="Service starting up")

    body = await request.body()
    body_str = body.decode("utf-8")

    try:
        # Validates signature and parses events
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle events asynchronously
    for event in events:
        await handle_event(event)

    return "OK"


async def handle_event(event):
    """
    Async Event Dispatcher
    """
    try:
        if isinstance(event, FollowEvent):
            await handle_follow(event)
        elif isinstance(event, UnfollowEvent):
            await handle_unfollow(event)
        elif isinstance(event, MessageEvent):
            if isinstance(event.message, TextMessageContent):
                await handle_text_message(event)
            elif isinstance(event.message, ImageMessageContent):
                await handle_image_message(event)
    except Exception as e:
        logger.error(f"Error handling event: {e}")


# --- Async Handlers ---


async def handle_follow(event):
    welcome_message = (
        "我是智能過敏菜單助理（AllergyMenu Assistant）\n"
        "是一個能幫助你快速判断餐廳菜色是否含有過敏原的智慧助手。\n\n"
        "✨ 主要功能：\n"
        "1. 上傳餐廳菜單圖片即可自動辨識文字（OCR）\n"
        "2. 由 AI 分析每道菜可能含有的過敏原\n"
        "3. 根據你個人的過敏資訊，分類成：\n"
        "✅ 可食用\n"
        "❌ 不可食用\n"
        "⚠️ 需注意\n\n"
        "首先請您用 /setallergy 設定您的過敏原，\n"
        "並利用 /setapikey 設定您的 Gemini API Key。"
    )

    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[
                TextMessage(text=welcome_message),
                TemplateMessage(
                    alt_text="快速功能選單",
                    template=ButtonsTemplate(
                        text="快速功能選單",
                        actions=[
                            MessageAction(label="/setallergy", text="/setallergy"),
                            MessageAction(label="/setapikey", text="/setapikey"),
                        ],
                    ),
                ),
            ],
        )
    )

    await set_api_key(event.source.user_id, None)
    await update_allergies(event.source.user_id, [])
    user_states.pop(event.source.user_id, None)


async def handle_text_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id
    reply_text = text

    # State Machine
    if user_id in user_states:
        state = user_states.pop(user_id)
        if state == "setapikey":
            if text.lower() == "/cancel":
                reply_text = "已取消設定。"
            elif text.lower() == "/clear":
                await set_api_key(user_id, None)
                reply_text = "已清除 Gemini API Key。"
            else:
                await set_api_key(user_id, text)
                reply_text = "已成功設定 Gemini API Key。"
        elif state == "setallergy":
            if text.lower() == "/cancel":
                reply_text = "已取消設定。"
            elif text.lower() == "/clear":
                await update_allergies(user_id, [])
                reply_text = "已清除過敏原。"
            else:
                allergies = [a.strip() for a in text.split(",") if a.strip()]
                await update_allergies(user_id, allergies)
                reply_text = f"已成功設定過敏原：\n{', '.join(allergies)}"

    # Commands
    elif text.lower() == "/setapikey":
        user_states[user_id] = "setapikey"
        reply_text = (
            "請輸入您的 Gemini API Key\n\n輸入 /clear 清除 API Key\n輸入 /cancel 取消"
        )

    elif text.lower() == "/setallergy":
        user_allergies = await get_allergies(user_id)
        user_states[user_id] = "setallergy"
        formatted_allergies = (
            f"目前已設定過敏原:\n{'、'.join(user_allergies)}\n"
            if user_allergies
            else ""
        )
        reply_text = (
            "請輸入您對什麼過敏，以逗號(,)分隔\n"
            f"{formatted_allergies}\n"
            "輸入 /cancel 取消\n"
            "輸入 /clear 清除"
        )

    elif text.lower() in ["/help", "/start"]:
        reply_text = (
            "我是智能過敏菜單助理（AllergyMenuAssistant）\n"
            "請輸入 /setallergy 設定您的過敏原，\n"
            "並利用 /setapikey 設定您的 Gemini API Key。"
        )

    # Buttons
    actions = []
    if "/setallergy" in reply_text:
        actions.append(MessageAction(label="/setallergy", text="/setallergy"))
    if "/setapikey" in reply_text:
        actions.append(MessageAction(label="/setapikey", text="/setapikey"))
    if "/cancel" in reply_text:
        actions.append(MessageAction(label="/cancel", text="/cancel"))
    if "/clear" in reply_text:
        actions.append(MessageAction(label="/clear", text="/clear"))

    messages_to_send = [TextMessage(text=reply_text)]
    if actions:
        messages_to_send.append(
            TemplateMessage(
                alt_text="快速功能選單",
                template=ButtonsTemplate(text="快速功能選單", actions=actions),
            )
        )

    await line_bot_api.reply_message(
        ReplyMessageRequest(reply_token=event.reply_token, messages=messages_to_send)
    )


async def handle_image_message(event):
    user_id = event.source.user_id
    message_id = event.message.id
    await _process_image_message(user_id, message_id, event.reply_token)


async def handle_unfollow(event):
    user_id = event.source.user_id
    await delete_user(user_id)
    user_states.pop(user_id, None)


async def _process_image_message(user_id, message_id, reply_token=None):
    api_key = await get_api_key(user_id)

    if api_key is None:
        await line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[
                    TextMessage(text="請先使用 /setapikey 指令設定 Gemini API Key"),
                    TemplateMessage(
                        alt_text="快速功能選單",
                        template=ButtonsTemplate(
                            text="快速功能選單",
                            actions=[
                                MessageAction(label="/setapikey", text="/setapikey")
                            ],
                        ),
                    ),
                ],
            )
        )
        return

    allergies_list = await get_allergies(user_id)
    reply_text = "已收到請求，請稍候..."
    if allergies_list:
        reply_text += (
            f"\n我會依據您的過敏原：({'、'.join(allergies_list)})給您餐點建議。"
        )
    else:
        reply_text += "\n(目前尚未設定過敏原，可以用 /setallergy 進行設定)"

    messages = [TextMessage(text=reply_text)]
    if "/setallergy" in reply_text:
        messages.append(
            TemplateMessage(
                alt_text="快速功能選單",
                template=ButtonsTemplate(
                    text="快速功能選單",
                    actions=[MessageAction(label="/setallergy", text="/setallergy")],
                ),
            )
        )

    await line_bot_api.reply_message(
        ReplyMessageRequest(reply_token=reply_token, messages=messages)
    )

    image_bytes = None
    try:
        # Fetch image content (returns bytes or iterator)
        message_content = await line_bot_api.get_message_content(message_id)

        if isinstance(message_content, bytes):
            image_bytes = message_content
        else:
            # If it's a response object, read it
            image_bytes = await message_content.read()

    except Exception as e:
        logger.warning(f"SDK fetch failed ({e}), falling back to direct HTTP")
        import aiohttp

        url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
        headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to fetch image: {resp.status}")
                    return
                image_bytes = await resp.read()

    result = await send_image_analyze(
        image_bytes=image_bytes,
        allergic_list=allergies_list,
        platform_user_id=user_id,
    )

    await line_bot_api.push_message(
        PushMessageRequest(to=user_id, messages=[TextMessage(text=result)])
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)

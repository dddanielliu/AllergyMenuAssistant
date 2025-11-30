import logging
from google import genai
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def call_llm1(menu_text: str, api_key: str):
    system_prompt = (
        "你是一個菜單解析助手。\n"
        "你的任務是從使用者上傳經過OCR處理的菜單文字中，提取所有菜名。\n\n"
        "要求："
        "1. 只輸出菜名列表，每個菜名單獨一行。\n"
        "2. 保留菜名完整原文，不要新增、簡化或翻譯，若OCR結果有誤但可以很明顯辨別菜名，請輸出更正的菜名。\n"
        "3. 不要輸出任何額外文字或說明。\n"
        "4. 如果文字中包含價格、份量、描述或調味說明，忽略這些，只保留菜名。"
    )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=menu_text,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.3,
        )
    )

    return response.text or ""


def call_llm2(cleaned_menu_text: str, api_key: str):
    system_prompt = (
        "你是一個菜單過敏原判定助手。\n"
        "你的任務是根據菜名，列出每道菜可能含有的過敏原。\n\n"
        "要求：\n"
        '1. 每一行先寫菜名，後接冒號 ":"，再列出該菜可能的過敏原。\n'
        '2. 過敏原用逗號 ", " 分隔。\n'
        "3. 每道菜獨立換行。\n"
        "4. 如果需要補充說明（例如部分食譜才有、調味料可能含），在過敏原後加一個空格，並將說明放在括號內。\n"
        "5. 僅輸出菜名與過敏原，不要添加任何其他文字或說明。\n"
        "6. 如果不確定過敏原，盡量列出所有可能來源。\n\n"
        "舉例輸出格式：\n"
        "麻婆豆腐: 大豆, 小麥, 芝麻, 牛肉, 花生 (醬料中可能含豆瓣醬、醬油、芝麻油，部分食譜會加牛肉末或花生)\n"
        "炒青菜: 大豆, 小麥 (若使用醬油調味)"
    )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=cleaned_menu_text,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.3,
        )
    )

    return response.text or ""


def call_llm3(llm2_response: str, allergic_list: List[str], api_key: str):
    system_prompt = (
        "你是一個專門處理過敏原判斷的助手。\n"
        "你的任務是根據使用者提供的過敏原與菜單過敏資訊，將菜分成三個區塊：\n"
        "✅ 可以吃：只列出完全沒有過敏原的菜名\n"
        "❌ 不能吃：列出含有使用者過敏原的菜，並簡單說明原因\n"
        "⚠️ 要注意：列出可能含過敏原的菜（例如部分食譜才會有，或調味料可能含），並簡單說明\n\n"
        "請僅輸出上述三個區塊的清單，每個區塊內使用清單（bullet points），不要添加其他任何多餘文字、表格、或自由發揮\n"
        "若無過敏原，請直接輸出清單以及每一項食物的過敏資訊，不分區塊\n"
        "若無菜單，請回答：'並未取得菜單資訊'\n"
    )
    allergic_list_str = ", ".join(allergic_list)

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            f"我的過敏原:{allergic_list_str}\n" f"菜單以及過敏資訊:\n{llm2_response}"
        ),
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.3,
        ),
    )

    return response.text or ""


def generate_response(menu_text: str, allergic_list: List[str], api_key: str, user_info: tuple[str, str]):
    # menu_text = "好吃店家。豬肉 牛肉蓋飯 麻婆豆腐"
    logging.info(f"[{user_info[0]}: {user_info[1]}] received allergic list:\n{allergic_list}\nmenu:\n{menu_text}")
    llm1_response = call_llm1(menu_text, api_key)
    logging.info(f"[{user_info[0]}: {user_info[1]}] LLM1:\n{llm1_response}")
    llm2_response = call_llm2(llm1_response, api_key)
    logging.info(f"[{user_info[0]}: {user_info[1]}] LLM2:\n{llm2_response}")
    llm3_response = call_llm3(llm2_response, allergic_list, api_key)
    logging.info(f"[{user_info[0]}: {user_info[1]}] LLM3:\n{llm3_response}")
    return llm3_response

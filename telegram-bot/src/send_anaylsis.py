import json
import os
from typing import List

import aiohttp
import asyncpg

PLATFORM = "telegram"


async def send_image_analyze(
    image_bytes: bytearray, allergic_list: List[str], platform_user_id: str
) -> str:
    url = "http://menu-analysis:8000/analyze"

    metadata = {
        "allergic_list": allergic_list,
        "platform": PLATFORM,
        "platform_user_id": platform_user_id,
    }

    result: dict | list | None = None
    async with aiohttp.ClientSession() as session:
        form = aiohttp.FormData()
        form.add_field(
            "file", image_bytes, filename="image.jpg", content_type="image/jpeg"
        )
        form.add_field(
            "metadata", json.dumps(metadata), content_type="application/json"
        )

        async with session.post(url, data=form) as resp:
            result = await resp.json()

    reply = result.get("llm_3_output", None)

    if not reply:
        raise Exception("No reply from LLM, result:\n" + str(result))
    return reply + f"\nFull result:\n{json.dumps(result, indent=2)}"

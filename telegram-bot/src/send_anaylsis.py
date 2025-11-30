import json
import logging
import os
from typing import List

import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
            if resp.status == 200:
                result = await resp.json()
            else:
                error_text = await resp.text()
                raise Exception(
                    f"Request failed with status code {resp.status}\n"
                    f"Response body: {error_text}"
                )
        try:
            async with session.post(url, data=form) as resp:
                # This raises aiohttp.ClientResponseError for 400+ status codes
                resp.raise_for_status()

                result = await resp.json()
                print(result)

        except aiohttp.ClientResponseError as e:
            logging.error(f"Request failed with status code: {e.status}\n{e.message}")
            raise Exception(f"Request failed with status code: {e.status}\n{e.message}")
        except Exception as e:
            logging.error(f"Request failed with unexpected error: {e}")
            raise Exception(f"Request failed with unexpected error: {e}")

    reply = result.get("llm_3_output", None)

    if not reply:
        raise Exception("No reply from LLM, result:\n" + str(result))

    logger.debug(json.dumps(result, indent=2))

    return reply

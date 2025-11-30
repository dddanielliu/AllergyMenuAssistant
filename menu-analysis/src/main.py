import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import List, Union

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from .db_connection import close_db_pool, init_db_pool
from .llm import generate_response
from .ocr import extract_raw_text
from .user_data_handler import get_api_key

# Use the provided logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()
    yield
    await close_db_pool()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze")
async def analyze_menu(file: UploadFile = File(...), metadata: str = Form(...)):
    """
    Analyzes a menu image for allergens.

    Accepts a multipart/form-data request with:
    - "file": The menu image.
    - "metadata": A JSON string containing a list of allergies.
      e.g., '{"allergic_list": ["peanuts", "shrimp"]}'
    """
    # The 'metadata' will be a JSON string, so we parse it.
    metadata_dict = json.loads(metadata)
    allergic_list = metadata_dict.get("allergic_list", [])

    # The 'file' is an UploadFile object. We can read its content.
    image_bytes = await file.read()

    platform = metadata_dict.get("platform")
    platform_user_id = str(metadata_dict.get("platform_user_id"))
    if not platform or not platform_user_id:
        raise ValueError("Missing platform or platform_user_id in metadata")

    # Get the user's API key from the database.
    api_key = await get_api_key(platform, platform_user_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No API key found."
        )

    raw_text = await asyncio.to_thread(extract_raw_text, image_bytes)
    raw_text = str(raw_text)

    metadata_dict["raw_text"] = raw_text
    # logger.info(f"Extracted raw text: \n{raw_text}")

    try:
        llms_response = await asyncio.to_thread(
            generate_response,
            raw_text,
            allergic_list,
            api_key,
            (platform, platform_user_id),
        )
    except Exception as e:
        logging.error(f"Failed to generate response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}",
        )

    response_dict = {
        "response": llms_response,
        "metadata": metadata_dict,
        "debug_info": {
            "received_allergies": allergic_list,
            "received_file_size": len(image_bytes),
            # "received_filename": file.filename,
            # "received_content_type": file.content_type,
        },
    }

    logger.info(f"Received analysis request with allergies: {allergic_list}")

    return response_dict


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

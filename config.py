"""config.py — Application configuration.

Provides LINE SDK objects and AI model wrappers used by main.py and
claim_engine.py.  Delegates to the shared Azure OpenAI client in ai/.
"""

import os
from dotenv import load_dotenv
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration

# Load environment variables
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

if not all([LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET]):
    raise ValueError("กรุณาตั้งค่า LINE Environment Variables ให้ครบถ้วน")

# LINE Configuration
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# AI model + genai wrappers — import from the shared ai/ module
from ai import get_model as _get_model, genai  # noqa: E402

gemini_model = _get_model()

# Backward-compat aliases used by main.py and tests
GEMINI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")

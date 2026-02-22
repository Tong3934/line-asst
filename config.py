import os
from dotenv import load_dotenv
import google.generativeai as genai
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration

# Load environment variables
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not all([LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, GEMINI_API_KEY]):
    raise ValueError("กรุณาตั้งค่า Environment Variables ให้ครบถ้วน")

# LINE Configuration
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Gemini Configuration
genai.configure(api_key=GEMINI_API_KEY)
# Using gemini-2.5-flash as requested in the latest main.py
gemini_model = genai.GenerativeModel(model_name='models/gemini-2.5-flash')

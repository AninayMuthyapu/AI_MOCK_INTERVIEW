"""
Application configuration: env vars, API keys, Gemini model setup, and safety settings.
"""
import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hackinterview")

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not set. "
        "Please create interview-backend/.env with GOOGLE_API_KEY=<your_key>."
    )

# Configure the Gemini client
genai.configure(api_key=API_KEY)

# Safety settings to prevent blocking
SAFETY_SETTINGS = [
    {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
    {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_NONE},
    {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_NONE},
    {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
]

# Initialize the Gemini model
model = genai.GenerativeModel('gemini-2.5-flash', safety_settings=SAFETY_SETTINGS)

# Static file directories
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
STATIC_OUTPUT_DIR = os.path.join(STATIC_DIR, "output")
os.makedirs(STATIC_OUTPUT_DIR, exist_ok=True)

# Trial period
TRIAL_DAYS = 20

# Posture analysis engine path
import sys
POSTURE_ENGINE_PATH = os.path.join(os.path.dirname(BASE_DIR), "Postureanalysis-main")
if os.path.isdir(POSTURE_ENGINE_PATH) and POSTURE_ENGINE_PATH not in sys.path:
    sys.path.insert(0, POSTURE_ENGINE_PATH)
    logger.info(f"Added Postureanalysis-main to sys.path: {POSTURE_ENGINE_PATH}")


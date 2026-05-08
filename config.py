import os
from dotenv import load_dotenv

load_dotenv()

# Server configuration
PORT = 5050
HOST = '0.0.0.0'
DEBUG = True
USE_HTTP = os.getenv("USE_HTTP", "False").lower() in ("true", "1", "yes")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MACOS_TRANSCRIBE_BIN = os.path.join(BASE_DIR, 'macos-transcribe/.build/arm64-apple-macosx/release/macos-transcribe')
FFMPEG_BIN = '/opt/homebrew/bin/ffmpeg'
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
CERT_DIR = os.path.join(BASE_DIR, 'certs')

# SSL Configuration
CERT_FILE = os.path.join(CERT_DIR, 'cert.pem')
KEY_FILE = os.path.join(CERT_DIR, 'key.pem')

# Voice mapping (OpenAI -> macOS)
VOICE_MAPPING = {
    'alloy': 'Alice (Enhanced)',
    'echo': 'Luca (Enhanced)',
    'nova': 'Emma (Premium)',
    'onyx': 'Fred',
    'shimmer': 'Zoe (Premium)',
    'fable': 'Samantha',
    'default': 'Alice'
}

# Language mapping for custom parameter (example)
LANG_VOICE_MAPPING = {
    'it': 'Alice (Enhanced)',
    'en': 'Samantha',
    'fr': 'Thomas',
    'de': 'Anna',
    'es': 'Monica'
}

# Supported formats
SUPPORTED_TTS_FORMATS = ['mp3', 'opus', 'aac', 'flac', 'wav', 'pcm']
SUPPORTED_STT_FORMATS = ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm']

# Ensure directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)


import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('TELEGRAM_CHANNEL_ID'))
ADMIN_CHAT_ID = int(os.getenv('TELEGRAM_ADMIN_CHAT_ID'))

DB_CONFIG = {
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": os.getenv('DB_NAME'),
    "host": os.getenv('DB_HOST'),
    "port": int(os.getenv('DB_PORT', 5432))
}

MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', '/var/www/uploads'))
IMAGE_DIR = Path(os.getenv('IMAGE_DIR', MEDIA_ROOT / 'img'))
VIDEO_DIR = Path(os.getenv('VIDEO_DIR', MEDIA_ROOT / 'video'))
AUDIO_DIR = Path(os.getenv('AUDIO_DIR', MEDIA_ROOT / 'audio'))
DOCUMENT_DIR = Path(os.getenv('DOCUMENT_DIR', MEDIA_ROOT / 'documents'))

WEBHOOK_HOST = os.getenv('WEBHOOK_HOST')
WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook/telegram')
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBHOOK_INTERVAL = int(os.getenv('WEBHOOK_INTERVAL', 1800))

API_HOST = os.getenv('API_HOST', '127.0.0.1')
API_PORT = int(os.getenv('API_PORT', 8000))

SSL_KEYFILE = os.getenv('SSL_KEYFILE')
SSL_CERTFILE = os.getenv('SSL_CERTFILE')

for directory in [MEDIA_ROOT, IMAGE_DIR, VIDEO_DIR, AUDIO_DIR, DOCUMENT_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

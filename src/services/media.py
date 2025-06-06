import asyncio
import aiofiles
from collections import defaultdict
from aiogram import Bot
from aiogram.types import Message
import logging
from pathlib import Path

from src.config import (
    IMAGE_DIR, 
    VIDEO_DIR, 
    AUDIO_DIR, 
    DOCUMENT_DIR
)

from src.database.models import save_message_to_db, save_media_group_to_db

media_groups: dict = defaultdict(list)
media_group_timers: dict = {}

class MediaProcessor:
    def __init__(self, bot: Bot, pool):
        self.bot = bot
        self.pool = pool
        self.logger = logging.getLogger(__name__)

    async def download_and_save_media(self, file_id: str, media_type: str, message_id: int):
        try:
            file_info = await self.bot.get_file(file_id)
            file_path = file_info.file_path

            # Определение директории и расширения
            directory, extension = self._get_media_directory_and_extension(media_type, file_path)
            
            filename = f"{message_id}_{media_type}.{extension}"
            filepath = directory / filename
            relative_path = f"uploads/{directory.name}/{filename}"

            # Скачивание файла
            file_content = await self.bot.download_file(file_path)
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(file_content.read())

            self.logger.info(f"📥 Сохранён файл: {relative_path}")
            return relative_path
        except Exception as e:
            self.logger.error(f"❌ Ошибка при скачивании файла {file_id}: {e}")
            return None

    def _get_media_directory_and_extension(self, media_type: str, file_path: str):
        if media_type == "photo":
            return IMAGE_DIR, "jpg"
        elif media_type == "video":
            return VIDEO_DIR, "mp4"
        elif media_type in ["audio", "voice"]:
            return AUDIO_DIR, "mp3"
        elif media_type == "document":
            extension = file_path.split(".")[-1] if "." in file_path else "file"
            return DOCUMENT_DIR, extension
        elif media_type == "animation":
            return VIDEO_DIR, "mp4"
        else:
            return None, None

    async def process_message_media(self, message: Message):
        content = message.text or message.caption or ""
        
        media_type = None
        file_id = None
        media_url = None

        # Определение типа медиа
        media_type, file_id = self._detect_media_type(message)

        if media_type and file_id:
            media_url = await self.download_and_save_media(file_id, media_type, message.message_id)

        # Обработка группового медиа
        if message.media_group_id:
            await self._process_media_group(message, content, media_type, media_url)
        else:
            await save_message_to_db(
                self.pool,
                message_id=message.message_id,
                text=content,
                media_type=media_type,
                media_url=media_url
            )

    def _detect_media_type(self, message: Message):
        media_mappings = [
            ("photo", lambda m: m.photo and m.photo[-1].file_id),
            ("video", lambda m: m.video and m.video.file_id),
            ("document", lambda m: m.document and m.document.file_id),
            ("audio", lambda m: m.audio and m.audio.file_id),
            ("voice", lambda m: m.voice and m.voice.file_id),
            ("animation", lambda m: m.animation and m.animation.file_id)
        ]

        for media_type, getter in media_mappings:
            file_id = getter(message)
            if file_id:
                return media_type, file_id
        
        return None, None

    async def _process_media_group(self, message: Message, content: str, media_type: str, media_url: str):
        media_groups[message.media_group_id].append({
            'message_id': message.message_id,
            'text': content,
            'media_type': media_type,
            'media_url': media_url
        })

        if message.media_group_id in media_group_timers:
            media_group_timers[message.media_group_id].cancel()

        async def delayed_process():
            await asyncio.sleep(2)
            await self._save_media_group(message.media_group_id)

        media_group_timers[message.media_group_id] = asyncio.create_task(delayed_process())

    async def _save_media_group(self, media_group_id: str):
        if media_group_id not in media_groups or not media_groups[media_group_id]:
            return

        messages = media_groups[media_group_id]
        main_message = messages[0]

        media_urls = []
        media_types = []
        all_texts = []

        for msg_data in messages:
            if msg_data['media_url']:
                media_urls.append(msg_data['media_url'])
                media_types.append(msg_data['media_type'])
            if msg_data['text']:
                all_texts.append(msg_data['text'])

        combined_text = ' '.join(all_texts) if all_texts else main_message['text']

        await save_media_group_to_db(
            self.pool,
            message_id=main_message['message_id'],
            text=combined_text,
            media_types=media_types,
            media_urls=media_urls,
            media_group_id=media_group_id
        )

        del media_groups[media_group_id]
        if media_group_id in media_group_timers:
            del media_group_timers[media_group_id]

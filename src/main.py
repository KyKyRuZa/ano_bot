import asyncio
import uvicorn
import asyncpg
import logging
import sys
import os

from fastapi import Request
from fastapi.staticfiles import StaticFiles
from aiogram import Bot, Dispatcher
from aiogram.types import Message, Update
from config import (
    API_TOKEN,MEDIA_ROOT,DB_CONFIG,
    WEBHOOK_PATH,API_HOST,API_PORT,SSL_KEYFILE,SSL_CERTFILE
)
from database.db import init_db
from api.api import app
from src.services.media import MediaProcessor
from src.hook.webhook import WebhookManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d.%m.%Y, %H:%M:%S"
)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

media_processor = MediaProcessor(bot, dp.pool) 

webhook_manager = WebhookManager(bot)

@app.post(WEBHOOK_PATH)
async def webhook_handler(request: Request):
    logger.debug("📥 Получен POST-запрос на вебхук")
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        logger.debug("📨 Апдейт передан диспетчеру")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке вебхука: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

async def start_api_server():
    try:
        if not os.path.exists(SSL_KEYFILE):
            logger.critical(f"❌ SSL ключ не найден: {SSL_KEYFILE}")
            raise FileNotFoundError(f"SSL key file not found at {SSL_KEYFILE}")
        if not os.path.exists(SSL_CERTFILE):
            logger.critical(f"❌ SSL сертификат не найден: {SSL_CERTFILE}")
            raise FileNotFoundError(f"SSL cert file not found at {SSL_CERTFILE}")
        config = uvicorn.Config(
            app,
            host=API_HOST,
            port=API_PORT,
            ssl_keyfile=SSL_KEYFILE,
            ssl_certfile=SSL_CERTFILE
        )
        server = uvicorn.Server(config)
        logger.info(f"🟢 API сервер запущен на https://{API_HOST}:{API_PORT}") 
        await server.serve()
    except Exception as e:
        logger.error(f"❌ Не удалось запустить API сервер: {e}")
        raise

async def keep_db_connection_alive(pool):
    while True:
        try:
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
            logger.debug("🔁 Соединение с БД активно")
        except Exception as e:
            logger.warning(f"⚠️ Проблема с БД: {e}. Пересоздание пула...")
            try:
                pool = await asyncpg.create_pool(**DB_CONFIG)
                dp.pool = pool
                logger.info("♻️ Пул БД пересоздан")
            except Exception as e:
                logger.error(f"❌ Не удалось пересоздать пул БД: {e}")
        await asyncio.sleep(1800)

app.mount("/uploads", StaticFiles(directory=str(MEDIA_ROOT)), name="uploads")

async def main():
    logger.info("🔄 Запуск бота и API сервера")
    dp.pool = None

    try:
        dp.pool = await asyncpg.create_pool(**DB_CONFIG, min_size=5, max_size=20)
        await init_db(dp.pool)
        logger.info("✅ Подключение к БД установлено")

        media_processor = MediaProcessor(bot, dp.pool)
        webhook_manager = WebhookManager(bot)


        dp.message.register(media_processor.process_message_media)
        dp.channel_post.register(media_processor.process_message_media)

        me = await bot.get_me()
        logger.info(f"🤖 Бот авторизован как @{me.username}")
        await webhook_manager.send_alert_to_admin(f"🟢 Бот запущен как @{me.username}")

        if not await webhook_manager.setup_webhook():
            logger.error("❌ Не удалось настроить вебхук")
            return

        asyncio.create_task(keep_db_connection_alive(dp.pool))
        asyncio.create_task(webhook_manager.monitor_webhook())
        
        logger.info("🟢 Запуск API сервера...")
        await start_api_server()

    except Exception as e:
        logger.critical(f"🔥 Критическая ошибка: {e}", exc_info=True)
        await webhook_manager.send_alert_to_admin(f"🔥 Критическая ошибка: {e}")
    
    finally:
        if dp.pool:
            await dp.pool.close()
        await bot.session.close()
        logger.info("🧹 Все ресурсы освобождены")


if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(main())
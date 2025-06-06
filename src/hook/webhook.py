import asyncio
import logging
from aiogram import Bot
from config import (
    WEBHOOK_URL, 
    WEBHOOK_PATH, 
    WEBHOOK_INTERVAL, 
    ADMIN_CHAT_ID
)

logger = logging.getLogger(__name__)

class WebhookManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    async def setup_webhook(self):
        """
        Настройка вебхука с Telegram
        """
        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
            self.logger.info("🧹 Старый вебхук удалён")

            await self.bot.set_webhook(
                url=WEBHOOK_URL,
                allowed_updates=None,  # Можно уточнить типы апдейтов
                drop_pending_updates=True
            )
            self.logger.info(f"✅ Вебхук установлен: {WEBHOOK_URL}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка при настройке вебхука: {e}", exc_info=True)
            return False

    async def monitor_webhook(self, interval=None):
        """
        Периодическая проверка состояния вебхука
        """
        interval = interval or WEBHOOK_INTERVAL
        while True:
            try:
                info = await self.bot.get_webhook_info()
                current_url = info.url
                
                if current_url != WEBHOOK_URL:
                    self.logger.warning(f"⚠️ Вебхук изменён: {current_url} ≠ {WEBHOOK_URL}")
                    success = await self.setup_webhook()
                    
                    if success:
                        self.logger.info("🔄 Вебхук восстановлен")
                        await self.send_alert_to_admin(f"🟢 Вебхук восстановлен: {WEBHOOK_URL}")
                    else:
                        self.logger.error("❌ Не удалось восстановить вебхук")
                else:
                    self.logger.debug(f"🔗 Вебхук корректен: {current_url}")
            
            except Exception as e:
                self.logger.error(f"❌ Ошибка при проверке вебхука: {e}", exc_info=True)
            
            await asyncio.sleep(interval)

    async def send_alert_to_admin(self, message_text):
        """
        Отправка уведомления администратору
        """
        try:
            await self.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_text)
        except Exception as e:
            self.logger.error(f"❌ Не удалось отправить уведомление: {e}")

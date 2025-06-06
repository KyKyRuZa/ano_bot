import json
import logging

logger = logging.getLogger(__name__)

async def save_message_to_db(pool, message_id, text, media_type=None, media_url=None):
    query = """
    INSERT INTO messages (message_id, text, media_type, media_url, timestamp)
    VALUES ($1, $2, $3, $4, NOW())
    RETURNING id;
    """
    
    try:
        async with pool.acquire() as conn:
            message_db_id = await conn.fetchval(
                query, message_id, text, media_type, media_url
            )
            logger.info(f"Сохранено сообщение {message_id} с ID {message_db_id}")
            return message_db_id
    except Exception as e:
        logger.error(f"Ошибка при сохранении сообщения {message_id}: {e}")
        raise

async def save_media_group_to_db(pool, message_id, text, media_types, media_urls, media_group_id):
    try:
        media_types_json = json.dumps(media_types) if media_types else None
        media_urls_json = json.dumps(media_urls) if media_urls else None
    except Exception as e:
        logger.error(f"Ошибка при сериализации медиа данных: {e}")
        media_types_json = None
        media_urls_json = None
    
    query = """
    INSERT INTO messages (message_id, text, media_type, media_url, media_group_id, timestamp)
    VALUES ($1, $2, $3, $4, $5, NOW())
    RETURNING id;
    """
    
    try:
        async with pool.acquire() as conn:
            message_db_id = await conn.fetchval(
                query, message_id, text, media_types_json, media_urls_json, media_group_id
            )
            logger.info(f"Сохранена группа медиа {media_group_id} с ID {message_db_id}")
            return message_db_id
    except Exception as e:
        logger.error(f"Ошибка при сохранении группы медиа {media_group_id}: {e}")
        raise

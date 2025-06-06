async def init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            message_id BIGINT NOT NULL,
            text TEXT,
            media_type TEXT,
            media_url TEXT,
            media_group_id VARCHAR(100),
            timestamp TIMESTAMP DEFAULT NOW()
        );
        ''')

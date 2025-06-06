from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import asyncpg
from typing import List, Optional, Union
from pydantic import BaseModel, validator
import config
from datetime import datetime
import json
import ssl
from src.config import (
    SSL_CERTFILE, 
    SSL_KEYFILE 
)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://anotsenimzhizn.ru"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=Path("media")), name="media")
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(**config.DB_CONFIG)

@app.on_event("shutdown")
async def shutdown():
    global pool
    if pool:
        await pool.close()

class Message(BaseModel):
    id: int
    message_id: int
    text: Optional[str] = None
    media_type: Optional[str] = None
    media_url: Optional[str] = None
    media_types: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    is_media_group: bool = False
    timestamp: str

    @validator('media_type', pre=True, always=True)
    def validate_media_type(cls, v):
        return v if v is not None else None

    @validator('media_url', pre=True, always=True)
    def validate_media_url(cls, v):
        return v if v is not None else None

    @validator('text', pre=True, always=True)
    def validate_text(cls, v):
        return v if v is not None else None

    class Config:
        from_attributes = True

@app.get("/apibot/messages", response_model=List[Message])
async def get_messages():
    global pool
    if not pool:
        pool = await asyncpg.create_pool(**config.DB_CONFIG)
        
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT id, message_id, text, media_type, media_url, media_group_id, timestamp
            FROM messages
            ORDER BY timestamp DESC
        ''')
        
        messages = []
        for row in rows:
            try:
                is_media_group = row["media_group_id"] is not None
                
                if is_media_group:
                    try:
                        media_types = json.loads(row["media_type"]) if row["media_type"] else []
                        media_urls = json.loads(row["media_url"]) if row["media_url"] else []
                    except (json.JSONDecodeError, TypeError):
                        media_types = [row["media_type"]] if row["media_type"] else []
                        media_urls = [row["media_url"]] if row["media_url"] else []
                    
                    message_data = {
                        "id": row["id"],
                        "message_id": row["message_id"],
                        "text": row["text"],
                        "media_type": None,
                        "media_url": None,
                        "media_types": media_types,
                        "media_urls": media_urls,
                        "is_media_group": True,
                        "timestamp": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else str(row["timestamp"])
                    }
                else:
                    message_data = {
                        "id": row["id"],
                        "message_id": row["message_id"],
                        "text": row["text"],
                        "media_type": row["media_type"],
                        "media_url": row["media_url"],
                        "media_types": None,
                        "media_urls": None,
                        "is_media_group": False,
                        "timestamp": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else str(row["timestamp"])
                    }
                
                messages.append(message_data)
                
            except Exception as e:
                print(f"Ошибка при обработке сообщения {row['id']}: {e}")
                continue
            
        return messages

def create_ssl_context():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        certfile=SSL_CERTFILE,
        keyfile=SSL_KEYFILE
    )
    return ssl_context

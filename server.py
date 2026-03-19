import os
import sqlite3
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hotel.db")

app = FastAPI(title="Forrest Hotel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Створюємо папку static, якщо її немає
if not os.path.exists(os.path.join(BASE_DIR, "static")):
    os.makedirs(os.path.join(BASE_DIR, "static"))

app.mount("/static", StaticFiles(directory="static"), name="static")

# ─────────────────────────────────────────────
# DB INIT (Створення таблиць при запуску)
# ─────────────────────────────────────────────

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_type TEXT,
                check_in TEXT,
                check_out TEXT,
                user_id INTEGER,
                guests INTEGER,
                name TEXT,
                phone TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS blocked_dates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_type TEXT,
                block_start TEXT,
                block_end TEXT,
                reason TEXT
            )
        """)
        conn.commit()

init_db()  # Викликаємо ініціалізацію відразу

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.get("/")
def root():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Server is running, but index.html not found in root"}

@app.get("/health")
def health():
    return {"status": "ok", "db_path": DB_PATH}

# Решта твоїх API методів (booking, availability і т.д.) залишаються без змін
# ... (твій попередній код API)

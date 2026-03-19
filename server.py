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
# НАЛАШТУВАННЯ ШЛЯХІВ
# ─────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hotel.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(title="Forrest Hotel API")

# Дозволяємо запити з будь-яких джерел (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Створюємо папку static, якщо її забули створити в репозиторії
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# Монтуємо папку static для CSS, JS та зображень
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ─────────────────────────────────────────────
# ІНІЦІАЛІЗАЦІЯ БАЗИ ДАНИХ
# ─────────────────────────────────────────────

def init_db():
    """Створює таблиці, якщо вони ще не існують"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Таблиця бронювань
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_type TEXT NOT NULL,
                check_in TEXT NOT NULL,
                check_out TEXT NOT NULL,
                guests INTEGER DEFAULT 2,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблиця заблокованих дат (адмін-панель)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocked_dates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_type TEXT NOT NULL,
                block_start TEXT NOT NULL,
                block_end TEXT NOT NULL,
                reason TEXT
            )
        """)
        conn.commit()

init_db()

# ─────────────────────────────────────────────
# МОДЕЛІ ДАНИХ (Pydantic)
# ─────────────────────────────────────────────

class BookingRequest(BaseModel):
    room_type: str
    check_in: str
    check_out: str
    name: str
    phone: str
    guests: int = 2
    wish: Optional[str] = None

# ─────────────────────────────────────────────
# МАРШРУТИ ДЛЯ СТОРІНОК (HTML)
# ─────────────────────────────────────────────

@app.get("/")
async def get_index():
    """Головна сторінка (index.html у корені)"""
    path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "index.html не знайдено в корені проєкту"}

@app.get("/hotel")
async def get_hotel():
    """Сторінка готелю (forrest-hotel.html у корені)"""
    path = os.path.join(BASE_DIR, "forrest-hotel.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "forrest-hotel.html не знайдено"}

# ─────────────────────────────────────────────
# API ЕНДПОІНТИ
# ─────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {
        "status": "online", 
        "database": "connected", 
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.post("/api/booking")
async def create_booking(req: BookingRequest):
    try:
        with

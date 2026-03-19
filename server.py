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

# Підключаємо статичні файли (css, js, images), якщо вони будуть у папці static
# Якщо папки static ще немає, створіть її, щоб не було помилки при запуску
if not os.path.exists(os.path.join(BASE_DIR, "static")):
    os.makedirs(os.path.join(BASE_DIR, "static"))

app.mount("/static", StaticFiles(directory="static"), name="static")

# ─────────────────────────────────────────────
# ROUTES FOR HTML
# ─────────────────────────────────────────────

@app.get("/")
def root():
    """Головна сторінка (index.html у корені)"""
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": f"index.html not found at {index_path}"}

@app.get("/hotel")
def get_hotel_page():
    """Сторінка готелю (forrest-hotel.html у корені)"""
    hotel_path = os.path.join(BASE_DIR, "forrest-hotel.html")
    if os.path.exists(hotel_path):
        return FileResponse(hotel_path)
    return {"error": "forrest-hotel.html not found"}

# ─────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    # Це дозволить звертатися до колонок за іменами r['status']
    conn.row_factory = sqlite3.Row
    return conn

def db_execute(query: str, params: tuple = ()):
    with get_db_connection() as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid

def is_available(room_type: str, check_in: str, check_out: str):
    with get_db_connection() as conn:
        # Перевірка заблокованих дат
        blocked = conn.execute(
            "SELECT 1 FROM blocked_dates WHERE room_type=? AND NOT (block_end<=? OR block_start>=?) LIMIT 1",
            (room_type, check_in, check_out),
        ).fetchone()
        if blocked: return False

        # Перевірка існуючих бронювань
        booked = conn.execute(
            "SELECT 1 FROM bookings WHERE room_type=? AND status IN ('pending','confirmed') AND NOT (check_out<=? OR check_in>=?) LIMIT 1",
            (room_type, check_in, check_out),
        ).fetchone()
        return not booked

# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

class BookingRequest(BaseModel):
    room_type: str
    check_in: str
    check_out: str
    name: str
    phone: str
    guests: int = 2
    wish: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok", "db": os.path.exists(DB_PATH)}

@app.post("/booking")
def create_booking(req: BookingRequest):
    if not is_available(req.room_type, req.check_in, req.check_out):
        raise HTTPException(409, "Дати вже зайняті")

    booking_id = db_execute(
        "INSERT INTO bookings (room_type, check_in, check_out, user_id, guests, name, phone, status) VALUES (?,?,?,?,?,?,?,'pending')",
        (req.room_type, req.check_in, req.check_out, 0, req.guests, req.name, req.phone),
    )
    return {"success": True, "id": booking_id}

# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
    uvicorn.run(app, host="0.0.0.0", port=8000)
    return {"status": "ok"}

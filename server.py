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
# КОНФІГУРАЦІЯ
# ─────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hotel.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(title="Forrest Hotel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ─────────────────────────────────────────────
# БАЗА ДАНИХ
# ─────────────────────────────────────────────

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_type TEXT,
                check_in TEXT,
                check_out TEXT,
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
                block_end TEXT
            )
        """)
        conn.commit()

init_db()

# ─────────────────────────────────────────────
# МОДЕЛІ
# ─────────────────────────────────────────────

class BookingRequest(BaseModel):
    room_type: str
    check_in: str
    check_out: str
    name: str
    phone: str
    guests: int = 2

# ─────────────────────────────────────────────
# РОУТИ (HTML)
# ─────────────────────────────────────────────

@app.get("/")
async def get_index():
    path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"message": "Server online, index.html missing"}

@app.get("/hotel")
async def get_hotel():
    path = os.path.join(BASE_DIR, "forrest-hotel.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "forrest-hotel.html missing"}

# ─────────────────────────────────────────────
# API
# ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "db": os.path.exists(DB_PATH)}

@app.post("/api/booking")
async def create_booking(req: BookingRequest):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO bookings (room_type, check_in, check_out, guests, name, phone) VALUES (?,?,?,?,?,?)",
                (req.room_type, req.check_in, req.check_out, req.guests, req.name, req.phone)
            )
            conn.commit()
            return {"success": True, "id": cur.lastrowid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)

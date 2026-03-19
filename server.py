import os
import sqlite3
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────

app = FastAPI(title="Forrest Hotel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# STATIC (ОСНОВНЕ РІШЕННЯ)
# ─────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# створить папку якщо нема
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

# ─────────────────────────────────────────────
# DB
# ─────────────────────────────────────────────

DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "hotel.db"))

def db_fetchall(query: str, params: tuple = ()):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(query, params).fetchall()

def db_execute(query: str, params: tuple = ()):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid

def is_available(room_type: str, check_in: str, check_out: str):
    blocked = db_fetchall(
        "SELECT 1 FROM blocked_dates WHERE room_type=? AND NOT (block_end<=? OR block_start>=?) LIMIT 1",
        (room_type, check_in, check_out)
    )
    if blocked:
        return False

    booked = db_fetchall(
        "SELECT 1 FROM bookings WHERE room_type=? AND status IN ('pending','confirmed') AND NOT (check_out<=? OR check_in>=?) LIMIT 1",
        (room_type, check_in, check_out)
    )
    return not booked

# ─────────────────────────────────────────────
# SCHEMA
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
# API
# ─────────────────────────────────────────────

@app.get("/availability")
def availability(room_type: str, check_in: str, check_out: str):
    return {"available": is_available(room_type, check_in, check_out)}

@app.post("/booking")
def create_booking(req: BookingRequest):
    if not is_available(req.room_type, req.check_in, req.check_out):
        raise HTTPException(status_code=409, detail="Зайнято")

    booking_id = db_execute(
        "INSERT INTO bookings (room_type, check_in, check_out, user_id, guests, name, phone, status) VALUES (?,?,?,?,?,?,?,'pending')",
        (req.room_type, req.check_in, req.check_out, 0, req.guests, req.name, req.phone)
    )

    return {"success": True, "id": booking_id}

@app.get("/health")
def health():
    return {"status": "ok"}

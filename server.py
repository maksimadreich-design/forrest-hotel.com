"""
Forrest Hotel — API сервер (production-ready)
"""

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
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "hotel.db"))

app = FastAPI(title="Forrest Hotel API")

# CORS (відкрито для фронта)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# STATIC FILES
# ─────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    """Головна сторінка"""
    index_path = os.path.join(BASE_DIR, "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html not found"}


# ─────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────

def db_fetchall(query: str, params: tuple = ()):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(query, params)
        return cur.fetchall()


def db_execute(query: str, params: tuple = ()):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid


def is_available(room_type: str, check_in: str, check_out: str):
    blocked = db_fetchall(
        "SELECT 1 FROM blocked_dates WHERE room_type=? AND NOT (block_end<=? OR block_start>=?) LIMIT 1",
        (room_type, check_in, check_out),
    )
    if blocked:
        return False

    booked = db_fetchall(
        "SELECT 1 FROM bookings WHERE room_type=? AND status IN ('pending','confirmed') AND NOT (check_out<=? OR check_in>=?) LIMIT 1",
        (room_type, check_in, check_out),
    )
    return not booked


# ─────────────────────────────────────────────
# SCHEMAS
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

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/availability")
def check_availability(room_type: str, check_in: str, check_out: str):
    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d").date()
        co = datetime.strptime(check_out, "%Y-%m-%d").date()

        if co <= ci:
            raise HTTPException(400, "check_out <= check_in")

        if ci < date.today():
            raise HTTPException(400, "date in past")

    except ValueError:
        raise HTTPException(400, "bad date format")

    return {
        "available": is_available(room_type, check_in, check_out)
    }


@app.post("/booking")
def create_booking(req: BookingRequest):
    if not is_available(req.room_type, req.check_in, req.check_out):
        raise HTTPException(409, "not available")

    booking_id = db_execute(
        "INSERT INTO bookings (room_type, check_in, check_out, user_id, guests, name, phone, status) VALUES (?,?,?,?,?,?,?,'pending')",
        (
            req.room_type,
            req.check_in,
            req.check_out,
            0,
            req.guests,
            req.name,
            req.phone,
        ),
    )

    return {"success": True, "id": booking_id}


@app.get("/bookings")
def get_bookings():
    rows = db_fetchall(
        "SELECT id, room_type, check_in, check_out, guests, name, phone, status FROM bookings ORDER BY id DESC"
    )

    return {
        "bookings": [
            {
                "id": r[0],
                "room_type": r[1],
                "check_in": r[2],
                "check_out": r[3],
                "guests": r[4],
                "name": r[5],
                "phone": r[6],
                "status": r[7],
            }
            for r in rows
        ]
    }


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
    return {"status": "ok"}

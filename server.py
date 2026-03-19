"""
Forrest Hotel — API сервер
Запуск: python server.py
Працює на http://localhost:8000
"""

import os
import sqlite3
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# База даних — поруч з server.py (і локально і на Render)
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "hotel.db"))

app = FastAPI(title="Forrest Hotel API")

# ── CORS — дозволяємо запити з будь-якого джерела ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────

def db_fetchall(query: str, params: tuple = ()) -> list[tuple]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(query, params)
        return cur.fetchall()


def db_execute(query: str, params: tuple = ()) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid


def is_available(room_type: str, check_in: str, check_out: str) -> bool:
    # Перевіряємо блоковані дати
    blocked = db_fetchall(
        "SELECT 1 FROM blocked_dates WHERE room_type=? AND NOT (block_end<=? OR block_start>=?) LIMIT 1",
        (room_type, check_in, check_out)
    )
    if blocked:
        return False
    # Перевіряємо існуючі бронювання (тільки confirmed і pending)
    booked = db_fetchall(
        "SELECT 1 FROM bookings WHERE room_type=? AND status IN ('pending','confirmed') AND NOT (check_out<=? OR check_in>=?) LIMIT 1",
        (room_type, check_in, check_out)
    )
    return not booked


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class BookingRequest(BaseModel):
    room_type: str
    check_in: str    # YYYY-MM-DD
    check_out: str   # YYYY-MM-DD
    name: str
    phone: str
    guests: int = 2
    wish: Optional[str] = None


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/availability")
def check_availability(room_type: str, check_in: str, check_out: str):
    """Перевірити чи номер вільний на дати"""
    try:
        # Валідація дат
        ci = datetime.strptime(check_in, "%Y-%m-%d").date()
        co = datetime.strptime(check_out, "%Y-%m-%d").date()
        if co <= ci:
            raise HTTPException(status_code=400, detail="Дата виїзду має бути після заїзду")
        if ci < date.today():
            raise HTTPException(status_code=400, detail="Дата заїзду не може бути в минулому")
    except ValueError:
        raise HTTPException(status_code=400, detail="Невірний формат дати (YYYY-MM-DD)")

    available = is_available(room_type, check_in, check_out)
    return {"available": available, "room_type": room_type, "check_in": check_in, "check_out": check_out}


@app.get("/booked-dates")
def get_booked_dates(room_type: str):
    """Отримати всі зайняті дати для номера (для календаря на сайті)"""
    rows = db_fetchall(
        "SELECT check_in, check_out FROM bookings WHERE room_type=? AND status IN ('pending','confirmed')",
        (room_type,)
    )
    blocks = db_fetchall(
        "SELECT block_start, block_end FROM blocked_dates WHERE room_type=?",
        (room_type,)
    )

    dates = set()
    for ci, co in rows + blocks:
        try:
            d = datetime.strptime(ci, "%Y-%m-%d").date()
            end = datetime.strptime(co, "%Y-%m-%d").date()
            while d < end:
                dates.add(d.isoformat())
                d = date.fromordinal(d.toordinal() + 1)
        except ValueError:
            continue

    return {"room_type": room_type, "booked_dates": sorted(dates)}


@app.post("/booking")
def create_booking(req: BookingRequest):
    """Створити бронювання з сайту"""
    # Валідація
    valid_rooms = ["standard", "deluxe", "suite"]
    if req.room_type not in valid_rooms:
        raise HTTPException(status_code=400, detail="Невірний тип номера")

    try:
        ci = datetime.strptime(req.check_in, "%Y-%m-%d").date()
        co = datetime.strptime(req.check_out, "%Y-%m-%d").date()
        if co <= ci:
            raise HTTPException(status_code=400, detail="Дата виїзду має бути після заїзду")
        if ci < date.today():
            raise HTTPException(status_code=400, detail="Дата заїзду не може бути в минулому")
    except ValueError:
        raise HTTPException(status_code=400, detail="Невірний формат дати")

    # Перевірка доступності
    if not is_available(req.room_type, req.check_in, req.check_out):
        raise HTTPException(status_code=409, detail="Номер вже зайнятий на ці дати")

    # Зберігаємо в БД
    wish_note = f" | Побажання: {req.wish}" if req.wish else ""
    booking_id = db_execute(
        "INSERT INTO bookings (room_type, check_in, check_out, user_id, guests, name, phone, status) VALUES (?,?,?,?,?,?,?,'pending')",
        (req.room_type, req.check_in, req.check_out, 0, req.guests, req.name, req.phone + wish_note)
    )

    return {
        "success": True,
        "booking_id": booking_id,
        "message": "Бронювання прийнято! Адміністратор зв'яжеться з вами найближчим часом."
    }


@app.get("/bookings")
def get_all_bookings():
    """Всі бронювання (для адмін панелі)"""
    rows = db_fetchall(
        "SELECT id, room_type, check_in, check_out, guests, name, phone, status FROM bookings ORDER BY id DESC LIMIT 50",
        ()
    )
    result = []
    for bid, room_type, ci, co, guests, name, phone, status in rows:
        result.append({
            "id": bid,
            "room_type": room_type,
            "check_in": ci,
            "check_out": co,
            "guests": guests,
            "name": name,
            "phone": phone,
            "status": status,
        })
    return {"bookings": result}


@app.get("/health")
def health():
    return {"status": "ok", "db": DB_PATH}


@app.get("/")
def serve_site():
    """Відкриває сайт forrest-hotel.html"""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forrest-hotel.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return {"error": "forrest-hotel.html not found"}


# ─────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("🌲 Forrest Hotel API запущено на http://localhost:8000")
    print("📖 Документація: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)

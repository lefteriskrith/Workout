from datetime import date, timedelta
from .db import get_conn


def log(*, on_date=None, weight_kg=None, sleep_h=None, energy=None,
        pain_notes=None, notes=None):
    log_date = on_date or date.today().isoformat()
    # INSERT OR REPLACE: health_logs.date is PRIMARY KEY, so this is an upsert —
    # logging twice on the same day overwrites instead of duplicating
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO health_logs
               (date, weight_kg, sleep_h, energy, pain_notes, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (log_date, weight_kg, sleep_h, energy, pain_notes, notes),
        )


def get_recent(days=30):
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM health_logs WHERE date >= ? ORDER BY date DESC",
            (cutoff,),
        ).fetchall()


def get_for_date(target_date):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM health_logs WHERE date = ?", (target_date,)
        ).fetchone()

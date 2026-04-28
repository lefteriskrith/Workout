# Statistics: personal records, streak, activity frequency, weekly volume
from datetime import date, timedelta
from .db import get_conn


def get_prs():
    with get_conn() as conn:
        return conn.execute(
            """SELECT pr.*, a.name, a.unit, a.category
               FROM personal_records pr JOIN activities a ON pr.activity_id = a.id
               ORDER BY a.category, a.name"""
        ).fetchall()


def streak():
    # Walk dates newest→oldest; allow yesterday as the opening day so the
    # streak doesn't reset just because the user hasn't trained yet today
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM workout_logs ORDER BY date DESC"
        ).fetchall()

    if not rows:
        return 0

    today = date.today()
    count = 0
    expected = today

    for row in rows:
        d = date.fromisoformat(row["date"])
        if d == expected:
            count += 1
            expected = d - timedelta(days=1)
        elif count == 0 and d == today - timedelta(days=1):
            # First date found is yesterday — start counting from there
            count += 1
            expected = d - timedelta(days=1)
        else:
            break

    return count


def activity_frequency(days=30):
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        return conn.execute(
            """SELECT a.name, a.category, COUNT(*) as count,
                      SUM(w.sets) as total_sets, SUM(w.reps) as total_reps,
                      SUM(w.duration_min) as total_min
               FROM workout_logs w JOIN activities a ON w.activity_id = a.id
               WHERE w.date >= ?
               GROUP BY w.activity_id
               ORDER BY count DESC""",
            (cutoff,),
        ).fetchall()


def weekly_volume(weeks=8):
    with get_conn() as conn:
        return conn.execute(
            """SELECT strftime('%Y-W%W', date) as week,
                      COUNT(*) as sessions,
                      COUNT(DISTINCT date) as days_active,
                      COUNT(DISTINCT activity_id) as different_exercises
               FROM workout_logs
               WHERE date >= date('now', ?)
               GROUP BY week ORDER BY week""",
            (f"-{weeks * 7} days",),
        ).fetchall()


def activity_trend(activity_id, limit=10):
    with get_conn() as conn:
        return conn.execute(
            """SELECT date, sets, reps, weight_kg, duration_min, notes
               FROM workout_logs WHERE activity_id = ?
               ORDER BY date DESC, logged_at DESC LIMIT ?""",
            (activity_id, limit),
        ).fetchall()

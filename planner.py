from datetime import date, timedelta
from db import get_conn

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def current_week_start(for_date=None):
    d = for_date or date.today()
    return (d - timedelta(days=d.weekday())).isoformat()


def set_entry(ws, day_index, activity_id, *, target_sets=None, target_reps=None,
              target_kg=None, target_min=None, notes=None):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO weekly_plans
               (week_start, day_index, activity_id, target_sets, target_reps,
                target_kg, target_min, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ws, day_index, activity_id, target_sets, target_reps,
             target_kg, target_min, notes),
        )


def get_plan(ws):
    with get_conn() as conn:
        return conn.execute(
            """SELECT p.*, a.name as activity_name, a.unit
               FROM weekly_plans p JOIN activities a ON p.activity_id = a.id
               WHERE p.week_start = ?
               ORDER BY p.day_index, a.name""",
            (ws,),
        ).fetchall()


def delete_entry(entry_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM weekly_plans WHERE id = ?", (entry_id,))


def copy_plan(from_ws, to_ws):
    # OR IGNORE respects the UNIQUE(week_start, day_index, activity_id) constraint —
    # entries the user has already set for to_ws are not overwritten
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM weekly_plans WHERE week_start = ?", (from_ws,)
        ).fetchall()
        for r in rows:
            conn.execute(
                """INSERT OR IGNORE INTO weekly_plans
                   (week_start, day_index, activity_id, target_sets, target_reps,
                    target_kg, target_min, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (to_ws, r["day_index"], r["activity_id"], r["target_sets"],
                 r["target_reps"], r["target_kg"], r["target_min"], r["notes"]),
            )

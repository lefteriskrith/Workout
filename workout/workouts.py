from datetime import date as date_type
from .db import get_conn


# ─── Core logging ─────────────────────────────────────────────────────────────

def log(activity_id, *, sets=None, reps=None, weight_kg=None,
        duration_min=None, notes=None, on_date=None):
    log_date = on_date or date_type.today().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO workout_logs
               (date, activity_id, sets, reps, weight_kg, duration_min, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (log_date, activity_id, sets, reps, weight_kg, duration_min, notes),
        )
        return _update_pr(conn, activity_id, sets, reps, weight_kg, duration_min, log_date)


def log_sets(activity_id, sets_data, notes=None, on_date=None):
    """Log individual sets. sets_data: list of dict(weight_kg, reps, rpe, duration_min)."""
    log_date = on_date or date_type.today().isoformat()
    all_prs = []
    # seen de-duplicates PR strings: multiple sets at the same weight each
    # trigger _update_pr, but we only want to report the first occurrence
    seen = set()
    with get_conn() as conn:
        for i, s in enumerate(sets_data, 1):
            conn.execute(
                """INSERT INTO workout_logs
                   (date, activity_id, set_num, reps, weight_kg, duration_min, rpe, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (log_date, activity_id, i,
                 s.get("reps"), s.get("weight_kg"),
                 s.get("duration_min"), s.get("rpe"), notes),
            )
            for pr in _update_pr(conn, activity_id, 1,
                                 s.get("reps"), s.get("weight_kg"),
                                 s.get("duration_min"), log_date):
                if pr not in seen:
                    all_prs.append(pr)
                    seen.add(pr)
    return all_prs


# ─── PR detection ─────────────────────────────────────────────────────────────

def _update_pr(conn, activity_id, sets, reps, weight_kg, duration_min, log_date):
    # Called after every set; returns human-readable PR strings for the UI to display
    new_prs = []
    # volume = sets × reps — crude proxy for total work done in a session
    volume = (sets or 1) * reps if reps else None

    existing = conn.execute(
        "SELECT * FROM personal_records WHERE activity_id = ?", (activity_id,)
    ).fetchone()

    if not existing:
        conn.execute(
            """INSERT INTO personal_records
               (activity_id, best_weight_kg, best_reps, best_duration_min, best_volume, pr_date)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (activity_id, weight_kg, reps, duration_min, volume, log_date),
        )
        if weight_kg:    new_prs.append(f"First weight: {weight_kg}kg!")
        if reps:         new_prs.append(f"First reps: {reps}!")
        if duration_min: new_prs.append(f"First duration: {duration_min:.0f}min!")
        return new_prs

    updates = {}
    if weight_kg and (not existing["best_weight_kg"] or weight_kg > existing["best_weight_kg"]):
        updates["best_weight_kg"] = weight_kg
        new_prs.append(f"New weight PR: {weight_kg}kg!")
    if reps and (not existing["best_reps"] or reps > existing["best_reps"]):
        updates["best_reps"] = reps
        new_prs.append(f"New reps PR: {reps}!")
    if duration_min and (not existing["best_duration_min"] or duration_min > existing["best_duration_min"]):
        updates["best_duration_min"] = duration_min
        new_prs.append(f"New duration PR: {duration_min:.0f}min!")
    if volume and (not existing["best_volume"] or volume > existing["best_volume"]):
        updates["best_volume"] = volume
        new_prs.append(f"New volume PR: {int(volume)}!")

    if updates:
        updates["pr_date"] = log_date
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE personal_records SET {set_clause} WHERE activity_id = ?",
            (*updates.values(), activity_id),
        )
    return new_prs


# ─── Query helpers ────────────────────────────────────────────────────────────

def last_session_sets(activity_id):
    """Returns (date_str, [(weight_kg, reps, rpe, duration_min), ...]) for last session."""
    with get_conn() as conn:
        last_date = conn.execute(
            "SELECT MAX(date) FROM workout_logs WHERE activity_id = ?",
            (activity_id,),
        ).fetchone()[0]
        if not last_date:
            return None, []
        rows = conn.execute(
            """SELECT weight_kg, reps, rpe, duration_min FROM workout_logs
               WHERE activity_id = ? AND date = ?
               ORDER BY COALESCE(set_num, rowid)""",
            (activity_id, last_date),
        ).fetchall()
        return last_date, [(r[0], r[1], r[2], r[3]) for r in rows]


def calc_1rm(weight_kg, reps):
    """Epley formula: weight × (1 + reps/30)."""
    if not weight_kg or not reps or reps <= 0:
        return None
    return round(weight_kg * (1 + reps / 30), 1)


def for_date(target_date):
    with get_conn() as conn:
        return conn.execute(
            """SELECT w.*, a.name as activity_name, a.category, a.unit
               FROM workout_logs w JOIN activities a ON w.activity_id = a.id
               WHERE w.date = ? ORDER BY w.logged_at""",
            (target_date,),
        ).fetchall()


def for_date_summary(target_date):
    """One aggregated row per exercise — for Today page display."""
    with get_conn() as conn:
        return conn.execute(
            """SELECT
                   a.id as activity_id,
                   a.name as activity_name, a.category, a.unit,
                   COUNT(*) as sets,
                   MAX(w.weight_kg) as max_weight,
                   MAX(w.reps) as max_reps,
                   SUM(w.duration_min) as total_duration,
                   ROUND(AVG(CAST(w.rpe AS REAL)), 1) as avg_rpe
               FROM workout_logs w JOIN activities a ON w.activity_id = a.id
               WHERE w.date = ?
               GROUP BY w.activity_id
               ORDER BY MIN(w.logged_at)""",
            (target_date,),
        ).fetchall()


def for_week(week_start):
    with get_conn() as conn:
        return conn.execute(
            """SELECT w.*, a.name as activity_name, a.category, a.unit,
                      a.id as activity_id
               FROM workout_logs w JOIN activities a ON w.activity_id = a.id
               WHERE w.date >= ? AND w.date < date(?, '+7 days')
               ORDER BY w.date, a.name""",
            (week_start, week_start),
        ).fetchall()


def for_activity(activity_id, limit=20):
    with get_conn() as conn:
        return conn.execute(
            """SELECT w.*, a.name as activity_name
               FROM workout_logs w JOIN activities a ON w.activity_id = a.id
               WHERE w.activity_id = ?
               ORDER BY w.date DESC, w.logged_at DESC LIMIT ?""",
            (activity_id, limit),
        ).fetchall()

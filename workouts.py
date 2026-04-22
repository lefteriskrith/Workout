from datetime import date as date_type
from db import get_conn


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


def _update_pr(conn, activity_id, sets, reps, weight_kg, duration_min, log_date):
    new_prs = []
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
        if weight_kg:    new_prs.append(f"First weight log: {weight_kg}kg!")
        if reps:         new_prs.append(f"First reps log: {reps}!")
        if duration_min: new_prs.append(f"First duration log: {duration_min:.0f}min!")
        return new_prs

    updates = {}
    if weight_kg and (not existing["best_weight_kg"] or weight_kg > existing["best_weight_kg"]):
        updates["best_weight_kg"] = weight_kg
        new_prs.append(f"New weight PR: {weight_kg}kg!")

    if reps and (not existing["best_reps"] or reps > existing["best_reps"]):
        updates["best_reps"] = reps
        new_prs.append(f"New reps PR: {reps} reps!")

    if duration_min and (not existing["best_duration_min"] or duration_min > existing["best_duration_min"]):
        updates["best_duration_min"] = duration_min
        new_prs.append(f"New duration PR: {duration_min:.0f}min!")

    if volume and (not existing["best_volume"] or volume > existing["best_volume"]):
        updates["best_volume"] = volume
        new_prs.append(f"New volume PR: {int(volume)} total reps!")

    if updates:
        updates["pr_date"] = log_date
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE personal_records SET {set_clause} WHERE activity_id = ?",
            (*updates.values(), activity_id),
        )

    return new_prs


def for_date(target_date):
    with get_conn() as conn:
        return conn.execute(
            """SELECT w.*, a.name as activity_name, a.category, a.unit
               FROM workout_logs w JOIN activities a ON w.activity_id = a.id
               WHERE w.date = ? ORDER BY w.logged_at""",
            (target_date,),
        ).fetchall()


def for_week(week_start):
    with get_conn() as conn:
        return conn.execute(
            """SELECT w.*, a.name as activity_name, a.category, a.unit
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

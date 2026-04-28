# Workout templates: reusable exercise lists with target sets/reps/weight
from .db import get_conn


def all_templates():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM templates ORDER BY name").fetchall()


def create(name):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO templates (name) VALUES (?)", (name,))
        return conn.execute(
            "SELECT id FROM templates WHERE name = ?", (name,)
        ).fetchone()["id"]


def get_exercises(template_id):
    with get_conn() as conn:
        return conn.execute(
            """SELECT te.*, a.name as activity_name, a.unit, a.category
               FROM template_exercises te JOIN activities a ON te.activity_id = a.id
               WHERE te.template_id = ? ORDER BY te.sort_order""",
            (template_id,),
        ).fetchall()


def add_exercise(template_id, activity_id, sort_order,
                 target_sets=None, target_reps=None, target_kg=None):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO template_exercises
               (template_id, activity_id, sort_order, target_sets, target_reps, target_kg)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (template_id, activity_id, sort_order, target_sets, target_reps, target_kg),
        )


def delete(template_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))


def remove_exercise(exercise_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM template_exercises WHERE id = ?", (exercise_id,))

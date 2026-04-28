from db import get_conn

# Pre-seeded exercises; INSERT OR IGNORE in seed() keeps re-runs safe
DEFAULTS = [
    ("Skate",     "sport",      "min"),
    ("Tennis",    "sport",      "min"),
    ("Kettlebell","strength",   "kg"),
    ("Monozigo",  "strength",   "kg"),
    ("Dizigo",    "strength",   "kg"),
    ("Box",       "combat",     "rounds"),
    ("Sxoinaki",  "cardio",     "min"),
    ("Push-ups",  "bodyweight", "reps"),
    ("Kiliakous", "bodyweight", "reps"),
    ("Pull-ups",  "bodyweight", "reps"),
    ("Plank",     "core",       "sec"),
    ("Gonato",    "rehab",      "sets"),
]

# Order matters: shown as-is in the UI combo boxes
CATEGORIES = ["sport", "strength", "bodyweight", "cardio", "combat", "core", "rehab"]
UNITS = ["reps", "min", "sec", "kg", "rounds", "sets"]


def seed():
    # OR IGNORE: calling this on every startup won't duplicate existing rows
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO activities (name, category, unit) VALUES (?, ?, ?)",
            DEFAULTS,
        )


def all_activities():
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM activities ORDER BY category, name"
        ).fetchall()


def get_by_id(activity_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM activities WHERE id = ?", (activity_id,)
        ).fetchone()


def add(name, category, unit):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO activities (name, category, unit) VALUES (?, ?, ?)",
            (name, category, unit),
        )

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".gym_tracker" / "gym.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn):
    for stmt in [
        "ALTER TABLE workout_logs ADD COLUMN set_num INTEGER",
        "ALTER TABLE workout_logs ADD COLUMN rpe     INTEGER",
    ]:
        try:
            conn.execute(stmt)
        except Exception:
            pass

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS templates (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE,
            created_at TEXT    DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS template_exercises (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
            activity_id INTEGER NOT NULL REFERENCES activities(id),
            sort_order  INTEGER NOT NULL DEFAULT 0,
            target_sets INTEGER,
            target_reps INTEGER,
            target_kg   REAL
        );
    """)


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS activities (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT    NOT NULL UNIQUE,
                category TEXT    NOT NULL,
                unit     TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workout_logs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT    NOT NULL,
                activity_id  INTEGER NOT NULL REFERENCES activities(id),
                sets         INTEGER,
                reps         INTEGER,
                weight_kg    REAL,
                duration_min REAL,
                notes        TEXT,
                logged_at    TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS personal_records (
                activity_id       INTEGER PRIMARY KEY REFERENCES activities(id),
                best_weight_kg    REAL,
                best_reps         INTEGER,
                best_duration_min REAL,
                best_volume       REAL,
                pr_date           TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS weekly_plans (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start   TEXT    NOT NULL,
                day_index    INTEGER NOT NULL,
                activity_id  INTEGER NOT NULL REFERENCES activities(id),
                target_sets  INTEGER,
                target_reps  INTEGER,
                target_kg    REAL,
                target_min   REAL,
                notes        TEXT,
                UNIQUE(week_start, day_index, activity_id)
            );

            CREATE TABLE IF NOT EXISTS health_logs (
                date       TEXT PRIMARY KEY,
                weight_kg  REAL,
                sleep_h    REAL,
                energy     INTEGER,
                pain_notes TEXT,
                notes      TEXT
            );
        """)
        _migrate(conn)

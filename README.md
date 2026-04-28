# Workout Tracker

A personal workout tracking desktop app built with Python and CustomTkinter.

## Download

[![Download](https://img.shields.io/badge/Download-Workout.zip-orange?style=for-the-badge&logo=windows)](https://raw.githubusercontent.com/lefteriskrith/Workout/main/releases/Workout.zip)

> Windows only · No installation required · Just unzip and run `Workout.exe`

---

## Screenshots

| Log Workout | Manage Activities |
|:-----------:|:-----------------:|
| ![Log Workout](docs/screenshots/log_workout.png) | ![Activities](docs/screenshots/activities.png) |

---

## Features

- **Log Workout** — Log sets with weight, reps, duration, and RPE per exercise
- **Today** — Summary of everything logged today
- **Weekly Overview** — See planned vs completed exercises for the week, with progress bars
- **Personal Records** — Tracks best weight, reps, duration and volume per exercise automatically
- **Planner** — Set weekly targets per exercise per day; copy last week's plan
- **Health Log** — Daily body weight, sleep hours, energy level, and pain notes
- **Statistics** — 30-day frequency table and 8-week volume trend
- **Templates** — Save reusable workout routines
- **Activities** — Add your own custom exercises with category and unit

---

## Running from Source

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt
python WorkoutApp.py
```

For the terminal (CLI) interface:

```bash
python main.py
```

---

## Project Structure

```
Workout/
├── workout/              # Business logic package
│   ├── db.py             # Database connection, schema, migrations
│   ├── activities.py     # Exercise library (CRUD)
│   ├── workouts.py       # Logging, PR detection, session queries
│   ├── stats.py          # Streak, frequency, weekly volume
│   ├── health.py         # Daily health log
│   ├── planner.py        # Weekly planner
│   └── templates.py      # Workout templates
├── WorkoutApp.py         # GUI entry point (CustomTkinter)
├── main.py               # CLI entry point (Rich)
└── tests/
    └── test_workout.py   # 47 smoke + regression tests
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

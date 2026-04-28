import sys
from datetime import date, timedelta

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

import workout.db as db
import workout.activities as act
import workout.workouts as wk
import workout.stats as st
import workout.planner as plan
import workout.health as hl

console = Console()

CATEGORY_COLORS = {
    "sport":      "blue",
    "strength":   "red",
    "bodyweight": "green",
    "cardio":     "yellow",
    "combat":     "magenta",
    "core":       "cyan",
    "rehab":      "white",
}


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def clr():
    console.clear()


def header(title="GYM TRACKER"):
    today = date.today().strftime("%A, %d %b %Y")
    streak = st.streak()
    streak_txt = f"  [bold yellow]streak {streak}d[/bold yellow]" if streak > 1 else ""
    console.print(Panel(
        f"[bold cyan]{title}[/bold cyan]  [dim]{today}[/dim]{streak_txt}",
        expand=False,
    ))


def pause():
    Prompt.ask("\n[dim]Enter to continue[/dim]", default="")


def _fmt_weight(v):  return f"{v}kg" if v else "—"
def _fmt_reps(v):    return str(v) if v else "—"
def _fmt_dur(v):     return f"{v:.0f}min" if v else "—"


def pick_activity(prompt_text="Select activity"):
    activities = act.all_activities()
    if not activities:
        console.print("[red]No activities found.[/red]")
        return None

    table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Activity", min_width=14)
    table.add_column("Category")
    table.add_column("Unit")

    for i, a in enumerate(activities, 1):
        color = CATEGORY_COLORS.get(a["category"], "white")
        table.add_row(str(i), a["name"],
                      f"[{color}]{a['category']}[/{color}]", a["unit"])

    console.print(table)
    valid = [str(i) for i in range(1, len(activities) + 1)]
    choice = Prompt.ask(prompt_text, choices=valid + ["b"], default="b")
    if choice == "b":
        return None
    return activities[int(choice) - 1]


def _ask_optional_int(label):
    raw = Prompt.ask(label, default="")
    return int(raw) if raw.strip() else None


def _ask_optional_float(label):
    raw = Prompt.ask(label, default="")
    return float(raw) if raw.strip() else None


# ─── LOG WORKOUT ─────────────────────────────────────────────────────────────

def log_workout_screen():
    clr()
    header("LOG WORKOUT")
    activity = pick_activity()
    if not activity:
        return

    console.print(f"\nLogging: [bold]{activity['name']}[/bold]  unit=[dim]{activity['unit']}[/dim]\n")

    unit = activity["unit"]
    sets = reps = weight_kg = duration_min = None

    if unit == "kg":
        weight_kg    = _ask_optional_float("Weight (kg)")
        reps         = _ask_optional_int("Reps")
        sets         = _ask_optional_int("Sets")

    elif unit == "reps":
        reps = _ask_optional_int("Reps")
        sets = _ask_optional_int("Sets")

    elif unit == "sec":
        raw = Prompt.ask("Duration (seconds)", default="")
        if raw.strip():
            duration_min = float(raw) / 60
        sets = _ask_optional_int("Rounds/Sets (optional)", )

    elif unit in ("min", "rounds"):
        duration_min = _ask_optional_float(f"Duration ({unit})")
        sets         = _ask_optional_int("Sets/Rounds (optional)")

    elif unit == "sets":
        sets = _ask_optional_int("Sets")
        reps = _ask_optional_int("Reps per set (optional)")

    notes_raw = Prompt.ask("Notes (optional)", default="")

    new_prs = wk.log(
        activity["id"],
        sets=sets, reps=reps, weight_kg=weight_kg,
        duration_min=duration_min, notes=notes_raw or None,
    )

    console.print("\n[green]Workout logged![/green]")
    for pr in new_prs:
        console.print(f"[bold yellow]  {pr}[/bold yellow]")
    pause()


# ─── TODAY'S SUMMARY ─────────────────────────────────────────────────────────

def today_summary_screen():
    clr()
    header("TODAY'S SUMMARY")

    today = date.today().isoformat()
    entries = wk.for_date(today)
    health  = hl.get_for_date(today)

    if not entries:
        console.print("\n[dim]No workouts logged today.[/dim]")
    else:
        table = Table(show_header=True, header_style="bold green", box=box.ROUNDED)
        table.add_column("Activity", min_width=12)
        table.add_column("Sets",     justify="right")
        table.add_column("Reps",     justify="right")
        table.add_column("Weight",   justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Notes")

        for e in entries:
            table.add_row(
                e["activity_name"],
                _fmt_reps(e["sets"]),
                _fmt_reps(e["reps"]),
                _fmt_weight(e["weight_kg"]),
                _fmt_dur(e["duration_min"]),
                e["notes"] or "",
            )
        console.print(table)
        console.print(f"\n[dim]Sessions logged: {len(entries)}[/dim]")

    if health:
        console.print(
            f"\n[bold]Health:[/bold]  weight={_fmt_weight(health['weight_kg'])}  "
            f"sleep={health['sleep_h'] or '—'}h  "
            f"energy={health['energy'] or '—'}/10"
        )
        if health["pain_notes"]:
            console.print(f"[red]Pain/discomfort: {health['pain_notes']}[/red]")

    pause()


# ─── WEEKLY OVERVIEW ─────────────────────────────────────────────────────────

def weekly_overview_screen():
    clr()
    header("WEEKLY OVERVIEW")

    today = date.today()
    ws      = plan.current_week_start(today)
    entries = wk.for_week(ws)

    if not entries:
        console.print("\n[dim]No workouts this week yet.[/dim]")
    else:
        table = Table(show_header=True, header_style="bold blue", box=box.ROUNDED)
        table.add_column("Day")
        table.add_column("Activity")
        table.add_column("Sets",     justify="right")
        table.add_column("Reps",     justify="right")
        table.add_column("Weight",   justify="right")
        table.add_column("Duration", justify="right")

        days_seen = {}
        for e in entries:
            day_name  = date.fromisoformat(e["date"]).strftime("%A")
            first_row = day_name not in days_seen
            days_seen[day_name] = True
            table.add_row(
                f"[bold]{day_name}[/bold]" if first_row else "",
                e["activity_name"],
                _fmt_reps(e["sets"]),
                _fmt_reps(e["reps"]),
                _fmt_weight(e["weight_kg"]),
                _fmt_dur(e["duration_min"]),
            )
        console.print(table)
        console.print(
            f"\n[dim]Days active: {len(days_seen)}/7  |  Total sessions: {len(entries)}[/dim]"
        )

    plan_rows = plan.get_plan(ws)
    if plan_rows:
        console.print("\n[bold]Plan vs Actual:[/bold]")
        _show_plan_vs_actual(ws, plan_rows, entries)

    pause()


def _show_plan_vs_actual(ws, plan_rows, actual_entries):
    actual_by_day = {}
    for e in actual_entries:
        day_idx = date.fromisoformat(e["date"]).weekday()
        actual_by_day.setdefault(day_idx, set()).add(e["activity_id"])

    plan_by_day = {}
    for p in plan_rows:
        plan_by_day.setdefault(p["day_index"], []).append(p)

    table = Table(box=box.SIMPLE)
    table.add_column("Day")
    table.add_column("Planned")
    table.add_column("Done", justify="center")
    table.add_column("Status", justify="center")

    for day_idx, day_plans in sorted(plan_by_day.items()):
        day_name  = plan.DAYS[day_idx]
        done_ids  = actual_by_day.get(day_idx, set())
        done_count = sum(1 for p in day_plans if p["activity_id"] in done_ids)
        total      = len(day_plans)
        planned_names = ", ".join(p["activity_name"] for p in day_plans)

        if done_count == total:
            color, status = "green", "✓"
        elif done_count > 0:
            color, status = "yellow", f"{done_count}/{total}"
        else:
            color, status = "red", "✗"

        table.add_row(
            day_name, planned_names,
            str(done_count),
            f"[{color}]{status}[/{color}]",
        )
    console.print(table)


# ─── PERSONAL RECORDS ────────────────────────────────────────────────────────

def prs_screen():
    clr()
    header("PERSONAL RECORDS")

    prs = st.get_prs()
    if not prs:
        console.print("\n[dim]No records yet. Start logging![/dim]")
        pause()
        return

    table = Table(show_header=True, header_style="bold yellow", box=box.ROUNDED)
    table.add_column("Activity",   min_width=12)
    table.add_column("Category")
    table.add_column("Best Weight",   justify="right")
    table.add_column("Best Reps",     justify="right")
    table.add_column("Best Duration", justify="right")
    table.add_column("Volume PR",     justify="right")
    table.add_column("Date")

    for pr in prs:
        color = CATEGORY_COLORS.get(pr["category"], "white")
        table.add_row(
            f"[bold]{pr['name']}[/bold]",
            f"[{color}]{pr['category']}[/{color}]",
            _fmt_weight(pr["best_weight_kg"]),
            _fmt_reps(pr["best_reps"]),
            _fmt_dur(pr["best_duration_min"]),
            str(int(pr["best_volume"])) if pr["best_volume"] else "—",
            pr["pr_date"],
        )
    console.print(table)
    pause()


# ─── WEEKLY PLANNER ──────────────────────────────────────────────────────────

def planner_screen():
    while True:
        clr()
        header("WEEKLY PLANNER")

        today = date.today()
        ws    = plan.current_week_start(today)
        console.print(f"\n[dim]Week of {ws}[/dim]\n")

        plan_rows = plan.get_plan(ws)
        if plan_rows:
            _show_plan_table(plan_rows)
        else:
            console.print("[dim]No plan set for this week.[/dim]\n")

        console.print("\n[cyan]1[/cyan] Add plan entry")
        console.print("[cyan]2[/cyan] Copy plan from last week")
        console.print("[cyan]3[/cyan] View a different week")
        console.print("[cyan]b[/cyan] Back\n")

        choice = Prompt.ask("Choice", choices=["1", "2", "3", "b"], default="b")

        if choice == "1":
            _add_plan_entry(ws)
        elif choice == "2":
            last_ws = (today - timedelta(days=today.weekday() + 7)).isoformat()
            plan.copy_plan(last_ws, ws)
            console.print("[green]Plan copied from last week![/green]")
            pause()
        elif choice == "3":
            _view_other_week()
        else:
            break


def _show_plan_table(plan_rows):
    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("Day")
    table.add_column("Activity",       min_width=12)
    table.add_column("Sets",           justify="right")
    table.add_column("Reps",           justify="right")
    table.add_column("Weight",         justify="right")
    table.add_column("Duration",       justify="right")
    table.add_column("Notes")

    day_seen = {}
    for p in plan_rows:
        day_name = plan.DAYS[p["day_index"]]
        first    = day_name not in day_seen
        day_seen[day_name] = True
        table.add_row(
            f"[bold]{day_name}[/bold]" if first else "",
            p["activity_name"],
            _fmt_reps(p["target_sets"]),
            _fmt_reps(p["target_reps"]),
            _fmt_weight(p["target_kg"]),
            _fmt_dur(p["target_min"]),
            p["notes"] or "",
        )
    console.print(table)


def _add_plan_entry(ws):
    console.print("\n[bold]Add Plan Entry[/bold]")
    for i, d in enumerate(plan.DAYS):
        console.print(f"  [cyan]{i}[/cyan] {d}")
    day_idx = int(
        Prompt.ask("Day (0=Mon, 6=Sun)",
                   choices=[str(i) for i in range(7)])
    )
    activity = pick_activity()
    if not activity:
        return

    target_sets = _ask_optional_int("Target sets")
    target_reps = _ask_optional_int("Target reps")
    target_kg   = _ask_optional_float("Target weight (kg)")
    target_min  = _ask_optional_float("Target duration (min)")
    notes_raw   = Prompt.ask("Notes", default="")

    plan.set_entry(ws, day_idx, activity["id"],
                   target_sets=target_sets, target_reps=target_reps,
                   target_kg=target_kg, target_min=target_min,
                   notes=notes_raw or None)
    console.print("[green]Plan entry added![/green]")
    pause()


def _view_other_week():
    raw = Prompt.ask("Enter any date in that week (YYYY-MM-DD)",
                     default=date.today().isoformat())
    try:
        d  = date.fromisoformat(raw)
        ws = plan.current_week_start(d)
        clr()
        console.print(f"\n[bold]Week of {ws}[/bold]\n")
        rows = plan.get_plan(ws)
        if rows:
            _show_plan_table(rows)
        else:
            console.print("[dim]No plan for this week.[/dim]")
    except ValueError:
        console.print("[red]Invalid date format.[/red]")
    pause()


# ─── HEALTH LOG ──────────────────────────────────────────────────────────────

def health_screen():
    while True:
        clr()
        header("HEALTH LOG")
        console.print("\n[cyan]1[/cyan] Log today")
        console.print("[cyan]2[/cyan] View history (30 days)")
        console.print("[cyan]b[/cyan] Back\n")

        choice = Prompt.ask("Choice", choices=["1", "2", "b"], default="b")
        if choice == "1":
            _log_health()
        elif choice == "2":
            _view_health_history()
        else:
            break


def _log_health():
    today    = date.today().isoformat()
    existing = hl.get_for_date(today)

    console.print(f"\n[bold]Health Log — {today}[/bold]")
    if existing:
        console.print("[dim](Updating today's entry)[/dim]")

    def _default(field):
        v = existing[field] if existing else None
        return str(v) if v is not None else ""

    raw = Prompt.ask("Weight (kg)", default=_default("weight_kg"))
    weight_kg = float(raw) if raw.strip() else None

    raw = Prompt.ask("Sleep (hours)", default=_default("sleep_h"))
    sleep_h = float(raw) if raw.strip() else None

    raw = Prompt.ask("Energy level (1–10)", default=_default("energy"))
    energy = int(raw) if raw.strip() else None

    pain  = Prompt.ask("Pain/discomfort", default=_default("pain_notes"))
    notes = Prompt.ask("General notes",   default=_default("notes"))

    hl.log(weight_kg=weight_kg, sleep_h=sleep_h, energy=energy,
           pain_notes=pain or None, notes=notes or None)
    console.print("[green]Health logged![/green]")
    pause()


def _view_health_history():
    clr()
    header("HEALTH HISTORY")
    records = hl.get_recent(30)
    if not records:
        console.print("[dim]No health records yet.[/dim]")
        pause()
        return

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("Date")
    table.add_column("Weight",    justify="right")
    table.add_column("Sleep (h)", justify="right")
    table.add_column("Energy",    justify="right")
    table.add_column("Pain/Notes")

    for r in records:
        e = r["energy"] or 0
        ecol = "green" if e >= 7 else "yellow" if e >= 4 else "red"
        table.add_row(
            r["date"],
            _fmt_weight(r["weight_kg"]),
            str(r["sleep_h"]) if r["sleep_h"] else "—",
            f"[{ecol}]{r['energy'] or '—'}[/{ecol}]",
            r["pain_notes"] or r["notes"] or "",
        )
    console.print(table)
    pause()


# ─── STATISTICS ──────────────────────────────────────────────────────────────

def stats_screen():
    while True:
        clr()
        header("STATISTICS")
        console.print("\n[cyan]1[/cyan] Activity frequency — last 30 days")
        console.print("[cyan]2[/cyan] Weekly volume trend — last 8 weeks")
        console.print("[cyan]3[/cyan] Activity history (select exercise)")
        console.print("[cyan]b[/cyan] Back\n")

        choice = Prompt.ask("Choice", choices=["1", "2", "3", "b"], default="b")
        if choice == "1":
            _show_frequency()
        elif choice == "2":
            _show_weekly_trend()
        elif choice == "3":
            _show_activity_history()
        else:
            break


def _show_frequency():
    clr()
    header("FREQUENCY — LAST 30 DAYS")
    data = st.activity_frequency(30)
    if not data:
        console.print("[dim]No data.[/dim]")
        pause()
        return

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("Activity")
    table.add_column("Category")
    table.add_column("Sessions", justify="right")
    table.add_column("Total Sets", justify="right")
    table.add_column("Total Reps", justify="right")
    table.add_column("Total Min",  justify="right")

    for row in data:
        color = CATEGORY_COLORS.get(row["category"], "white")
        table.add_row(
            row["name"],
            f"[{color}]{row['category']}[/{color}]",
            str(row["count"]),
            str(row["total_sets"] or "—"),
            str(row["total_reps"] or "—"),
            f"{row['total_min']:.0f}" if row["total_min"] else "—",
        )
    console.print(table)
    pause()


def _show_weekly_trend():
    clr()
    header("WEEKLY TREND — LAST 8 WEEKS")
    data = st.weekly_volume(8)
    if not data:
        console.print("[dim]No data.[/dim]")
        pause()
        return

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("Week")
    table.add_column("Sessions",  justify="right")
    table.add_column("Days Active", justify="right")
    table.add_column("Exercises", justify="right")
    table.add_column("Volume bar")

    max_s = max(r["sessions"] for r in data) or 1
    for row in data:
        bar = "█" * int((row["sessions"] / max_s) * 20)
        table.add_row(
            row["week"],
            str(row["sessions"]),
            str(row["days_active"]),
            str(row["different_exercises"]),
            f"[cyan]{bar}[/cyan]",
        )
    console.print(table)
    pause()


def _show_activity_history():
    clr()
    header("ACTIVITY HISTORY")
    activity = pick_activity("Select activity")
    if not activity:
        return

    history = wk.for_activity(activity["id"], limit=15)
    if not history:
        console.print(f"[dim]No history for {activity['name']}.[/dim]")
        pause()
        return

    table = Table(
        show_header=True, header_style="bold", box=box.ROUNDED,
        title=f"{activity['name']} — last {len(history)} sessions",
    )
    table.add_column("Date")
    table.add_column("Sets",     justify="right")
    table.add_column("Reps",     justify="right")
    table.add_column("Weight",   justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Notes")

    for e in history:
        table.add_row(
            e["date"],
            _fmt_reps(e["sets"]),
            _fmt_reps(e["reps"]),
            _fmt_weight(e["weight_kg"]),
            _fmt_dur(e["duration_min"]),
            e["notes"] or "",
        )
    console.print(table)
    pause()


# ─── MANAGE ACTIVITIES ────────────────────────────────────────────────────────

def manage_activities_screen():
    while True:
        clr()
        header("MANAGE ACTIVITIES")
        activities = act.all_activities()

        table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Name")
        table.add_column("Category")
        table.add_column("Unit")

        for i, a in enumerate(activities, 1):
            color = CATEGORY_COLORS.get(a["category"], "white")
            table.add_row(
                str(i), a["name"],
                f"[{color}]{a['category']}[/{color}]",
                a["unit"],
            )
        console.print(table)
        console.print("\n[cyan]1[/cyan] Add new activity")
        console.print("[cyan]b[/cyan] Back\n")

        choice = Prompt.ask("Choice", choices=["1", "b"], default="b")
        if choice == "1":
            _add_activity()
        else:
            break


def _add_activity():
    name = Prompt.ask("Name")
    if not name.strip():
        return

    from activities import CATEGORIES, UNITS
    for i, c in enumerate(CATEGORIES, 1):
        console.print(f"  [cyan]{i}[/cyan] {c}")
    cat_idx  = int(Prompt.ask("Category", choices=[str(i) for i in range(1, len(CATEGORIES) + 1)])) - 1
    category = CATEGORIES[cat_idx]

    for i, u in enumerate(UNITS, 1):
        console.print(f"  [cyan]{i}[/cyan] {u}")
    unit_idx = int(Prompt.ask("Unit", choices=[str(i) for i in range(1, len(UNITS) + 1)])) - 1
    unit     = UNITS[unit_idx]

    act.add(name.strip(), category, unit)
    console.print(f"[green]'{name}' added![/green]")
    pause()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    db.init_db()
    act.seed()

    while True:
        clr()
        header()

        streak = st.streak()
        if streak > 0:
            console.print(
                f"\n  [bold yellow]Streak: {streak} day{'s' if streak != 1 else ''}[/bold yellow]"
            )

        console.print("\n[bold]MAIN MENU[/bold]\n")
        console.print("  [cyan]1[/cyan]  Log Workout")
        console.print("  [cyan]2[/cyan]  Today's Summary")
        console.print("  [cyan]3[/cyan]  Weekly Overview")
        console.print("  [cyan]4[/cyan]  Personal Records")
        console.print("  [cyan]5[/cyan]  Weekly Planner")
        console.print("  [cyan]6[/cyan]  Health Log")
        console.print("  [cyan]7[/cyan]  Statistics")
        console.print("  [cyan]8[/cyan]  Manage Activities")
        console.print("  [cyan]q[/cyan]  Quit\n")

        choice = Prompt.ask("Choice",
                            choices=["1", "2", "3", "4", "5", "6", "7", "8", "q"])

        handlers = {
            "1": log_workout_screen,
            "2": today_summary_screen,
            "3": weekly_overview_screen,
            "4": prs_screen,
            "5": planner_screen,
            "6": health_screen,
            "7": stats_screen,
            "8": manage_activities_screen,
        }

        if choice == "q":
            console.print("\n[dim]Stay consistent. See you tomorrow.[/dim]\n")
            sys.exit(0)

        handlers[choice]()


if __name__ == "__main__":
    main()

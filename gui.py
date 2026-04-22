import customtkinter as ctk
from datetime import date, timedelta
import sys

import db
import activities as act
import workouts as wk
import stats as st
import planner as plan
import health as hl

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FT  = ("Segoe UI", 12)
FTB = ("Segoe UI", 12, "bold")
FTT = ("Segoe UI", 20, "bold")
FTS = ("Segoe UI", 10)

def _w(v):  return f"{v}kg" if v else "—"
def _r(v):  return str(v) if v else "—"
def _d(v):  return f"{v:.0f}min" if v else "—"

def clear(frame):
    for w in frame.winfo_children():
        w.destroy()


# ─── Scrollable table helper ──────────────────────────────────────────────────

def make_table(parent, headers, rows, widths=None):
    sf = ctk.CTkScrollableFrame(parent, fg_color="transparent")

    for c, h in enumerate(headers):
        kw = dict(text=h, font=FTB, anchor="w")
        if widths:
            kw["width"] = widths[c]
        ctk.CTkLabel(sf, **kw).grid(row=0, column=c, padx=(4, 10), pady=(4, 2), sticky="w")

    ctk.CTkFrame(sf, height=1, fg_color=("gray60", "gray40")).grid(
        row=1, column=0, columnspan=len(headers), sticky="ew", padx=4, pady=2
    )

    for r, row in enumerate(rows, 2):
        for c, cell in enumerate(row):
            text, color = cell if isinstance(cell, tuple) else (cell, None)
            kw = dict(text=str(text), font=FT, anchor="w")
            if color:
                kw["text_color"] = color
            if widths:
                kw["width"] = widths[c]
            ctk.CTkLabel(sf, **kw).grid(row=r, column=c, padx=(4, 10), pady=1, sticky="w")

    return sf


def page_title(parent, text):
    ctk.CTkLabel(parent, text=text, font=FTT).pack(anchor="w", pady=(0, 12))


# ─── Main App ────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gym Tracker")
        self.geometry("1060x700")
        self.minsize(900, 600)
        self._build()
        self._nav("log")

    def _build(self):
        # ── Sidebar ──
        sb = ctk.CTkFrame(self, width=165, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        ctk.CTkLabel(sb, text="GYM\nTRACKER", font=("Segoe UI", 17, "bold")).pack(pady=(18, 4))
        ctk.CTkLabel(sb, text=date.today().strftime("%a %d %b"),
                     font=FTS, text_color="gray55").pack(pady=(0, 12))

        pages = [
            ("log",     "  Log Workout"),
            ("today",   "  Today"),
            ("weekly",  "  Weekly"),
            ("prs",     "  Records"),
            ("planner", "  Planner"),
            ("health",  "  Health"),
            ("stats",   "  Statistics"),
            ("manage",  "  Activities"),
        ]
        self._nav_btns = {}
        for key, label in pages:
            btn = ctk.CTkButton(
                sb, text=label, anchor="w",
                fg_color="transparent", hover_color=("gray70", "gray28"),
                font=("Segoe UI", 12),
                command=lambda k=key: self._nav(k),
            )
            btn.pack(fill="x", padx=6, pady=2)
            self._nav_btns[key] = btn

        self.streak_lbl = ctk.CTkLabel(sb, text="", font=FTS, text_color="#eab308")
        self.streak_lbl.pack(side="bottom", pady=14)

        # ── Content area ──
        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray92", "gray14"))
        self._content.pack(side="left", fill="both", expand=True)

    def _nav(self, key):
        for k, btn in self._nav_btns.items():
            btn.configure(fg_color="transparent" if k != key else ("gray75", "gray28"))

        clear(self._content)

        s = st.streak()
        self.streak_lbl.configure(text=f"  {s}d streak" if s > 1 else "")

        pages = {
            "log":     LogPage,
            "today":   TodayPage,
            "weekly":  WeeklyPage,
            "prs":     PRsPage,
            "planner": PlannerPage,
            "health":  HealthPage,
            "stats":   StatsPage,
            "manage":  ManagePage,
        }
        pages[key](self._content).pack(fill="both", expand=True, padx=18, pady=12)


# ─── Log Workout ─────────────────────────────────────────────────────────────

class LogPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Log Workout")

        self._activities = act.all_activities()
        self._act_map    = {a["name"]: a for a in self._activities}
        names = [a["name"] for a in self._activities]

        form = ctk.CTkFrame(self)
        form.pack(anchor="nw", pady=(0, 8))

        def lbl(text, row):
            ctk.CTkLabel(form, text=text, width=145, anchor="e").grid(
                row=row, column=0, padx=(10, 5), pady=6, sticky="e"
            )

        lbl("Activity:", 0)
        self.act_var = ctk.StringVar(value=names[0] if names else "")
        ctk.CTkComboBox(form, values=names, variable=self.act_var,
                        command=self._on_change, width=210).grid(
            row=0, column=1, padx=5, pady=6, sticky="w"
        )

        lbl("Weight (kg):", 1)
        self.e_weight = ctk.CTkEntry(form, width=130, placeholder_text="optional")
        self.e_weight.grid(row=1, column=1, padx=5, pady=6, sticky="w")

        lbl("Reps:", 2)
        self.e_reps = ctk.CTkEntry(form, width=130, placeholder_text="optional")
        self.e_reps.grid(row=2, column=1, padx=5, pady=6, sticky="w")

        lbl("Sets:", 3)
        self.e_sets = ctk.CTkEntry(form, width=130, placeholder_text="optional")
        self.e_sets.grid(row=3, column=1, padx=5, pady=6, sticky="w")

        lbl("Duration:", 4)
        dur_row = ctk.CTkFrame(form, fg_color="transparent")
        dur_row.grid(row=4, column=1, padx=5, pady=6, sticky="w")
        self.e_dur = ctk.CTkEntry(dur_row, width=100, placeholder_text="optional")
        self.e_dur.pack(side="left")
        self.dur_lbl = ctk.CTkLabel(dur_row, text="min", font=FTS, text_color="gray55")
        self.dur_lbl.pack(side="left", padx=4)

        lbl("Notes:", 5)
        self.e_notes = ctk.CTkEntry(form, width=310, placeholder_text="optional")
        self.e_notes.grid(row=5, column=1, columnspan=2, padx=5, pady=6, sticky="w")

        ctk.CTkButton(self, text="LOG WORKOUT", command=self._log,
                      font=FTB, height=38, width=180).pack(anchor="w", pady=8)

        self.result = ctk.CTkLabel(self, text="", font=FTB, wraplength=600)
        self.result.pack(anchor="w")

        if names:
            self._on_change(names[0])

    def _on_change(self, name):
        a = self._act_map.get(name)
        if not a:
            return
        unit = a["unit"]
        hints = {
            "kg":     ("e.g. 24", "e.g. 10", "e.g. 4", "optional", "min"),
            "reps":   ("optional", "e.g. 12", "e.g. 3", "optional", "min"),
            "sec":    ("optional", "optional", "optional", "e.g. 60", "sec"),
            "min":    ("optional", "optional", "optional", "e.g. 30", "min"),
            "rounds": ("optional", "optional", "e.g. 3", "e.g. 5", "rounds"),
            "sets":   ("optional", "e.g. 10", "e.g. 3", "optional", "min"),
        }
        w, r, s, d, du = hints.get(unit, ("optional",) * 4 + ("min",))
        self.e_weight.configure(placeholder_text=w)
        self.e_reps.configure(placeholder_text=r)
        self.e_sets.configure(placeholder_text=s)
        self.e_dur.configure(placeholder_text=d)
        self.dur_lbl.configure(text=du)

    def _gf(self, e):
        try:    return float(e.get().strip()) if e.get().strip() else None
        except: return None

    def _gi(self, e):
        try:    return int(float(e.get().strip())) if e.get().strip() else None
        except: return None

    def _log(self):
        name = self.act_var.get()
        a    = self._act_map.get(name)
        if not a:
            return

        dur_raw = self._gf(self.e_dur)
        dur_min = (dur_raw / 60) if (dur_raw and a["unit"] == "sec") else dur_raw

        new_prs = wk.log(
            a["id"],
            sets=self._gi(self.e_sets), reps=self._gi(self.e_reps),
            weight_kg=self._gf(self.e_weight), duration_min=dur_min,
            notes=self.e_notes.get().strip() or None,
        )
        for e in [self.e_weight, self.e_reps, self.e_sets, self.e_dur, self.e_notes]:
            e.delete(0, "end")

        if new_prs:
            self.result.configure(text="  " + "  |  ".join(new_prs), text_color="#eab308")
        else:
            self.result.configure(text=f"  {name} logged!", text_color="#22c55e")


# ─── Today's Summary ─────────────────────────────────────────────────────────

class TodayPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, f"Today — {date.today().strftime('%A, %d %b')}")

        today   = date.today().isoformat()
        entries = wk.for_date(today)
        h       = hl.get_for_date(today)

        if not entries:
            ctk.CTkLabel(self, text="No workouts logged today.",
                         text_color="gray55", font=FT).pack(anchor="w")
        else:
            headers = ["Activity", "Sets", "Reps", "Weight", "Duration", "Notes"]
            widths  = [140, 55, 55, 85, 85, 220]
            rows = [
                [e["activity_name"], _r(e["sets"]), _r(e["reps"]),
                 _w(e["weight_kg"]), _d(e["duration_min"]), e["notes"] or ""]
                for e in entries
            ]
            make_table(self, headers, rows, widths).pack(fill="both", expand=True)
            ctk.CTkLabel(self, text=f"  Sessions: {len(entries)}",
                         font=FTS, text_color="gray55").pack(anchor="w", pady=(4, 0))

        if h:
            info = ctk.CTkFrame(self)
            info.pack(anchor="w", pady=12, fill="x")
            ctk.CTkLabel(info, text="Health today", font=FTB).grid(
                row=0, column=0, columnspan=8, padx=12, pady=(8, 2), sticky="w"
            )
            pairs = [
                ("Weight",  _w(h["weight_kg"])),
                ("Sleep",   f"{h['sleep_h']}h" if h["sleep_h"] else "—"),
                ("Energy",  f"{h['energy']}/10" if h["energy"] else "—"),
                ("Pain",    h["pain_notes"] or "none"),
            ]
            for i, (k, v) in enumerate(pairs):
                ctk.CTkLabel(info, text=f"{k}:", font=FTS, text_color="gray55").grid(
                    row=1, column=i * 2, padx=(12, 2), pady=(2, 8))
                ctk.CTkLabel(info, text=v, font=FTB).grid(
                    row=1, column=i * 2 + 1, padx=(0, 18), pady=(2, 8))


# ─── Weekly Overview ─────────────────────────────────────────────────────────

class WeeklyPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        today = date.today()
        ws    = (today - timedelta(days=today.weekday())).isoformat()
        page_title(self, f"Weekly Overview — week of {ws}")

        entries   = wk.for_week(ws)
        plan_rows = plan.get_plan(ws)

        if not entries:
            ctk.CTkLabel(self, text="No workouts this week yet.",
                         text_color="gray55", font=FT).pack(anchor="w")
        else:
            days_seen = {}
            rows = []
            for e in entries:
                dn = date.fromisoformat(e["date"]).strftime("%A")
                rows.append([
                    ("" if dn in days_seen else dn, None),
                    e["activity_name"], _r(e["sets"]), _r(e["reps"]),
                    _w(e["weight_kg"]), _d(e["duration_min"]),
                ])
                days_seen[dn] = True

            ctk.CTkLabel(self, text=f"  Days active: {len(days_seen)}/7  |  Sessions: {len(entries)}",
                         font=FTS, text_color="gray55").pack(anchor="w", pady=(0, 6))
            make_table(self, ["Day","Activity","Sets","Reps","Weight","Duration"],
                       rows, [100,130,55,55,80,80]).pack(fill="both", expand=True)

        if plan_rows:
            ctk.CTkLabel(self, text="Plan vs Actual", font=FTB).pack(anchor="w", pady=(10, 4))
            actual_by_day = {}
            for e in entries:
                di = date.fromisoformat(e["date"]).weekday()
                actual_by_day.setdefault(di, set()).add(e["activity_id"])

            plan_by_day = {}
            for p in plan_rows:
                plan_by_day.setdefault(p["day_index"], []).append(p)

            DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            pv_rows = []
            for di, dp in sorted(plan_by_day.items()):
                done_ids  = actual_by_day.get(di, set())
                done_n    = sum(1 for p in dp if p["activity_id"] in done_ids)
                total     = len(dp)
                planned   = ", ".join(p["activity_name"] for p in dp)
                if done_n == total:
                    status = ("✓", "#22c55e")
                elif done_n > 0:
                    status = (f"{done_n}/{total}", "#eab308")
                else:
                    status = ("✗", "#ef4444")
                pv_rows.append([DAYS[di], planned, status])

            make_table(self, ["Day","Planned","Status"], pv_rows,
                       [100, 260, 60]).pack(fill="x")


# ─── Personal Records ────────────────────────────────────────────────────────

class PRsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Personal Records")

        prs = st.get_prs()
        if not prs:
            ctk.CTkLabel(self, text="No records yet. Start logging!",
                         text_color="gray55", font=FT).pack(anchor="w")
            return

        headers = ["Activity", "Category", "Best Weight", "Best Reps", "Best Duration", "Volume", "Date"]
        widths  = [130, 100, 105, 90, 115, 80, 100]
        rows = [
            [pr["name"], pr["category"],
             _w(pr["best_weight_kg"]), _r(pr["best_reps"]),
             _d(pr["best_duration_min"]),
             str(int(pr["best_volume"])) if pr["best_volume"] else "—",
             pr["pr_date"]]
            for pr in prs
        ]
        make_table(self, headers, rows, widths).pack(fill="both", expand=True)


# ─── Planner ─────────────────────────────────────────────────────────────────

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

class PlannerPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Weekly Planner")

        today  = date.today()
        self._ws = (today - timedelta(days=today.weekday())).isoformat()
        ctk.CTkLabel(self, text=f"Week of {self._ws}",
                     font=FTS, text_color="gray55").pack(anchor="w")

        self._plan_area = ctk.CTkFrame(self, fg_color="transparent")
        self._plan_area.pack(fill="both", expand=True, pady=(6, 0))
        self._refresh()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(anchor="w", pady=8)
        ctk.CTkButton(btn_row, text="+ Add Entry", command=self._add_dlg, width=120).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Copy Last Week", command=self._copy_last,
                      width=140, fg_color="gray35", hover_color="gray28").pack(side="left")

    def _refresh(self):
        clear(self._plan_area)
        rows_data = plan.get_plan(self._ws)
        if not rows_data:
            ctk.CTkLabel(self._plan_area, text="No plan set for this week.",
                         text_color="gray55", font=FT).pack(anchor="w")
            return
        day_seen = {}
        rows = []
        for p in rows_data:
            dn = DAYS[p["day_index"]]
            rows.append([
                ("" if dn in day_seen else dn, None),
                p["activity_name"], _r(p["target_sets"]), _r(p["target_reps"]),
                _w(p["target_kg"]), _d(p["target_min"]), p["notes"] or "",
            ])
            day_seen[dn] = True
        make_table(self._plan_area,
                   ["Day","Activity","Sets","Reps","Weight","Duration","Notes"],
                   rows, [100,130,55,55,80,80,150]).pack(fill="both", expand=True)

    def _add_dlg(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Add Plan Entry")
        dlg.geometry("400x380")
        dlg.grab_set()

        activities = act.all_activities()
        act_names  = [a["name"] for a in activities]
        act_map    = {a["name"]: a for a in activities}

        def lbl(text, row):
            ctk.CTkLabel(dlg, text=text, width=145, anchor="e").grid(
                row=row, column=0, padx=(10, 5), pady=7, sticky="e")

        lbl("Day:", 0)
        day_var = ctk.StringVar(value=DAYS[0])
        ctk.CTkComboBox(dlg, values=DAYS, variable=day_var, width=180).grid(
            row=0, column=1, padx=5, pady=7, sticky="w")

        lbl("Activity:", 1)
        act_var = ctk.StringVar(value=act_names[0] if act_names else "")
        ctk.CTkComboBox(dlg, values=act_names, variable=act_var, width=180).grid(
            row=1, column=1, padx=5, pady=7, sticky="w")

        fields = [("Target Sets:", 2), ("Target Reps:", 3),
                  ("Target Weight (kg):", 4), ("Target Duration (min):", 5), ("Notes:", 6)]
        entries = []
        for label, row in fields:
            lbl(label, row)
            e = ctk.CTkEntry(dlg, width=160, placeholder_text="optional")
            e.grid(row=row, column=1, padx=5, pady=7, sticky="w")
            entries.append(e)
        e_sets, e_reps, e_kg, e_min, e_notes = entries

        def gi(e):
            try:    return int(float(e.get().strip())) if e.get().strip() else None
            except: return None
        def gf(e):
            try:    return float(e.get().strip()) if e.get().strip() else None
            except: return None

        def save():
            a = act_map.get(act_var.get())
            if not a:
                return
            plan.set_entry(self._ws, DAYS.index(day_var.get()), a["id"],
                           target_sets=gi(e_sets), target_reps=gi(e_reps),
                           target_kg=gf(e_kg), target_min=gf(e_min),
                           notes=e_notes.get().strip() or None)
            dlg.destroy()
            self._refresh()

        ctk.CTkButton(dlg, text="Save", command=save, width=120).grid(
            row=7, column=0, columnspan=2, pady=14)

    def _copy_last(self):
        today   = date.today()
        last_ws = (today - timedelta(days=today.weekday() + 7)).isoformat()
        plan.copy_plan(last_ws, self._ws)
        self._refresh()


# ─── Health ──────────────────────────────────────────────────────────────────

class HealthPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Health Log")

        today    = date.today().isoformat()
        existing = hl.get_for_date(today)

        def defval(field):
            v = existing[field] if existing else None
            return str(v) if v is not None else ""

        form = ctk.CTkFrame(self)
        form.pack(anchor="nw", pady=(0, 8))

        def lbl(text, row):
            ctk.CTkLabel(form, text=text, width=155, anchor="e").grid(
                row=row, column=0, padx=(10, 5), pady=6, sticky="e")

        lbl("Weight (kg):", 0);       self.e_wt   = ctk.CTkEntry(form, width=130, placeholder_text="e.g. 78.5")
        lbl("Sleep (hours):", 1);     self.e_sl   = ctk.CTkEntry(form, width=130, placeholder_text="e.g. 7.5")
        lbl("Energy (1–10):", 2);     self.e_en   = ctk.CTkEntry(form, width=130, placeholder_text="e.g. 8")
        lbl("Pain/discomfort:", 3);   self.e_pain = ctk.CTkEntry(form, width=300, placeholder_text="e.g. slight left knee")
        lbl("Notes:", 4);             self.e_notes= ctk.CTkEntry(form, width=300, placeholder_text="optional")

        for row, entry in enumerate([self.e_wt, self.e_sl, self.e_en, self.e_pain, self.e_notes]):
            entry.grid(row=row, column=1, padx=5, pady=6, sticky="w")

        for entry, field in [(self.e_wt,"weight_kg"),(self.e_sl,"sleep_h"),
                             (self.e_en,"energy"),(self.e_pain,"pain_notes"),(self.e_notes,"notes")]:
            v = defval(field)
            if v:
                entry.insert(0, v)

        ctk.CTkButton(self, text="Save", command=self._save,
                      font=FTB, height=36, width=140).pack(anchor="w", pady=8)
        self.save_lbl = ctk.CTkLabel(self, text="", font=FTB)
        self.save_lbl.pack(anchor="w")

        ctk.CTkLabel(self, text="Last 30 days", font=FTB).pack(anchor="w", pady=(10, 4))
        records = hl.get_recent(30)
        if records:
            rows = []
            for rec in records:
                e   = rec["energy"] or 0
                col = "#22c55e" if e >= 7 else "#eab308" if e >= 4 else "#ef4444"
                rows.append([rec["date"], _w(rec["weight_kg"]),
                             f"{rec['sleep_h']}h" if rec["sleep_h"] else "—",
                             (f"{e}/10" if e else "—", col if e else None),
                             rec["pain_notes"] or rec["notes"] or ""])
            make_table(self, ["Date","Weight","Sleep","Energy","Pain/Notes"],
                       rows, [100,80,70,70,260]).pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(self, text="No health records yet.",
                         text_color="gray55", font=FT).pack(anchor="w")

    def _save(self):
        def gf(e):
            try:    return float(e.get().strip()) if e.get().strip() else None
            except: return None
        def gi(e):
            try:    return int(float(e.get().strip())) if e.get().strip() else None
            except: return None

        hl.log(weight_kg=gf(self.e_wt), sleep_h=gf(self.e_sl),
               energy=gi(self.e_en),
               pain_notes=self.e_pain.get().strip() or None,
               notes=self.e_notes.get().strip() or None)
        self.save_lbl.configure(text="  Saved!", text_color="#22c55e")


# ─── Statistics ──────────────────────────────────────────────────────────────

class StatsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Statistics")

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True)

        # ── Frequency tab ──
        tabs.add("Frequency (30d)")
        ft = tabs.tab("Frequency (30d)")
        data = st.activity_frequency(30)
        if data:
            rows = [[r["name"], r["category"], str(r["count"]),
                     str(r["total_sets"] or "—"),
                     str(r["total_reps"] or "—"),
                     f"{r['total_min']:.0f}" if r["total_min"] else "—"]
                    for r in data]
            make_table(ft, ["Activity","Category","Sessions","Total Sets","Total Reps","Total Min"],
                       rows, [130,100,80,90,90,80]).pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(ft, text="No data yet.", text_color="gray55").pack(anchor="w", padx=10, pady=10)

        # ── Weekly trend tab ──
        tabs.add("Weekly Trend")
        wt = tabs.tab("Weekly Trend")
        wdata = st.weekly_volume(8)
        if wdata:
            max_s = max(r["sessions"] for r in wdata) or 1
            rows  = [[r["week"], str(r["sessions"]), str(r["days_active"]),
                      str(r["different_exercises"]),
                      ("█" * int((r["sessions"] / max_s) * 22), "#3b82f6")]
                     for r in wdata]
            make_table(wt, ["Week","Sessions","Days","Exercises","Volume"],
                       rows, [100,80,60,90,220]).pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(wt, text="No data yet.", text_color="gray55").pack(anchor="w", padx=10, pady=10)


# ─── Manage Activities ────────────────────────────────────────────────────────

class ManagePage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Manage Activities")

        self._list = ctk.CTkFrame(self, fg_color="transparent")
        self._list.pack(fill="both", expand=True)
        self._show_list()

        ctk.CTkButton(self, text="+ Add Activity", command=self._add_dlg,
                      width=150).pack(anchor="w", pady=8)

    def _show_list(self):
        clear(self._list)
        activities = act.all_activities()
        rows = [[str(i), a["name"], a["category"], a["unit"]]
                for i, a in enumerate(activities, 1)]
        make_table(self._list, ["#","Name","Category","Unit"],
                   rows, [36,150,120,80]).pack(fill="both", expand=True)

    def _add_dlg(self):
        from activities import CATEGORIES, UNITS
        dlg = ctk.CTkToplevel(self)
        dlg.title("Add Activity")
        dlg.geometry("360x260")
        dlg.grab_set()

        def lbl(text, row):
            ctk.CTkLabel(dlg, text=text, width=120, anchor="e").grid(
                row=row, column=0, padx=(10, 5), pady=8, sticky="e")

        lbl("Name:", 0)
        e_name = ctk.CTkEntry(dlg, width=180)
        e_name.grid(row=0, column=1, padx=5, pady=8, sticky="w")

        lbl("Category:", 1)
        cat_var = ctk.StringVar(value=CATEGORIES[0])
        ctk.CTkComboBox(dlg, values=CATEGORIES, variable=cat_var, width=180).grid(
            row=1, column=1, padx=5, pady=8, sticky="w")

        lbl("Unit:", 2)
        unit_var = ctk.StringVar(value=UNITS[0])
        ctk.CTkComboBox(dlg, values=UNITS, variable=unit_var, width=180).grid(
            row=2, column=1, padx=5, pady=8, sticky="w")

        msg = ctk.CTkLabel(dlg, text="")
        msg.grid(row=3, column=0, columnspan=2)

        def save():
            name = e_name.get().strip()
            if not name:
                msg.configure(text="Name is required.", text_color="#ef4444")
                return
            act.add(name, cat_var.get(), unit_var.get())
            dlg.destroy()
            self._show_list()

        ctk.CTkButton(dlg, text="Add", command=save, width=120).grid(
            row=4, column=0, columnspan=2, pady=12)


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    db.init_db()
    act.seed()
    App().mainloop()


if __name__ == "__main__":
    main()

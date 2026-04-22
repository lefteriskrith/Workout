import customtkinter as ctk
from datetime import date, timedelta
import sys

import db
import activities as act
import workouts as wk
import stats as st
import planner as plan
import health as hl
import templates as tmpl

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── Palette ───────────────────────────────────────────────────────────────────
ORANGE     = "#F97316"
ORANGE_DK  = "#C05400"
CARD       = ("gray87", "#1E1E22")
TEXT_MUTED = "gray55"
GREEN      = "#22c55e"
RED        = "#ef4444"
BLUE       = "#3b82f6"

FT  = ("Segoe UI", 12)
FTB = ("Segoe UI", 12, "bold")
FTT = ("Segoe UI", 20, "bold")
FTS = ("Segoe UI", 10)


# ── Helpers ───────────────────────────────────────────────────────────────────

def clear(frame):
    for w in frame.winfo_children():
        w.destroy()


def page_title(parent, text):
    ctk.CTkLabel(parent, text=text, font=FTT).pack(anchor="w", pady=(0, 10))


def _fmt_done(d):
    parts = []
    if d["sets"] > 1:    parts.append(f"{d['sets']} sets")
    if d["max_weight"]:  parts.append(f"{d['max_weight']}kg")
    if d["max_reps"]:    parts.append(f"x {d['max_reps']}")
    if d["total_dur"]:   parts.append(f"{d['total_dur']:.0f}min")
    return "  ".join(parts) if parts else "done"


def make_table(parent, headers, rows, widths=None):
    sf = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    for c, h in enumerate(headers):
        kw = dict(text=h, font=FTB, anchor="w")
        if widths:
            kw["width"] = widths[c]
        ctk.CTkLabel(sf, **kw).grid(row=0, column=c, padx=(4, 10), pady=(4, 2), sticky="w")
    ctk.CTkFrame(sf, height=1, fg_color=("gray60", "gray35")).grid(
        row=1, column=0, columnspan=len(headers), sticky="ew", padx=4, pady=2)
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


# ── SetRow ────────────────────────────────────────────────────────────────────

class SetRow:
    def __init__(self, parent, num, unit, prev=None, on_del=None, on_change=None):
        self._unit = unit
        self._del  = on_del
        self._change = on_change
        self.frame = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=6)
        self.num_lbl = None
        self.e_weight = self.e_reps = self.e_dur = self.e_rpe = None
        self._build(num, prev)

    def _build(self, num, prev):
        f   = self.frame
        pw  = prev[0] if prev else None
        pr  = prev[1] if prev else None
        prpe = prev[2] if prev else None
        pd  = prev[3] if prev else None

        self.num_lbl = ctk.CTkLabel(f, text=str(num), width=28,
                                     font=FTB, text_color=ORANGE)
        self.num_lbl.grid(row=0, column=0, padx=(10, 4), pady=8)

        if self._unit == "kg":
            prev_txt = f"{pw}kg x{pr}" if pw and pr else (f"{pw}kg" if pw else (f"x{pr}" if pr else "-"))
        elif self._unit in ("sec", "min", "rounds"):
            prev_txt = f"{pd:.0f}{'s' if self._unit=='sec' else 'm'}" if pd else "-"
        else:
            prev_txt = f"x{pr}" if pr else "-"

        ctk.CTkLabel(f, text=prev_txt, width=80, font=FTS,
                     text_color=TEXT_MUTED, anchor="w").grid(row=0, column=1, padx=4, pady=8)

        col = 2
        if self._unit == "kg":
            self.e_weight = ctk.CTkEntry(f, width=72, placeholder_text="kg")
            if pw: self.e_weight.insert(0, str(pw))
            self.e_weight.grid(row=0, column=col, padx=4, pady=8)
            self.e_weight.bind("<KeyRelease>", lambda _: self._fire())
            col += 1
            self.e_reps = ctk.CTkEntry(f, width=58, placeholder_text="reps")
            if pr: self.e_reps.insert(0, str(pr))
            self.e_reps.grid(row=0, column=col, padx=4, pady=8)
            self.e_reps.bind("<KeyRelease>", lambda _: self._fire())
            col += 1

        elif self._unit in ("reps", "sets"):
            self.e_reps = ctk.CTkEntry(f, width=70, placeholder_text="reps")
            if pr: self.e_reps.insert(0, str(pr))
            self.e_reps.grid(row=0, column=col, padx=4, pady=8)
            self.e_reps.bind("<KeyRelease>", lambda _: self._fire())
            col += 1

        elif self._unit in ("sec", "min", "rounds"):
            self.e_dur = ctk.CTkEntry(f, width=80, placeholder_text=self._unit)
            if pd:
                v = pd * 60 if self._unit == "sec" else pd
                self.e_dur.insert(0, str(int(v)))
            self.e_dur.grid(row=0, column=col, padx=4, pady=8)
            col += 1

        self.e_rpe = ctk.CTkEntry(f, width=48, placeholder_text="RPE")
        if prpe: self.e_rpe.insert(0, str(prpe))
        self.e_rpe.grid(row=0, column=col, padx=4, pady=8)
        col += 1

        if self._del:
            ctk.CTkButton(f, text="x", width=26, height=26,
                          fg_color="transparent", hover_color=RED,
                          text_color=TEXT_MUTED, font=FTS,
                          command=self._del).grid(row=0, column=col, padx=(2, 8), pady=8)

    def _fire(self):
        if self._change:
            self._change()

    def get_data(self):
        def gf(e):
            if not e: return None
            try: return float(e.get().strip()) if e.get().strip() else None
            except: return None
        def gi(e):
            if not e: return None
            try: return int(float(e.get().strip())) if e.get().strip() else None
            except: return None

        dur_raw = gf(self.e_dur)
        dur_min = (dur_raw / 60) if (dur_raw and self._unit == "sec") else dur_raw
        return {
            "weight_kg":    gf(self.e_weight),
            "reps":         gi(self.e_reps),
            "duration_min": dur_min,
            "rpe":          gi(self.e_rpe),
        }

    def pack(self, **kw):
        self.frame.pack(**kw)

    def destroy(self):
        self.frame.destroy()


# ── RestTimer ─────────────────────────────────────────────────────────────────

class RestTimer(ctk.CTkFrame):
    PRESETS = [("60s", 60), ("90s", 90), ("2m", 120), ("3m", 180)]

    def __init__(self, parent):
        super().__init__(parent, fg_color=CARD, corner_radius=10)
        self._secs    = 90
        self._running = False
        self._build()
        self._update_display()

    def _build(self):
        ctk.CTkLabel(self, text="REST TIMER", font=FTS,
                     text_color=TEXT_MUTED).pack(anchor="w", padx=10, pady=(8, 2))

        pre = ctk.CTkFrame(self, fg_color="transparent")
        pre.pack(padx=8, pady=(0, 2))
        for label, secs in self.PRESETS:
            ctk.CTkButton(pre, text=label, width=42, height=24,
                          fg_color="gray28", hover_color="gray22", font=FTS,
                          command=lambda s=secs: self._load(s)).pack(side="left", padx=2)

        self.time_lbl = ctk.CTkLabel(self, text="01:30",
                                      font=("Segoe UI", 28, "bold"))
        self.time_lbl.pack(pady=(2, 4))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=(0, 10))
        self.toggle_btn = ctk.CTkButton(btns, text="Start", width=78, height=28,
                                         fg_color=ORANGE, hover_color=ORANGE_DK,
                                         font=FTS, command=self._toggle)
        self.toggle_btn.pack(side="left", padx=3)
        ctk.CTkButton(btns, text="Reset", width=60, height=28,
                      fg_color="gray28", hover_color="gray22",
                      font=FTS, command=self._reset).pack(side="left", padx=2)

    def _load(self, secs):
        self._running = False
        self.toggle_btn.configure(text="Start")
        self._secs = secs
        self._update_display()

    def _toggle(self):
        if self._running:
            self._running = False
            self.toggle_btn.configure(text="Resume")
        else:
            self._running = True
            self.toggle_btn.configure(text="Pause")
            self._tick()

    def _reset(self):
        self._running = False
        self.toggle_btn.configure(text="Start")
        self._update_display()

    def _tick(self):
        if not self._running:
            return
        if self._secs > 0:
            self._secs -= 1
            self._update_display()
            self.after(1000, self._tick)
        else:
            self._running = False
            self.toggle_btn.configure(text="Start")
            self._beep()

    def _update_display(self):
        m, s = divmod(self._secs, 60)
        self.time_lbl.configure(
            text=f"{m:02d}:{s:02d}",
            text_color=RED if 0 < self._secs <= 10 else "white",
        )

    def _beep(self):
        try:
            import winsound
            for _ in range(3):
                winsound.Beep(880, 300)
        except Exception:
            pass


# ── LogPage ───────────────────────────────────────────────────────────────────

class LogPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._activities    = act.all_activities()
        self._act_map       = {a["name"]: a for a in self._activities}
        self._set_rows      = []
        self._current_unit  = "reps"
        self._build()

    def _build(self):
        page_title(self, "Log Workout")

        # ── Exercise selector ──
        top = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        top.pack(fill="x", pady=(0, 8))
        inner = ctk.CTkFrame(top, fg_color="transparent")
        inner.pack(padx=14, pady=10, fill="x")
        ctk.CTkLabel(inner, text="EXERCISE", font=FTS, text_color=TEXT_MUTED).pack(anchor="w")

        sel = ctk.CTkFrame(inner, fg_color="transparent")
        sel.pack(anchor="w", fill="x", pady=(4, 0))

        names = [a["name"] for a in self._activities]
        self.act_var = ctk.StringVar(value=names[0] if names else "")
        ctk.CTkComboBox(sel, values=names, variable=self.act_var,
                        command=self._on_act, width=220, height=34,
                        font=("Segoe UI", 13)).pack(side="left")
        self.last_lbl = ctk.CTkLabel(sel, text="", font=FTS, text_color=TEXT_MUTED)
        self.last_lbl.pack(side="left", padx=12)
        self.orm_lbl = ctk.CTkLabel(sel, text="", font=FTB, text_color=ORANGE)
        self.orm_lbl.pack(side="left", padx=4)

        # ── Set-rows section (strength / bodyweight) ──
        self._sets_section = ctk.CTkFrame(self, fg_color="transparent")

        hdr = ctk.CTkFrame(self._sets_section, fg_color="transparent")
        hdr.pack(fill="x", padx=2, pady=(0, 2))
        for c, (txt, w) in enumerate([("SET", 28), ("PREV", 80), ("KG", 72), ("REPS", 58), ("RPE", 48)]):
            ctk.CTkLabel(hdr, text=txt, width=w, font=FTS,
                         text_color=TEXT_MUTED, anchor="w").grid(
                row=0, column=c, padx=(10 if c == 0 else 4, 4), sticky="w")

        self._rows_sf = ctk.CTkScrollableFrame(
            self._sets_section, fg_color="transparent", height=180)
        self._rows_sf.pack(fill="x")

        add_row = ctk.CTkFrame(self._sets_section, fg_color="transparent")
        add_row.pack(anchor="w", pady=(4, 0))
        ctk.CTkButton(add_row, text="+ Add Set", width=100, height=28,
                      fg_color="gray28", hover_color="gray22", font=FTS,
                      command=lambda: self._add_row()).pack(side="left")

        # ── Simple cardio section ──
        self._simple_section = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        sf = ctk.CTkFrame(self._simple_section, fg_color="transparent")
        sf.pack(padx=14, pady=10)

        def slbl(text, row):
            ctk.CTkLabel(sf, text=text, width=135, anchor="e").grid(
                row=row, column=0, padx=(0, 8), pady=6, sticky="e")

        slbl("Duration:", 0)
        self.e_dur = ctk.CTkEntry(sf, width=90, placeholder_text="value")
        self.e_dur.grid(row=0, column=1, pady=6, sticky="w")
        self.dur_unit_lbl = ctk.CTkLabel(sf, text="min", font=FTS, text_color=TEXT_MUTED)
        self.dur_unit_lbl.grid(row=0, column=2, padx=4, sticky="w")
        slbl("Rounds / Sets:", 1)
        self.e_s_sets = ctk.CTkEntry(sf, width=80, placeholder_text="optional")
        self.e_s_sets.grid(row=1, column=1, pady=6, sticky="w")
        slbl("RPE (1-10):", 2)
        self.e_s_rpe = ctk.CTkEntry(sf, width=80, placeholder_text="optional")
        self.e_s_rpe.grid(row=2, column=1, pady=6, sticky="w")

        # ── Notes ──
        nr = ctk.CTkFrame(self, fg_color="transparent")
        nr.pack(anchor="w", pady=(8, 6))
        ctk.CTkLabel(nr, text="Notes:", font=FTS, text_color=TEXT_MUTED).pack(side="left", padx=(0, 8))
        self.e_notes = ctk.CTkEntry(nr, width=380, placeholder_text="optional")
        self.e_notes.pack(side="left")

        # ── Bottom bar ──
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.pack(fill="x", pady=4)
        left = ctk.CTkFrame(bot, fg_color="transparent")
        left.pack(side="left", fill="y")
        ctk.CTkButton(left, text="LOG SESSION", command=self._log,
                      fg_color=ORANGE, hover_color=ORANGE_DK,
                      font=("Segoe UI", 13, "bold"), height=40, width=160).pack(anchor="w")
        self.result_lbl = ctk.CTkLabel(left, text="", font=FTB, wraplength=450)
        self.result_lbl.pack(anchor="w", pady=(6, 0))
        RestTimer(bot).pack(side="right", anchor="ne", padx=(14, 0))

        if names:
            self._on_act(names[0])

    def _on_act(self, name):
        a = self._act_map.get(name)
        if not a:
            return
        self._current_unit = a["unit"]

        last_date, prev_sets = wk.last_session_sets(a["id"])
        if last_date:
            self.last_lbl.configure(
                text=f"Last: {last_date}  ({len(prev_sets)} set{'s' if len(prev_sets)!=1 else ''})")
        else:
            self.last_lbl.configure(text="No previous sessions")
        self.orm_lbl.configure(text="")

        if a["unit"] in ("kg", "reps", "sets"):
            self._simple_section.pack_forget()
            self._sets_section.pack(fill="x", pady=(0, 6))
            self._clear_rows()
            for i in range(max(len(prev_sets), 3)):
                self._add_row(prev_sets[i] if i < len(prev_sets) else None)
        else:
            self._sets_section.pack_forget()
            self._simple_section.pack(fill="x", pady=(0, 6))
            self.dur_unit_lbl.configure(text=a["unit"])
            if prev_sets:
                ps = prev_sets[0]
                if ps[3]:
                    v = ps[3] * 60 if a["unit"] == "sec" else ps[3]
                    self.e_dur.delete(0, "end")
                    self.e_dur.insert(0, str(int(v)))

    def _clear_rows(self):
        for r in self._set_rows:
            r.destroy()
        self._set_rows.clear()

    def _add_row(self, prev=None):
        n = len(self._set_rows) + 1

        def delete_me():
            row.destroy()
            self._set_rows.remove(row)
            for i, r in enumerate(self._set_rows, 1):
                r.num_lbl.configure(text=str(i))

        row = SetRow(self._rows_sf, n, self._current_unit,
                     prev=prev,
                     on_del=delete_me if n > 1 else None,
                     on_change=self._update_1rm)
        row.pack(fill="x", padx=2, pady=3)
        self._set_rows.append(row)

    def _update_1rm(self):
        if self._current_unit != "kg":
            self.orm_lbl.configure(text="")
            return
        best = None
        for row in self._set_rows:
            d = row.get_data()
            if d["weight_kg"] and d["reps"]:
                rm = wk.calc_1rm(d["weight_kg"], d["reps"])
                if rm and (best is None or rm > best):
                    best = rm
        self.orm_lbl.configure(text=f"Est. 1RM ~{best}kg" if best else "")

    def _log(self):
        a = self._act_map.get(self.act_var.get())
        if not a:
            return
        notes = self.e_notes.get().strip() or None

        def gf(e):
            try: return float(e.get().strip()) if e.get().strip() else None
            except: return None
        def gi(e):
            try: return int(float(e.get().strip())) if e.get().strip() else None
            except: return None

        if a["unit"] in ("kg", "reps", "sets"):
            sets_data = [r.get_data() for r in self._set_rows
                         if any(v is not None for k, v in r.get_data().items() if k != "rpe")]
            if not sets_data:
                self.result_lbl.configure(text="Enter at least one set.", text_color=RED)
                return
            new_prs = wk.log_sets(a["id"], sets_data, notes=notes)
            n = len(sets_data)
        else:
            dur_raw = gf(self.e_dur)
            if not dur_raw:
                self.result_lbl.configure(text="Enter duration.", text_color=RED)
                return
            dur_min = dur_raw / 60 if a["unit"] == "sec" else dur_raw
            new_prs = wk.log_sets(a["id"], [{
                "weight_kg": None, "reps": gi(self.e_s_sets),
                "duration_min": dur_min, "rpe": gi(self.e_s_rpe),
            }], notes=notes)
            self.e_dur.delete(0, "end")
            self.e_s_sets.delete(0, "end")
            self.e_s_rpe.delete(0, "end")
            n = 1

        self.e_notes.delete(0, "end")
        if new_prs:
            self.result_lbl.configure(
                text="  " + "  |  ".join(new_prs), text_color=ORANGE)
        else:
            self.result_lbl.configure(
                text=f"  {a['name']} -- {n} set{'s' if n > 1 else ''} logged!",
                text_color=GREEN)


# ── TodayPage ────────────────────────────────────────────────────────────────

class TodayPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, f"Today -- {date.today().strftime('%A, %d %b')}")

        today   = date.today().isoformat()
        entries = wk.for_date_summary(today)
        h       = hl.get_for_date(today)

        if not entries:
            ctk.CTkLabel(self, text="No workouts logged today.",
                         text_color=TEXT_MUTED, font=FT).pack(anchor="w")
        else:
            headers = ["Exercise", "Sets", "Max Weight", "Max Reps", "Duration", "Avg RPE"]
            widths  = [140, 50, 95, 85, 85, 70]
            rows = [
                [e["activity_name"],
                 str(e["sets"]),
                 f"{e['max_weight']}kg" if e["max_weight"] else "--",
                 str(e["max_reps"]) if e["max_reps"] else "--",
                 f"{e['total_duration']:.0f}min" if e["total_duration"] else "--",
                 str(e["avg_rpe"]) if e["avg_rpe"] else "--"]
                for e in entries
            ]
            make_table(self, headers, rows, widths).pack(fill="both", expand=True)
            ctk.CTkLabel(self, text=f"  Exercises done: {len(entries)}",
                         font=FTS, text_color=TEXT_MUTED).pack(anchor="w", pady=(4, 0))

        if h:
            info = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
            info.pack(anchor="w", pady=10, fill="x")
            ctk.CTkLabel(info, text="Health today", font=FTB).grid(
                row=0, column=0, columnspan=8, padx=12, pady=(8, 2), sticky="w")
            pairs = [
                ("Weight",  f"{h['weight_kg']}kg" if h["weight_kg"] else "--"),
                ("Sleep",   f"{h['sleep_h']}h" if h["sleep_h"] else "--"),
                ("Energy",  f"{h['energy']}/10" if h["energy"] else "--"),
                ("Pain",    h["pain_notes"] or "--"),
            ]
            for i, (k, v) in enumerate(pairs):
                ctk.CTkLabel(info, text=f"{k}:", font=FTS, text_color=TEXT_MUTED).grid(
                    row=1, column=i * 2, padx=(12, 2), pady=(2, 10))
                ctk.CTkLabel(info, text=v, font=FTB).grid(
                    row=1, column=i * 2 + 1, padx=(0, 16), pady=(2, 10))


# ── WeeklyPage ────────────────────────────────────────────────────────────────

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class WeeklyPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        today = date.today()
        ws    = (today - timedelta(days=today.weekday())).isoformat()
        page_title(self, f"Weekly Overview -- {ws}")

        entries   = wk.for_week(ws)
        plan_rows = plan.get_plan(ws)

        # Aggregate logged: {day_idx: {activity_id: {...}}}
        logged = {}
        for e in entries:
            di  = date.fromisoformat(e["date"]).weekday()
            aid = e["activity_id"]
            logged.setdefault(di, {})
            if aid not in logged[di]:
                logged[di][aid] = {
                    "name": e["activity_name"], "unit": e["unit"],
                    "sets": 0, "max_weight": None, "max_reps": None, "total_dur": 0.0,
                }
            a = logged[di][aid]
            a["sets"] += 1
            if e["weight_kg"]:    a["max_weight"] = max(a["max_weight"] or 0, e["weight_kg"])
            if e["reps"]:         a["max_reps"]   = max(a["max_reps"]   or 0, e["reps"])
            if e["duration_min"]: a["total_dur"]  += e["duration_min"]

        plan_by_day = {}
        for p in plan_rows:
            plan_by_day.setdefault(p["day_index"], []).append(p)

        today_idx = today.weekday()

        sf = ctk.CTkScrollableFrame(self, fg_color="transparent")
        sf.pack(fill="both", expand=True)

        for di in range(7):
            day_name = DAYS[di]
            planned  = plan_by_day.get(di, [])
            done_map = logged.get(di, {})
            is_today = (di == today_idx)

            if not planned and not done_map:
                continue

            card = ctk.CTkFrame(sf, fg_color=CARD, corner_radius=10)
            card.pack(fill="x", padx=2, pady=5)

            # Header
            hdr = ctk.CTkFrame(card, fg_color="transparent")
            hdr.pack(fill="x", padx=12, pady=(10, 4))
            ctk.CTkLabel(hdr, text=day_name, font=FTB,
                         text_color=ORANGE if is_today else "white").pack(side="left")

            if planned:
                done_n = sum(1 for p in planned if p["activity_id"] in done_map)
                total  = len(planned)
                ratio  = done_n / total
                col    = GREEN if ratio == 1 else (ORANGE if ratio > 0 else TEXT_MUTED)
                ctk.CTkLabel(hdr, text=f"{done_n}/{total}",
                             font=FTS, text_color=col).pack(side="left", padx=8)
                pb = ctk.CTkProgressBar(hdr, width=110, height=7, corner_radius=4,
                                         progress_color=col)
                pb.set(ratio)
                pb.pack(side="left", padx=2)

            # Exercise rows
            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="x", padx=14, pady=(0, 10))

            planned_ids = set()
            for p in planned:
                aid = p["activity_id"]
                planned_ids.add(aid)
                done = done_map.get(aid)

                row = ctk.CTkFrame(body, fg_color="transparent")
                row.pack(fill="x", pady=2)

                if done:
                    ctk.CTkLabel(row, text="v", font=FTB, text_color=GREEN, width=20).pack(side="left")
                    detail = _fmt_done(done)
                else:
                    ctk.CTkLabel(row, text="x", font=FTB, text_color=RED, width=20).pack(side="left")
                    parts = []
                    if p["target_sets"]: parts.append(f"{p['target_sets']} sets")
                    if p["target_reps"]: parts.append(f"x {p['target_reps']}")
                    if p["target_kg"]:   parts.append(f"@ {p['target_kg']}kg")
                    if p["target_min"]:  parts.append(f"{p['target_min']:.0f}min")
                    detail = "  ".join(parts) if parts else "planned"

                ctk.CTkLabel(row, text=p["activity_name"],
                             font=FT, width=130, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=detail,
                             font=FTS, text_color=TEXT_MUTED).pack(side="left")

            # Unplanned extras
            for aid, done in done_map.items():
                if aid in planned_ids:
                    continue
                row = ctk.CTkFrame(body, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text="+", font=FTB, text_color=BLUE, width=20).pack(side="left")
                ctk.CTkLabel(row, text=done["name"],
                             font=FT, width=130, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=_fmt_done(done),
                             font=FTS, text_color=TEXT_MUTED).pack(side="left")


# ── PRsPage ───────────────────────────────────────────────────────────────────

class PRsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Personal Records")

        prs = st.get_prs()
        if not prs:
            ctk.CTkLabel(self, text="No records yet. Start logging!",
                         text_color=TEXT_MUTED, font=FT).pack(anchor="w")
            return

        headers = ["Exercise", "Category", "Best Weight", "Best Reps", "Best Duration", "Volume", "Date"]
        widths  = [130, 100, 105, 90, 115, 80, 100]
        rows = [
            [pr["name"], pr["category"],
             f"{pr['best_weight_kg']}kg" if pr["best_weight_kg"] else "--",
             str(pr["best_reps"]) if pr["best_reps"] else "--",
             f"{pr['best_duration_min']:.0f}min" if pr["best_duration_min"] else "--",
             str(int(pr["best_volume"])) if pr["best_volume"] else "--",
             pr["pr_date"]]
            for pr in prs
        ]
        make_table(self, headers, rows, widths).pack(fill="both", expand=True)


# ── PlannerPage ───────────────────────────────────────────────────────────────

class PlannerPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Weekly Planner")

        today    = date.today()
        self._ws = (today - timedelta(days=today.weekday())).isoformat()
        ctk.CTkLabel(self, text=f"Week of {self._ws}",
                     font=FTS, text_color=TEXT_MUTED).pack(anchor="w")

        self._plan_area = ctk.CTkFrame(self, fg_color="transparent")
        self._plan_area.pack(fill="both", expand=True, pady=(6, 0))
        self._refresh()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(anchor="w", pady=8)
        ctk.CTkButton(btn_row, text="+ Add Entry", command=self._add_dlg,
                      fg_color=ORANGE, hover_color=ORANGE_DK, width=120).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Copy Last Week", command=self._copy_last,
                      width=140, fg_color="gray35", hover_color="gray28").pack(side="left")

    def _refresh(self):
        clear(self._plan_area)
        rows_data = plan.get_plan(self._ws)
        if not rows_data:
            ctk.CTkLabel(self._plan_area, text="No plan for this week.",
                         text_color=TEXT_MUTED, font=FT).pack(anchor="w")
            return
        day_seen = {}
        rows = []
        for p in rows_data:
            dn = DAYS[p["day_index"]]
            rows.append([
                ("" if dn in day_seen else dn, None),
                p["activity_name"],
                str(p["target_sets"]) if p["target_sets"] else "--",
                str(p["target_reps"]) if p["target_reps"] else "--",
                f"{p['target_kg']}kg" if p["target_kg"] else "--",
                f"{p['target_min']:.0f}min" if p["target_min"] else "--",
                p["notes"] or "",
            ])
            day_seen[dn] = True
        make_table(self._plan_area,
                   ["Day", "Exercise", "Sets", "Reps", "Weight", "Duration", "Notes"],
                   rows, [100, 130, 55, 55, 80, 80, 150]).pack(fill="both", expand=True)

    def _add_dlg(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Add Plan Entry")
        dlg.geometry("400x370")
        dlg.grab_set()

        activities = act.all_activities()
        act_names  = [a["name"] for a in activities]
        act_map    = {a["name"]: a for a in activities}

        def lbl(text, row):
            ctk.CTkLabel(dlg, text=text, width=150, anchor="e").grid(
                row=row, column=0, padx=(10, 5), pady=7, sticky="e")

        lbl("Day:", 0)
        day_var = ctk.StringVar(value=DAYS[0])
        ctk.CTkComboBox(dlg, values=DAYS, variable=day_var, width=180).grid(
            row=0, column=1, padx=5, pady=7, sticky="w")

        lbl("Exercise:", 1)
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
            try: return int(float(e.get().strip())) if e.get().strip() else None
            except: return None
        def gf(e):
            try: return float(e.get().strip()) if e.get().strip() else None
            except: return None

        def save():
            a = act_map.get(act_var.get())
            if not a: return
            plan.set_entry(self._ws, DAYS.index(day_var.get()), a["id"],
                           target_sets=gi(e_sets), target_reps=gi(e_reps),
                           target_kg=gf(e_kg), target_min=gf(e_min),
                           notes=e_notes.get().strip() or None)
            dlg.destroy()
            self._refresh()

        ctk.CTkButton(dlg, text="Save", command=save, fg_color=ORANGE,
                      hover_color=ORANGE_DK, width=120).grid(
            row=7, column=0, columnspan=2, pady=14)

    def _copy_last(self):
        today   = date.today()
        last_ws = (today - timedelta(days=today.weekday() + 7)).isoformat()
        plan.copy_plan(last_ws, self._ws)
        self._refresh()


# ── HealthPage ────────────────────────────────────────────────────────────────

class HealthPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Health Log")

        today    = date.today().isoformat()
        existing = hl.get_for_date(today)

        def defval(field):
            v = existing[field] if existing else None
            return str(v) if v is not None else ""

        form  = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        form.pack(anchor="nw", pady=(0, 8))
        inner = ctk.CTkFrame(form, fg_color="transparent")
        inner.pack(padx=14, pady=10)

        def lbl(text, row):
            ctk.CTkLabel(inner, text=text, width=155, anchor="e").grid(
                row=row, column=0, padx=(0, 8), pady=6, sticky="e")

        lbl("Weight (kg):", 0);      self.e_wt    = ctk.CTkEntry(inner, width=130, placeholder_text="e.g. 78.5")
        lbl("Sleep (hours):", 1);    self.e_sl    = ctk.CTkEntry(inner, width=130, placeholder_text="e.g. 7.5")
        lbl("Energy (1-10):", 2);    self.e_en    = ctk.CTkEntry(inner, width=130, placeholder_text="e.g. 8")
        lbl("Pain / discomfort:", 3); self.e_pain = ctk.CTkEntry(inner, width=300, placeholder_text="e.g. slight left knee")
        lbl("Notes:", 4);            self.e_notes = ctk.CTkEntry(inner, width=300, placeholder_text="optional")

        for row, entry in enumerate([self.e_wt, self.e_sl, self.e_en, self.e_pain, self.e_notes]):
            entry.grid(row=row, column=1, padx=5, pady=6, sticky="w")

        for entry, field in [(self.e_wt, "weight_kg"), (self.e_sl, "sleep_h"),
                             (self.e_en, "energy"), (self.e_pain, "pain_notes"), (self.e_notes, "notes")]:
            v = defval(field)
            if v:
                entry.insert(0, v)

        ctk.CTkButton(self, text="Save", command=self._save,
                      fg_color=ORANGE, hover_color=ORANGE_DK,
                      font=FTB, height=36, width=130).pack(anchor="w", pady=8)
        self.save_lbl = ctk.CTkLabel(self, text="", font=FTB)
        self.save_lbl.pack(anchor="w")

        ctk.CTkLabel(self, text="Last 30 days", font=FTB).pack(anchor="w", pady=(10, 4))
        records = hl.get_recent(30)
        if records:
            rows = []
            for rec in records:
                e   = rec["energy"] or 0
                col = GREEN if e >= 7 else ORANGE if e >= 4 else (RED if e > 0 else None)
                rows.append([rec["date"],
                             f"{rec['weight_kg']}kg" if rec["weight_kg"] else "--",
                             f"{rec['sleep_h']}h" if rec["sleep_h"] else "--",
                             (f"{e}/10" if e else "--", col),
                             rec["pain_notes"] or rec["notes"] or ""])
            make_table(self, ["Date", "Weight", "Sleep", "Energy", "Pain/Notes"],
                       rows, [100, 80, 70, 70, 260]).pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(self, text="No health records yet.",
                         text_color=TEXT_MUTED, font=FT).pack(anchor="w")

    def _save(self):
        def gf(e):
            try: return float(e.get().strip()) if e.get().strip() else None
            except: return None
        def gi(e):
            try: return int(float(e.get().strip())) if e.get().strip() else None
            except: return None
        hl.log(weight_kg=gf(self.e_wt), sleep_h=gf(self.e_sl), energy=gi(self.e_en),
               pain_notes=self.e_pain.get().strip() or None,
               notes=self.e_notes.get().strip() or None)
        self.save_lbl.configure(text="  Saved!", text_color=GREEN)


# ── StatsPage ─────────────────────────────────────────────────────────────────

class StatsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Statistics")

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True)

        tabs.add("Frequency (30d)")
        ft   = tabs.tab("Frequency (30d)")
        data = st.activity_frequency(30)
        if data:
            rows = [[r["name"], r["category"], str(r["count"]),
                     str(r["total_sets"] or "--"),
                     str(r["total_reps"] or "--"),
                     f"{r['total_min']:.0f}" if r["total_min"] else "--"]
                    for r in data]
            make_table(ft, ["Exercise", "Category", "Sessions", "Sets", "Reps", "Min"],
                       rows, [130, 100, 80, 60, 60, 60]).pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(ft, text="No data yet.", text_color=TEXT_MUTED).pack(anchor="w", padx=10, pady=10)

        tabs.add("Weekly Trend")
        wt    = tabs.tab("Weekly Trend")
        wdata = st.weekly_volume(8)
        if wdata:
            max_s = max(r["sessions"] for r in wdata) or 1
            rows  = [[r["week"], str(r["sessions"]), str(r["days_active"]),
                      str(r["different_exercises"]),
                      ("||" * int((r["sessions"] / max_s) * 18), ORANGE)]
                     for r in wdata]
            make_table(wt, ["Week", "Sessions", "Days", "Exercises", "Volume"],
                       rows, [100, 80, 60, 90, 200]).pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(wt, text="No data yet.", text_color=TEXT_MUTED).pack(anchor="w", padx=10, pady=10)


# ── TemplatesPage ─────────────────────────────────────────────────────────────

class TemplatesPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Workout Templates")

        ctk.CTkButton(self, text="+ New Template", command=self._new_dlg,
                      fg_color=ORANGE, hover_color=ORANGE_DK,
                      font=FTB, height=34).pack(anchor="w", pady=(0, 10))

        self._list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._list.pack(fill="both", expand=True)
        self._refresh()

    def _refresh(self):
        clear(self._list)
        all_t = tmpl.all_templates()
        if not all_t:
            ctk.CTkLabel(self._list, text="No templates yet. Create your first!",
                         text_color=TEXT_MUTED, font=FT).pack(anchor="w", pady=10)
            return

        for t in all_t:
            card = ctk.CTkFrame(self._list, fg_color=CARD, corner_radius=10)
            card.pack(fill="x", pady=4)

            hdr = ctk.CTkFrame(card, fg_color="transparent")
            hdr.pack(fill="x", padx=12, pady=(10, 4))
            ctk.CTkLabel(hdr, text=t["name"], font=FTB).pack(side="left")
            ctk.CTkButton(hdr, text="Delete", width=70, height=26,
                          fg_color="gray28", hover_color=RED, font=FTS,
                          command=lambda tid=t["id"]: self._delete(tid)).pack(side="right", padx=4)
            ctk.CTkButton(hdr, text="+ Exercise", width=90, height=26,
                          fg_color="gray28", hover_color="gray22", font=FTS,
                          command=lambda tid=t["id"]: self._add_ex_dlg(tid)).pack(side="right", padx=4)

            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="x", padx=14, pady=(0, 10))

            exs = tmpl.get_exercises(t["id"])
            if not exs:
                ctk.CTkLabel(body, text="No exercises yet.",
                             font=FTS, text_color=TEXT_MUTED).pack(anchor="w")
            else:
                for i, ex in enumerate(exs, 1):
                    row = ctk.CTkFrame(body, fg_color="transparent")
                    row.pack(fill="x", pady=2)
                    ctk.CTkLabel(row, text=str(i), width=22, font=FTB,
                                 text_color=ORANGE).pack(side="left")
                    ctk.CTkLabel(row, text=ex["activity_name"],
                                 font=FT, width=140, anchor="w").pack(side="left")
                    parts = []
                    if ex["target_sets"]: parts.append(f"{ex['target_sets']} sets")
                    if ex["target_reps"]: parts.append(f"x {ex['target_reps']}")
                    if ex["target_kg"]:   parts.append(f"@ {ex['target_kg']}kg")
                    ctk.CTkLabel(row, text="  ".join(parts),
                                 font=FTS, text_color=TEXT_MUTED).pack(side="left")

    def _new_dlg(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("New Template")
        dlg.geometry("320x155")
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Template name:").pack(padx=20, pady=(20, 4), anchor="w")
        e = ctk.CTkEntry(dlg, width=280, placeholder_text="e.g. Push Day")
        e.pack(padx=20, pady=(0, 8))
        msg = ctk.CTkLabel(dlg, text="")
        msg.pack()

        def save():
            name = e.get().strip()
            if not name:
                msg.configure(text="Name required.", text_color=RED)
                return
            tmpl.create(name)
            dlg.destroy()
            self._refresh()

        ctk.CTkButton(dlg, text="Create", command=save,
                      fg_color=ORANGE, hover_color=ORANGE_DK, width=120).pack(pady=6)

    def _add_ex_dlg(self, template_id):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Add Exercise")
        dlg.geometry("380x280")
        dlg.grab_set()

        activities = act.all_activities()
        names      = [a["name"] for a in activities]
        act_map    = {a["name"]: a for a in activities}

        def lbl(text, row):
            ctk.CTkLabel(dlg, text=text, width=145, anchor="e").grid(
                row=row, column=0, padx=(10, 5), pady=7, sticky="e")

        lbl("Exercise:", 0)
        av = ctk.StringVar(value=names[0] if names else "")
        ctk.CTkComboBox(dlg, values=names, variable=av, width=180).grid(
            row=0, column=1, padx=5, pady=7, sticky="w")
        lbl("Target Sets:", 1)
        e_sets = ctk.CTkEntry(dlg, width=100, placeholder_text="optional")
        e_sets.grid(row=1, column=1, padx=5, pady=7, sticky="w")
        lbl("Target Reps:", 2)
        e_reps = ctk.CTkEntry(dlg, width=100, placeholder_text="optional")
        e_reps.grid(row=2, column=1, padx=5, pady=7, sticky="w")
        lbl("Target Weight (kg):", 3)
        e_kg = ctk.CTkEntry(dlg, width=100, placeholder_text="optional")
        e_kg.grid(row=3, column=1, padx=5, pady=7, sticky="w")

        def gi(e):
            try: return int(float(e.get())) if e.get().strip() else None
            except: return None
        def gf(e):
            try: return float(e.get()) if e.get().strip() else None
            except: return None

        def save():
            a = act_map.get(av.get())
            if not a: return
            tmpl.add_exercise(template_id, a["id"],
                              len(tmpl.get_exercises(template_id)),
                              target_sets=gi(e_sets), target_reps=gi(e_reps),
                              target_kg=gf(e_kg))
            dlg.destroy()
            self._refresh()

        ctk.CTkButton(dlg, text="Add", command=save,
                      fg_color=ORANGE, hover_color=ORANGE_DK, width=120).grid(
            row=4, column=0, columnspan=2, pady=14)

    def _delete(self, template_id):
        tmpl.delete(template_id)
        self._refresh()


# ── ManagePage ────────────────────────────────────────────────────────────────

class ManagePage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        page_title(self, "Manage Activities")

        self._list = ctk.CTkFrame(self, fg_color="transparent")
        self._list.pack(fill="both", expand=True)
        self._show_list()

        ctk.CTkButton(self, text="+ Add Activity", command=self._add_dlg,
                      fg_color=ORANGE, hover_color=ORANGE_DK, width=150).pack(anchor="w", pady=8)

    def _show_list(self):
        clear(self._list)
        activities = act.all_activities()
        rows = [[str(i), a["name"], a["category"], a["unit"]]
                for i, a in enumerate(activities, 1)]
        make_table(self._list, ["#", "Name", "Category", "Unit"],
                   rows, [36, 150, 120, 80]).pack(fill="both", expand=True)

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
                msg.configure(text="Name required.", text_color=RED)
                return
            act.add(name, cat_var.get(), unit_var.get())
            dlg.destroy()
            self._show_list()

        ctk.CTkButton(dlg, text="Add", command=save,
                      fg_color=ORANGE, hover_color=ORANGE_DK, width=120).grid(
            row=4, column=0, columnspan=2, pady=12)


# ── App ───────────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gym Tracker")
        self.geometry("1080x720")
        self.minsize(900, 600)
        self._build()
        self._nav("log")

    def _build(self):
        sb = ctk.CTkFrame(self, width=165, corner_radius=0,
                          fg_color=("gray82", "#161618"))
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        ctk.CTkLabel(sb, text="GYM\nTRACKER",
                     font=("Segoe UI", 17, "bold"),
                     text_color=ORANGE).pack(pady=(18, 4))
        ctk.CTkLabel(sb, text=date.today().strftime("%a %d %b"),
                     font=FTS, text_color=TEXT_MUTED).pack(pady=(0, 10))

        pages = [
            ("log",       "  Log Workout"),
            ("today",     "  Today"),
            ("weekly",    "  Weekly"),
            ("prs",       "  Records"),
            ("planner",   "  Planner"),
            ("health",    "  Health"),
            ("stats",     "  Statistics"),
            ("templates", "  Templates"),
            ("manage",    "  Activities"),
        ]
        self._nav_btns = {}
        for key, label in pages:
            btn = ctk.CTkButton(
                sb, text=label, anchor="w",
                fg_color="transparent", hover_color=("gray72", "#2a2a2e"),
                font=("Segoe UI", 12),
                command=lambda k=key: self._nav(k),
            )
            btn.pack(fill="x", padx=6, pady=2)
            self._nav_btns[key] = btn

        self.streak_lbl = ctk.CTkLabel(sb, text="", font=FTS, text_color=ORANGE)
        self.streak_lbl.pack(side="bottom", pady=14)

        self._content = ctk.CTkFrame(self, corner_radius=0,
                                      fg_color=("gray91", "#131315"))
        self._content.pack(side="left", fill="both", expand=True)

    def _nav(self, key):
        for k, btn in self._nav_btns.items():
            btn.configure(fg_color="transparent" if k != key else ("gray72", "#2a2a2e"))
        clear(self._content)

        s = st.streak()
        self.streak_lbl.configure(text=f"  {s}d streak" if s > 1 else "")

        pages = {
            "log":       LogPage,
            "today":     TodayPage,
            "weekly":    WeeklyPage,
            "prs":       PRsPage,
            "planner":   PlannerPage,
            "health":    HealthPage,
            "stats":     StatsPage,
            "templates": TemplatesPage,
            "manage":    ManagePage,
        }
        pages[key](self._content).pack(fill="both", expand=True, padx=18, pady=12)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    db.init_db()
    act.seed()
    App().mainloop()


if __name__ == "__main__":
    main()

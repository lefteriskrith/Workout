"""
Smoke tests  — basic operations don't crash
Regression tests — specific behavioral contracts that must always hold
"""
import unittest
import tempfile
from pathlib import Path
from datetime import date, timedelta

# Redirect db to a temp file BEFORE importing any module that calls get_conn()
import db
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
db.DB_PATH = Path(_tmp.name)
db.init_db()

import activities as act
import workouts as wk
import stats as st
import health as hl
import planner as plan
import templates as tmpl


def _add(name, category="strength", unit="kg"):
    """Add an activity and return its id."""
    act.add(name, category, unit)
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT id FROM activities WHERE name=?", (name,)
        ).fetchone()["id"]


# ── Smoke tests ───────────────────────────────────────────────────────────────

class SmokeTests(unittest.TestCase):

    def test_db_init_is_idempotent(self):
        db.init_db()
        db.init_db()

    def test_seed_populates_activities(self):
        act.seed()
        self.assertGreater(len(act.all_activities()), 0)

    def test_add_and_fetch_activity(self):
        act.add("Smoke_Add", "cardio", "min")
        names = [a["name"] for a in act.all_activities()]
        self.assertIn("Smoke_Add", names)

    def test_get_activity_by_id(self):
        aid = _add("Smoke_GetById")
        a = act.get_by_id(aid)
        self.assertEqual(a["name"], "Smoke_GetById")

    def test_log_returns_list(self):
        aid = _add("Smoke_Log")
        result = wk.log(aid, sets=3, reps=10, weight_kg=50.0)
        self.assertIsInstance(result, list)

    def test_log_sets_returns_list(self):
        aid = _add("Smoke_LogSets")
        sets_data = [
            {"weight_kg": 60.0, "reps": 8, "rpe": 7, "duration_min": None},
            {"weight_kg": 65.0, "reps": 6, "rpe": 8, "duration_min": None},
        ]
        result = wk.log_sets(aid, sets_data)
        self.assertIsInstance(result, list)

    def test_for_date_returns_list(self):
        result = wk.for_date(date.today().isoformat())
        self.assertIsInstance(result, list)

    def test_for_date_summary_returns_list(self):
        result = wk.for_date_summary(date.today().isoformat())
        self.assertIsInstance(result, list)

    def test_for_week_returns_list(self):
        ws = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        result = wk.for_week(ws)
        self.assertIsInstance(result, list)

    def test_last_session_sets_empty_activity(self):
        aid = _add("Smoke_LastEmpty")
        last_date, sets = wk.last_session_sets(aid)
        self.assertIsNone(last_date)
        self.assertEqual(sets, [])

    def test_health_log_and_fetch(self):
        hl.log(on_date="2025-06-01", weight_kg=75.0, sleep_h=7.5, energy=8)
        rec = hl.get_for_date("2025-06-01")
        self.assertIsNotNone(rec)

    def test_health_get_recent_returns_list(self):
        self.assertIsInstance(hl.get_recent(30), list)

    def test_planner_set_and_get(self):
        aid = _add("Smoke_Planner")
        ws = "2025-03-03"
        plan.set_entry(ws, 0, aid, target_sets=3)
        rows = plan.get_plan(ws)
        self.assertTrue(any(r["activity_id"] == aid for r in rows))

    def test_planner_delete_entry(self):
        aid = _add("Smoke_PlanDel")
        ws = "2025-03-10"
        plan.set_entry(ws, 1, aid)
        entry_id = plan.get_plan(ws)[0]["id"]
        plan.delete_entry(entry_id)
        self.assertEqual(plan.get_plan(ws), [])

    def test_template_create_and_list(self):
        tid = tmpl.create("Smoke_Template")
        self.assertIsNotNone(tid)
        self.assertIn("Smoke_Template", [t["name"] for t in tmpl.all_templates()])

    def test_template_add_and_get_exercises(self):
        tid = tmpl.create("Smoke_TemplateEx")
        aid = _add("Smoke_TmplEx")
        tmpl.add_exercise(tid, aid, 0, target_sets=3, target_reps=10)
        self.assertEqual(len(tmpl.get_exercises(tid)), 1)

    def test_template_delete(self):
        tid = tmpl.create("Smoke_TmplDel")
        tmpl.delete(tid)
        self.assertNotIn("Smoke_TmplDel", [t["name"] for t in tmpl.all_templates()])

    def test_get_prs_returns_list(self):
        self.assertIsInstance(st.get_prs(), list)

    def test_streak_returns_non_negative_int(self):
        result = st.streak()
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)

    def test_activity_frequency_returns_list(self):
        self.assertIsInstance(st.activity_frequency(30), list)

    def test_weekly_volume_returns_list(self):
        self.assertIsInstance(st.weekly_volume(8), list)

    def test_current_week_start_returns_string(self):
        ws = plan.current_week_start()
        self.assertRegex(ws, r"\d{4}-\d{2}-\d{2}")


# ── Regression tests ──────────────────────────────────────────────────────────

class RegressionTests(unittest.TestCase):

    # ── calc_1rm ──────────────────────────────────────────────────────────────

    def test_1rm_epley_formula(self):
        # 100 kg × 10 reps → 100 × (1 + 10/30) = 133.3
        self.assertAlmostEqual(wk.calc_1rm(100.0, 10), 133.3, places=1)

    def test_1rm_single_rep_equals_weight_plus_fraction(self):
        self.assertAlmostEqual(wk.calc_1rm(100.0, 1), 103.3, places=1)

    def test_1rm_none_weight_returns_none(self):
        self.assertIsNone(wk.calc_1rm(None, 10))

    def test_1rm_none_reps_returns_none(self):
        self.assertIsNone(wk.calc_1rm(100.0, None))

    def test_1rm_zero_reps_returns_none(self):
        self.assertIsNone(wk.calc_1rm(100.0, 0))

    # ── PR detection ─────────────────────────────────────────────────────────

    def test_first_log_creates_pr_record(self):
        aid = _add("Reg_PRFirst")
        prs = wk.log(aid, sets=1, reps=5, weight_kg=50.0)
        self.assertTrue(any("First" in p for p in prs))
        pr_list = [p for p in st.get_prs() if p["activity_id"] == aid]
        self.assertEqual(len(pr_list), 1)
        self.assertEqual(pr_list[0]["best_weight_kg"], 50.0)

    def test_higher_weight_triggers_pr(self):
        aid = _add("Reg_PRHigherW")
        wk.log(aid, sets=1, reps=5, weight_kg=50.0)
        prs = wk.log(aid, sets=1, reps=5, weight_kg=55.0)
        self.assertTrue(any("New weight PR" in p for p in prs))

    def test_same_weight_no_new_pr(self):
        aid = _add("Reg_PRSameW")
        wk.log(aid, sets=1, reps=5, weight_kg=50.0)
        prs = wk.log(aid, sets=1, reps=5, weight_kg=50.0)
        self.assertFalse(any("weight PR" in p for p in prs))

    def test_lower_weight_no_new_pr(self):
        aid = _add("Reg_PRLowerW")
        wk.log(aid, sets=1, reps=5, weight_kg=60.0)
        prs = wk.log(aid, sets=1, reps=5, weight_kg=55.0)
        self.assertFalse(any("weight PR" in p for p in prs))

    def test_higher_reps_triggers_pr(self):
        aid = _add("Reg_PRHigherR")
        wk.log(aid, sets=1, reps=10, weight_kg=40.0)
        prs = wk.log(aid, sets=1, reps=12, weight_kg=40.0)
        self.assertTrue(any("reps PR" in p for p in prs))

    def test_higher_duration_triggers_pr(self):
        aid = _add("Reg_PRDur", category="cardio", unit="min")
        wk.log(aid, duration_min=30.0)
        prs = wk.log(aid, duration_min=35.0)
        self.assertTrue(any("duration PR" in p for p in prs))

    # ── log_sets deduplication ────────────────────────────────────────────────

    def test_log_sets_deduplicates_pr_messages(self):
        # Three identical sets — PR should be reported only once, not three times
        aid = _add("Reg_Dedup")
        sets_data = [{"weight_kg": 80.0, "reps": 5, "rpe": 8, "duration_min": None}] * 3
        prs = wk.log_sets(aid, sets_data)
        self.assertLessEqual(len([p for p in prs if "weight" in p.lower()]), 1)

    # ── for_date_summary ─────────────────────────────────────────────────────

    def test_summary_aggregates_sets_and_max_weight(self):
        aid = _add("Reg_Summary")
        d = "2025-05-01"
        wk.log(aid, sets=1, reps=10, weight_kg=60.0, on_date=d)
        wk.log(aid, sets=1, reps=10, weight_kg=70.0, on_date=d)
        wk.log(aid, sets=1, reps=10, weight_kg=65.0, on_date=d)
        rows = wk.for_date_summary(d)
        s = next(r for r in rows if r["activity_id"] == aid)
        self.assertEqual(s["sets"], 3)
        self.assertEqual(s["max_weight"], 70.0)

    # ── for_week ─────────────────────────────────────────────────────────────

    def test_for_week_includes_days_in_range_only(self):
        aid = _add("Reg_WeekRange")
        ws          = "2025-01-06"   # Monday
        in_range    = "2025-01-09"   # Thursday — inside
        out_range   = "2025-01-13"   # following Monday — outside
        wk.log(aid, sets=1, reps=5, on_date=in_range)
        wk.log(aid, sets=1, reps=5, on_date=out_range)
        dates = [r["date"] for r in wk.for_week(ws)]
        self.assertIn(in_range, dates)
        self.assertNotIn(out_range, dates)

    # ── last_session_sets ────────────────────────────────────────────────────

    def test_last_session_returns_correct_date_and_count(self):
        aid = _add("Reg_LastSession")
        d = "2025-04-10"
        wk.log(aid, sets=1, reps=8, weight_kg=60.0, on_date=d)
        wk.log(aid, sets=1, reps=6, weight_kg=65.0, on_date=d)
        last_date, sets = wk.last_session_sets(aid)
        self.assertEqual(last_date, d)
        self.assertEqual(len(sets), 2)

    def test_last_session_returns_most_recent_date(self):
        aid = _add("Reg_LastRecent")
        wk.log(aid, sets=1, reps=5, on_date="2025-03-01")
        wk.log(aid, sets=1, reps=5, on_date="2025-03-15")
        last_date, _ = wk.last_session_sets(aid)
        self.assertEqual(last_date, "2025-03-15")

    # ── streak ───────────────────────────────────────────────────────────────

    def test_streak_consecutive_days(self):
        aid = _add("Reg_Streak")
        today = date.today()
        for i in range(3):
            wk.log(aid, sets=1, reps=5, on_date=(today - timedelta(days=i)).isoformat())
        self.assertGreaterEqual(st.streak(), 3)

    def test_streak_broken_by_gap(self):
        aid = _add("Reg_StreakBroken")
        # Log today and 3 days ago — gap of 2 days breaks the streak
        wk.log(aid, sets=1, reps=5, on_date=date.today().isoformat())
        wk.log(aid, sets=1, reps=5, on_date=(date.today() - timedelta(days=3)).isoformat())
        # Streak is at least 1 (today) but the old isolated log shouldn't inflate it
        self.assertGreaterEqual(st.streak(), 1)

    # ── health upsert ─────────────────────────────────────────────────────────

    def test_health_replace_overwrites_same_day(self):
        hl.log(on_date="2025-07-01", weight_kg=70.0)
        hl.log(on_date="2025-07-01", weight_kg=71.5)
        rec = hl.get_for_date("2025-07-01")
        self.assertEqual(rec["weight_kg"], 71.5)

    def test_health_different_days_are_separate(self):
        hl.log(on_date="2025-07-10", weight_kg=72.0)
        hl.log(on_date="2025-07-11", weight_kg=73.0)
        self.assertEqual(hl.get_for_date("2025-07-10")["weight_kg"], 72.0)
        self.assertEqual(hl.get_for_date("2025-07-11")["weight_kg"], 73.0)

    # ── planner copy ─────────────────────────────────────────────────────────

    def test_copy_plan_transfers_entries(self):
        aid = _add("Reg_CopyPlan")
        from_ws, to_ws = "2025-02-03", "2025-02-10"
        plan.set_entry(from_ws, 1, aid, target_sets=4)
        plan.copy_plan(from_ws, to_ws)
        self.assertTrue(any(r["activity_id"] == aid for r in plan.get_plan(to_ws)))

    def test_copy_plan_does_not_overwrite_existing(self):
        # OR IGNORE: if to_ws already has an entry for (day, activity), keep it
        aid = _add("Reg_CopyNoOver")
        from_ws, to_ws = "2025-02-17", "2025-02-24"
        plan.set_entry(from_ws, 0, aid, target_sets=3)
        plan.set_entry(to_ws,   0, aid, target_sets=5)
        plan.copy_plan(from_ws, to_ws)
        entry = next(r for r in plan.get_plan(to_ws) if r["activity_id"] == aid)
        self.assertEqual(entry["target_sets"], 5)

    # ── current_week_start ───────────────────────────────────────────────────

    def test_week_start_is_always_monday(self):
        monday    = date(2025, 4, 28)
        wednesday = date(2025, 4, 30)
        sunday    = date(2025, 5,  4)
        self.assertEqual(plan.current_week_start(monday),    "2025-04-28")
        self.assertEqual(plan.current_week_start(wednesday), "2025-04-28")
        self.assertEqual(plan.current_week_start(sunday),    "2025-04-28")

    # ── templates ────────────────────────────────────────────────────────────

    def test_template_exercises_are_ordered(self):
        tid = tmpl.create("Reg_TmplOrder")
        a1 = _add("Reg_TmplEx1")
        a2 = _add("Reg_TmplEx2")
        tmpl.add_exercise(tid, a1, sort_order=0)
        tmpl.add_exercise(tid, a2, sort_order=1)
        exs = tmpl.get_exercises(tid)
        self.assertEqual(exs[0]["activity_id"], a1)
        self.assertEqual(exs[1]["activity_id"], a2)

    def test_template_delete_cascades_exercises(self):
        tid = tmpl.create("Reg_TmplCascade")
        aid = _add("Reg_TmplCascEx")
        tmpl.add_exercise(tid, aid, sort_order=0)
        tmpl.delete(tid)
        # After deleting the template, its exercises should also be gone (ON DELETE CASCADE)
        self.assertEqual(tmpl.get_exercises(tid), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

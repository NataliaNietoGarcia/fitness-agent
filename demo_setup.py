import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from database.db import get_connection, create_tables, save_user_profile, log_weight, log_food
from tools.nutrition import get_nutrition_by_exact_name


# ============================================================
# RESET — run ONCE before recording, to start with a clean app
# ============================================================

def reset_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_profile")
    cursor.execute("DELETE FROM weight_log")
    cursor.execute("DELETE FROM workouts")
    cursor.execute("DELETE FROM nutrition")
    conn.commit()
    conn.close()
    print("🗑️ Database cleared (food_database kept). Ready to record profile creation live.")


# ============================================================
# WORKOUT HISTORY — 4 weeks
#
# Roles by exercise:
# - Kniebeuge, Kreuzheben, Beinpresse, Klimmzüge → clean 4-week
#   progression, for nice-looking charts
# - Bankdrücken → PLATEAU demo: 3 sessions, all at the same weight,
#   placed in the last 10 days. Logging "Bankdrücken 80kg ..." live
#   makes it a guaranteed 4th identical entry → deterministic plateau
#   warning fires (rule: last up to 5 sessions all equal).
# - Schulterdrücken → "TIME TO INCREASE" demo: progression that
#   flattens for the last 2 historical sessions (40kg, 40kg).
#   Logging "Schulterdrücken 40kg ..." live makes it 3 in a row at
#   40kg, but an earlier different weight (35/37.5kg) is still within
#   the last-5 window, so the deterministic plateau rule does NOT
#   fire — instead the LLM-based automatic check (which reads the
#   raw session history) is likely to notice the recent flat trend
#   and suggest increasing the weight. This is LLM-driven, not a
#   hardcoded rule — do a dry run beforehand to confirm the wording.
# ============================================================

def add_demo_workouts():
    today = date.today()
    workouts = [
        # Week 1 (days 27-21 ago)
        (today - timedelta(days=27), [
            {"exercise": "Kniebeuge", "weight_kg": 90, "sets": 4, "reps": 8},
            {"exercise": "Klimmzüge", "weight_kg": 0, "sets": 3, "reps": 8},
        ]),
        (today - timedelta(days=25), [
            {"exercise": "Kreuzheben", "weight_kg": 100, "sets": 3, "reps": 6},
            {"exercise": "Schulterdrücken", "weight_kg": 35, "sets": 3, "reps": 10},
        ]),
        (today - timedelta(days=22), [
            {"exercise": "Beinpresse", "weight_kg": 140, "sets": 3, "reps": 10},
        ]),

        # Week 2 (days 20-14 ago)
        (today - timedelta(days=20), [
            {"exercise": "Kniebeuge", "weight_kg": 92.5, "sets": 4, "reps": 8},
            {"exercise": "Klimmzüge", "weight_kg": 2.5, "sets": 3, "reps": 8},
        ]),
        (today - timedelta(days=18), [
            {"exercise": "Kreuzheben", "weight_kg": 105, "sets": 3, "reps": 6},
            {"exercise": "Schulterdrücken", "weight_kg": 37.5, "sets": 3, "reps": 10},
        ]),
        (today - timedelta(days=15), [
            {"exercise": "Beinpresse", "weight_kg": 145, "sets": 3, "reps": 10},
        ]),

        # Week 3 (days 13-7 ago)
        (today - timedelta(days=13), [
            {"exercise": "Kniebeuge", "weight_kg": 95, "sets": 4, "reps": 8},
            {"exercise": "Klimmzüge", "weight_kg": 5, "sets": 3, "reps": 8},
        ]),
        (today - timedelta(days=11), [
            {"exercise": "Kreuzheben", "weight_kg": 110, "sets": 3, "reps": 6},
            {"exercise": "Schulterdrücken", "weight_kg": 40, "sets": 3, "reps": 10},
        ]),
        (today - timedelta(days=8), [
            {"exercise": "Beinpresse", "weight_kg": 152.5, "sets": 3, "reps": 10},
            {"exercise": "Bankdrücken", "weight_kg": 80, "sets": 3, "reps": 8},
        ]),

        # Week 4 (days 6-2 ago) — Bankdrücken & Schulterdrücken plateaus set up here
        (today - timedelta(days=6), [
            {"exercise": "Kniebeuge", "weight_kg": 97.5, "sets": 4, "reps": 8},
            {"exercise": "Klimmzüge", "weight_kg": 5, "sets": 3, "reps": 8},
        ]),
        (today - timedelta(days=5), [
            {"exercise": "Bankdrücken", "weight_kg": 80, "sets": 3, "reps": 8},
        ]),
        (today - timedelta(days=4), [
            {"exercise": "Kreuzheben", "weight_kg": 115, "sets": 3, "reps": 6},
            {"exercise": "Schulterdrücken", "weight_kg": 40, "sets": 3, "reps": 10},
        ]),
        (today - timedelta(days=2), [
            {"exercise": "Beinpresse", "weight_kg": 160, "sets": 3, "reps": 10},
            {"exercise": "Bankdrücken", "weight_kg": 80, "sets": 3, "reps": 8},
        ]),
    ]

    conn = get_connection()
    cursor = conn.cursor()
    for workout_date, exercises in workouts:
        for e in exercises:
            cursor.execute("""
                INSERT INTO workouts (date, exercise, weight_kg, sets, reps)
                VALUES (?, ?, ?, ?, ?)
            """, (workout_date, e["exercise"], e["weight_kg"], e["sets"], e["reps"]))
    conn.commit()
    conn.close()
    print("✅ Workout history added (13 sessions over 4 weeks)")
    print("   → Live demo: log 'Bankdrücken 80kg 3x8' → guaranteed plateau warning")
    print("   → Live demo: log 'Schulterdrücken 40kg 3x10' → likely 'increase weight' hint (LLM-based, do a dry run)")


# ============================================================
# WEIGHT HISTORY — 4-week bulk progression, starting at 86kg
# ============================================================

def add_demo_weight_history():
    today = date.today()
    log_weight(86.0, today - timedelta(days=27))
    log_weight(86.4, today - timedelta(days=23))
    log_weight(86.8, today - timedelta(days=19))
    log_weight(87.2, today - timedelta(days=15))
    log_weight(87.6, today - timedelta(days=11))
    log_weight(88.0, today - timedelta(days=8))
    log_weight(88.4, today - timedelta(days=5))
    log_weight(88.8, today - timedelta(days=2))
    print("✅ Weight history added (86.0kg → 88.8kg over 4 weeks)")


# ============================================================
# NUTRITION HISTORY — varied portion sizes across 4 weeks,
# alternating lighter and heavier days for a visible calorie
# difference in the weekly/monthly overview. Today stays empty
# for the live coaching-feedback demo.
# ============================================================

def add_demo_nutrition_history():
    today = date.today()

    daily_meals = {
        # Week 1
        26: [("Haferflocken", 70), ("Banane roh", 100), ("Hähnchenbrustfilet gebraten", 180)],           # lighter day
        24: [("Ei gekocht", 120), ("Vollkornbrot", 100), ("Rindfleisch", 200), ("Kartoffeln", 250), ("Olivenöl", 15)],  # heavier day
        21: [("Magerquark", 200), ("Banane roh", 100), ("Reis gekocht", 150)],                            # lighter day

        # Week 2
        19: [("Haferflocken", 90), ("Hähnchenbrustfilet gebraten", 220), ("Nudeln", 220), ("Olivenöl", 20)],  # heavier day
        16: [("Ei gekocht", 60), ("Banane roh", 120), ("Magerquark", 150)],                                # lighter day
        14: [("Lachs", 180), ("Reis gekocht", 220), ("Kartoffeln", 150), ("Vollkornbrot", 80)],            # heavier day

        # Week 3
        12: [("Haferflocken", 60), ("Banane roh", 100), ("Hähnchenbrustfilet gebraten", 160)],             # lighter day
        9:  [("Ei gekocht", 120), ("Rindfleisch", 220), ("Kartoffeln", 280), ("Olivenöl", 20), ("Nudeln", 150)],  # heavier day
        7:  [("Magerquark", 250), ("Banane roh", 120), ("Vollkornbrot", 60)],                              # lighter day

        # Week 4
        5:  [("Haferflocken", 90), ("Hähnchenbrustfilet gebraten", 220), ("Reis gekocht", 220), ("Olivenöl", 15)],  # heavier day
        3:  [("Ei gekocht", 60), ("Banane roh", 100), ("Magerquark", 150)],                                # lighter day
        1:  [("Lachs", 200), ("Kartoffeln", 250), ("Nudeln", 180), ("Olivenöl", 20)],                      # heavier day
    }

    for days_ago, meals in daily_meals.items():
        meal_date = today - timedelta(days=days_ago)
        for food_name, amount in meals:
            nutrition = get_nutrition_by_exact_name(food_name, amount)
            if nutrition:
                log_food(
                    nutrition["name"], nutrition["amount_g"], nutrition["calories"],
                    nutrition["protein_g"], nutrition["carbs_g"], nutrition["fat_g"],
                    nutrition.get("sugar_g", 0), meal_date
                )
            else:
                print(f"  ⚠️ Not found: {food_name} (skipped for {meal_date})")

    print("✅ Nutrition history added (13 days across 4 weeks, varied calories) — today left empty for live demo")


# ============================================================
# COMBINED — run this AFTER creating the profile live in the app
# ============================================================

def add_demo_history():
    """Adds 4 weeks of workouts, weight, and nutrition history —
    does NOT touch the user profile, so it's safe to run after
    you've created the profile live during recording."""
    add_demo_workouts()
    add_demo_weight_history()
    add_demo_nutrition_history()
    print("\n🎬 Ready! Reload the app to see progression, weekly macros, and charts.")


if __name__ == "__main__":
    create_tables()

    # ------------------------------------------------------------------
    # USAGE FOR THE VIDEO:
    #
    # 1) Run ONCE before you start recording:
    #        reset_db()
    #    → gives you a completely empty app
    #
    # 2) Record: create the profile live in the app (via the form),
    #    optionally log 1-2 entries live too.
    #
    # 3) STOP recording. Run:
    #        add_demo_history()
    #    → injects 4 weeks of workouts/weight/nutrition WITHOUT
    #      touching the profile you just created live
    #
    # 4) Resume recording: reload the app, show "4 weeks later",
    #    then show progression charts, weekly macros, and coaching
    #    feedback.
    #
    #    Live inputs to trigger the two automatic training hints:
    #      "Bankdrücken 80kg 3x8"        → guaranteed plateau warning
    #      "Schulterdrücken 40kg 3x10"   → likely "increase weight"
    #                                       hint (LLM-based — do a
    #                                       dry run first to confirm)
    # ------------------------------------------------------------------

    # Uncomment ONE of these depending on which step you're on:

    #reset_db()
    add_demo_history()
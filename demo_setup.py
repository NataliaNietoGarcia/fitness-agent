"""
Seeds the database with 4 weeks of sample data (workouts, weight, nutrition)
for a demo user profile — useful for trying out progression charts, weekly
overviews, and coaching feedback without logging weeks of real data first.

Usage:
    python demo_setup.py

This resets the database and adds the sample history in one run. If you want
to keep an existing user profile, comment out reset_db() and call
add_demo_history() on its own — it does not touch the user_profile table.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from database.db import get_connection, create_tables, log_weight, log_food
from tools.nutritrion import get_nutrition_by_exact_name


# ============================================================
# RESET — clears all user data (keeps the food_database table)
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
    print("🗑️ Database cleared (food_database kept).")


# ============================================================
# WORKOUT HISTORY — 4 weeks, six exercises, showing clear
# progression across most exercises
# ============================================================

def add_demo_workouts():
    today = date.today()
    workouts = [
        # Week 1
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

        # Week 2
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

        # Week 3
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

        # Week 4
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


# ============================================================
# WEIGHT HISTORY — 4-week progression, starting at 86kg
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
# alternating lighter and heavier days for visible variation
# in the weekly overview
# ============================================================

def add_demo_nutrition_history():
    today = date.today()

    daily_meals = {
        # Week 1
        26: [("Haferflocken", 70), ("Banane roh", 100), ("Hähnchenbrustfilet gebraten", 180)],
        24: [("Ei gekocht", 120), ("Vollkornbrot", 100), ("Rindfleisch", 200), ("Kartoffeln", 250), ("Olivenöl", 15)],
        21: [("Magerquark", 200), ("Banane roh", 100), ("Reis gekocht", 150)],

        # Week 2
        19: [("Haferflocken", 90), ("Hähnchenbrustfilet gebraten", 220), ("Nudeln", 220), ("Olivenöl", 20)],
        16: [("Ei gekocht", 60), ("Banane roh", 120), ("Magerquark", 150)],
        14: [("Lachs", 180), ("Reis gekocht", 220), ("Kartoffeln", 150), ("Vollkornbrot", 80)],

        # Week 3
        12: [("Haferflocken", 60), ("Banane roh", 100), ("Hähnchenbrustfilet gebraten", 160)],
        9:  [("Ei gekocht", 120), ("Rindfleisch", 220), ("Kartoffeln", 280), ("Olivenöl", 20), ("Nudeln", 150)],
        7:  [("Magerquark", 250), ("Banane roh", 120), ("Vollkornbrot", 60)],

        # Week 4
        5:  [("Haferflocken", 90), ("Hähnchenbrustfilet gebraten", 220), ("Reis gekocht", 220), ("Olivenöl", 15)],
        3:  [("Ei gekocht", 60), ("Banane roh", 100), ("Magerquark", 150)],
        1:  [("Lachs", 200), ("Kartoffeln", 250), ("Nudeln", 180), ("Olivenöl", 20)],
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

    print("✅ Nutrition history added (13 days across 4 weeks)")


# ============================================================
# COMBINED
# ============================================================

def add_demo_history():
    """Adds 4 weeks of workouts, weight, and nutrition history.
    Does not touch the user_profile table."""
    add_demo_workouts()
    add_demo_weight_history()
    add_demo_nutrition_history()
    print("\n✅ Demo data ready. Reload the app to see charts and overviews.")


if __name__ == "__main__":
    create_tables()
    reset_db()
    add_demo_history()
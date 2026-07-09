import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime, timedelta
from database.db import get_connection, get_user_profile, get_weight_history, get_daily_nutrition


# ============================================================
# TDEE (Mifflin-St Jeor Formula)
# ============================================================

def calculate_tdee(weight_kg: float, height_cm: float, age: int,
                    gender: str, activity_level: str) -> int:
    if gender.lower() == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    activity_factors = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }
    factor = activity_factors.get(activity_level.lower(), 1.55)
    return round(bmr * factor)


# ============================================================
# MACROS
# ============================================================

def calculate_macros(tdee: float, goal: str, weight_kg: float) -> dict:
    if goal.lower() == "muscle_gain":
        calories = tdee + 300
        protein = weight_kg * 2.0
    elif goal.lower() == "fat_loss":
        calories = tdee - 400
        protein = weight_kg * 2.2
    else:  # recomp
        calories = tdee
        protein = weight_kg * 2.0

    protein_cal = protein * 4
    fat_cal = calories * 0.25
    fat = fat_cal / 9
    carbs_cal = calories - protein_cal - fat_cal
    carbs = carbs_cal / 4

    return {
        "calories": round(calories),
        "protein_g": round(protein),
        "carbs_g": round(carbs),
        "fat_g": round(fat)
    }


# ============================================================
# 1RM (Epley Formula)
# ============================================================

def calculate_1rm(weight_kg: float, reps: int) -> float:
    if reps == 1:
        return weight_kg
    return round(weight_kg * (1 + reps / 30), 1)


# ============================================================
# VOLUME, PR, PLATEAU
# ============================================================

def calculate_volume(exercise: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, sets, reps, weight_kg
        FROM workouts
        WHERE exercise = ?
        ORDER BY date DESC
        LIMIT 5
    """, (exercise,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return f"❌ Keine Daten für {exercise} gefunden."

    result = f"📊 Volumen-Verlauf für {exercise}:\n" + "-" * 40 + "\n"
    for row in rows:
        volume = row[1] * row[2] * row[3]
        result += f"📅 {row[0]} | Volumen: {volume:.0f}kg\n"
    return result


def get_pr(exercise: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MAX(weight_kg), date
        FROM workouts
        WHERE exercise = ?
    """, (exercise,))
    row = cursor.fetchone()
    conn.close()

    if not row or row[0] is None:
        return f"❌ Keine Daten für {exercise} gefunden."

    return f"🏆 Dein PR bei {exercise}: {row[0]}kg (am {row[1]})"


def detect_plateau(exercise: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT weight_kg, date
        FROM workouts
        WHERE exercise = ?
        ORDER BY date DESC
        LIMIT 5
    """, (exercise,))
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 3:
        return f"ℹ️ Noch nicht genug Daten für {exercise}, um ein Plateau zu erkennen (mindestens 3 Einheiten nötig)."

    weights = [row[0] for row in rows]
    if len(set(weights)) == 1:
        return (f"⚠️ Plateau erkannt bei {exercise}! Du hebst seit {len(rows)} Einheiten "
                f"{weights[0]}kg. Zeit für eine Steigerung!")
    return f"✅ Kein Plateau bei {exercise} — du machst Fortschritte!"


def check_workout_plausibility(exercise, weight_kg, sets, reps):
    """Basic sanity check for workout values. Returns a list of warnings (empty if plausible)."""
    warnings = []
    high_weight_exercises = ["beinpresse", "kniebeuge", "kreuzheben"]
    exercise_lower = exercise.lower()

    if any(ex in exercise_lower for ex in high_weight_exercises) and weight_kg < 20:
        warnings.append(f"⚠️ {weight_kg}kg wirkt niedrig für {exercise} — meintest du ein höheres Gewicht?")

    if weight_kg > 500:
        warnings.append(f"⚠️ {weight_kg}kg wirkt sehr hoch für {exercise} — bitte bestätige den Wert.")

    if sets > 15 or reps > 50:
        warnings.append(f"⚠️ {sets} Sätze x {reps} Wdh — ungewöhnlich hoch, bitte prüfen.")

    return warnings


# ============================================================
# WEEKLY VOLUME
# ============================================================

def get_weekly_volume(exercise: str, weeks=1):
    """Total sets for an exercise in the last N weeks."""
    conn = get_connection()
    cursor = conn.cursor()
    start_date = date.today() - timedelta(weeks=weeks)
    cursor.execute("""
        SELECT SUM(sets * reps) FROM workouts WHERE exercise = ? AND date >= ?
    """, (exercise, start_date))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else 0


def get_weekly_volume_all_exercises(weeks=1):
    """Weekly volume grouped by exercise: list of (exercise, total_sets, total_volume)."""
    conn = get_connection()
    cursor = conn.cursor()
    start_date = date.today() - timedelta(weeks=weeks)
    cursor.execute("""
        SELECT exercise, SUM(sets * reps), SUM(sets * reps * weight_kg)
        FROM workouts
        WHERE date >= ?
        GROUP BY exercise
        ORDER BY exercise
    """, (start_date,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# ============================================================
# RAW FACTS (for LLM-based, RAG-informed feedback — no hardcoded thresholds)
# ============================================================

def get_training_facts(exercise: str):
    """Returns raw facts about an exercise — no interpretation, no judgement."""
    conn = get_connection()
    cursor = conn.cursor()

    week_ago = date.today() - timedelta(days=7)
    cursor.execute("""
        SELECT SUM(sets) FROM workouts WHERE exercise = ? AND date >= ?
    """, (exercise, week_ago))
    weekly_sets = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT date, weight_kg FROM workouts
        WHERE exercise = ? ORDER BY date DESC LIMIT 5
    """, (exercise,))
    recent = cursor.fetchall()
    conn.close()

    return {
        "exercise": exercise,
        "weekly_sets": weekly_sets,
        "recent_sessions": [{"date": r[0], "weight_kg": r[1]} for r in recent],
        "same_weight_streak": len(set(r[1] for r in recent)) == 1 if len(recent) >= 3 else False
    }


def get_weekly_nutrition_facts(start_date=None, end_date=None):
    """Nutrition averages for a date range — defaults to the last 7 days."""
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=6)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, SUM(calories), SUM(protein_g), SUM(carbs_g), SUM(fat_g)
        FROM nutrition
        WHERE date >= ? AND date <= ?
        GROUP BY date
        ORDER BY date
    """, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    total_days = len(rows)
    return {
        "days_logged": total_days,
        "start_date": start_date,
        "end_date": end_date,
        "daily_breakdown": [{"date": r[0], "calories": r[1]} for r in rows],
        "avg_calories": round(sum(r[1] for r in rows) / total_days),
        "avg_protein_g": round(sum(r[2] for r in rows) / total_days),
        "avg_carbs_g": round(sum(r[3] for r in rows) / total_days),
        "avg_fat_g": round(sum(r[4] for r in rows) / total_days)
    }


def get_nutrition_facts(target_date=None):
    """Returns raw nutrition facts for the day — no interpretation."""
    if target_date is None:
        target_date = date.today()

    profile = get_user_profile()
    if not profile:
        return {"error": "no_profile"}

    _, name, gender, height, birth_year, activity, goal, _, _ = profile
    age = date.today().year - birth_year

    weight_history = get_weight_history(1)
    if not weight_history:
        return {"error": "no_weight"}
    current_weight = weight_history[0][1]

    tdee = calculate_tdee(current_weight, height, age, gender, activity)
    target_macros = calculate_macros(tdee, goal, current_weight)

    foods = get_daily_nutrition(target_date)
    eaten_cal = sum(f[2] for f in foods)
    eaten_protein = sum(f[3] for f in foods)
    eaten_carbs = sum(f[4] for f in foods)
    eaten_fat = sum(f[5] for f in foods)
    eaten_sugar = sum(f[6] for f in foods) if foods and len(foods[0]) > 6 else 0

    now_hour = datetime.now().hour
    day_progress_pct = round((now_hour / 24) * 100)

    return {
        "goal": goal,
        "target": target_macros,
        "eaten": {
            "calories": round(eaten_cal),
            "protein_g": round(eaten_protein),
            "carbs_g": round(eaten_carbs),
            "fat_g": round(eaten_fat),
            "sugar_g": round(eaten_sugar)
        },
        "current_hour": now_hour,
        "day_progress_pct": day_progress_pct,
        "num_meals_logged": len(foods)
    }


if __name__ == "__main__":
    tdee = calculate_tdee(67, 170, 28, "female", "moderate")
    print(f"TDEE: {tdee} kcal")
    print(f"Macros: {calculate_macros(tdee, 'recomp', 67)}")
    print(f"1RM: {calculate_1rm(100, 8)}kg")
    print(get_pr("Beinpresse"))
    print(detect_plateau("Beinpresse"))
    print(calculate_volume("Beinpresse"))
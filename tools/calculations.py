import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_connection
from datetime import date

# ============================================
# TDEE CALCULATION (Mifflin-St Jeor Formula)
# ============================================
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


# ============================================
# MACRO CALCULATION
# ============================================
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


# ============================================
# 1RM CALCULATION (Epley Formula)
# ============================================
def calculate_1rm(weight_kg: float, reps: int) -> float:
    if reps == 1:
        return weight_kg
    return round(weight_kg * (1 + reps / 30), 1)


# ============================================
# VOLUME CALCULATION
# ============================================
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
        return f"No data found for {exercise}."

    result = f"📊 Volume history for {exercise}:\n"
    result += "-" * 40 + "\n"
    for row in rows:
        volume = row[1] * row[2] * row[3]
        result += f"📅 {row[0]} | Volume: {volume:.0f}kg\n"
    return result


# ============================================
# PR DETECTION (Personal Record)
# ============================================
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
        return f"No data found for {exercise}."

    return f"🏆 Your PR for {exercise}: {row[0]}kg (on {row[1]})"


# ============================================
# PLATEAU DETECTION
# ============================================
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
        return f"Not enough data for {exercise} to detect a plateau (need at least 3 sessions)."

    weights = [row[0] for row in rows]
    if len(set(weights)) == 1:
        return (f"⚠️ Plateau detected for {exercise}! "
                f"You've been lifting {weights[0]}kg for {len(rows)} sessions. "
                f"Consider increasing weight or reps!")
    return f"✅ No plateau detected for {exercise} — you're making progress!"


# ============================================
# TEST
# ============================================
if __name__ == "__main__":
    # TDEE test
    tdee = calculate_tdee(67, 170, 28, "female", "moderate")
    print(f"TDEE: {tdee} kcal")

    # Macros test
    macros = calculate_macros(tdee, "recomp", 67)
    print(f"Macros: {macros}")

    # 1RM test
    print(f"1RM: {calculate_1rm(100, 8)}kg")

    # PR test
    print(get_pr("Beinpresse"))

    # Plateau test
    print(detect_plateau("Beinpresse"))

    # Volume test
    print(calculate_volume("Beinpresse"))
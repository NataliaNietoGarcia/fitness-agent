import sqlite3
from datetime import date


def get_connection():
    return sqlite3.connect("database/fitness.db")


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            exercise TEXT NOT NULL,
            weight_kg REAL,
            sets INTEGER,
            reps INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gender TEXT,
            height_cm REAL,
            birth_year INTEGER,
            activity_level TEXT,
            goal TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weight_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weight_kg REAL NOT NULL,
            date DATE NOT NULL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nutrition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            food_name TEXT NOT NULL,
            amount_g REAL,
            calories REAL,
            protein_g REAL,
            carbs_g REAL,
            fat_g REAL,
            sugar_g REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("Tables created successfully")


# ============================================================
# WORKOUTS
# ============================================================

def save_workout(exercises, workout_date=None):
    if workout_date is None:
        workout_date = date.today()
    conn = get_connection()
    cursor = conn.cursor()
    for e in exercises:
        cursor.execute("""
            INSERT INTO workouts (date, exercise, weight_kg, sets, reps)
            VALUES (?, ?, ?, ?, ?)
        """, (workout_date, e["exercise"], e["weight_kg"], e["sets"], e["reps"]))
    conn.commit()
    conn.close()


def get_recent_workouts(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, exercise, weight_kg, sets, reps
        FROM workouts
        ORDER BY date DESC, id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# ============================================================
# USER PROFILE
# ============================================================

def get_user_profile():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_profile LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row


def save_user_profile(name, gender, height_cm, birth_year, activity_level, goal):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_profile")
    cursor.execute("""
        INSERT INTO user_profile (name, gender, height_cm, birth_year, activity_level, goal)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, gender, height_cm, birth_year, activity_level, goal))
    conn.commit()
    conn.close()


def update_user_goal(new_goal):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_profile
        SET goal = ?, updated_at = CURRENT_TIMESTAMP
    """, (new_goal,))
    conn.commit()
    conn.close()


# ============================================================
# WEIGHT LOG
# ============================================================

def log_weight(weight_kg, log_date=None, note=None):
    if log_date is None:
        log_date = date.today()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO weight_log (weight_kg, date, note)
        VALUES (?, ?, ?)
    """, (weight_kg, log_date, note))
    conn.commit()
    conn.close()


def get_weight_history(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, weight_kg, note
        FROM weight_log
        ORDER BY date DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# ============================================================
# NUTRITION LOG
# ============================================================

def log_food(food_name, amount_g, calories, protein_g, carbs_g, fat_g, sugar_g=0, log_date=None):
    if log_date is None:
        log_date = date.today()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO nutrition (date, food_name, amount_g, calories, protein_g, carbs_g, fat_g, sugar_g)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (log_date, food_name, amount_g, calories, protein_g, carbs_g, fat_g, sugar_g))
    conn.commit()
    conn.close()


def get_daily_nutrition(target_date=None):
    """Returns (food_name, amount_g, calories, protein_g, carbs_g, fat_g, sugar_g) — no id."""
    if target_date is None:
        target_date = date.today()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT food_name, amount_g, calories, protein_g, carbs_g, fat_g, sugar_g
        FROM nutrition
        WHERE date = ?
        ORDER BY id
    """, (target_date,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_daily_nutrition_with_id(target_date=None):
    """Same as get_daily_nutrition but includes the entry id — used for editing/deleting."""
    if target_date is None:
        target_date = date.today()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, food_name, amount_g, calories, protein_g, carbs_g, fat_g, sugar_g
        FROM nutrition
        WHERE date = ?
        ORDER BY id
    """, (target_date,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def find_recent_food_by_keyword(keyword, log_date=None):
    """Finds the most recent nutrition entry matching a keyword."""
    if log_date is None:
        log_date = date.today()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, food_name, amount_g
        FROM nutrition
        WHERE date = ? AND food_name LIKE ?
        ORDER BY id DESC
        LIMIT 1
    """, (log_date, f"%{keyword}%"))
    row = cursor.fetchone()
    conn.close()
    return row  # (id, food_name, amount_g) or None


def update_food_entry(entry_id, food_name, amount_g, calories, protein_g, carbs_g, fat_g, sugar_g=0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE nutrition
        SET food_name = ?, amount_g = ?, calories = ?, protein_g = ?, carbs_g = ?, fat_g = ?, sugar = ?
        WHERE id = ?
    """, (food_name, amount_g, calories, protein_g, carbs_g, fat_g,sugar_g, entry_id))
    conn.commit()
    conn.close()


def delete_food_entry(entry_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM nutrition WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
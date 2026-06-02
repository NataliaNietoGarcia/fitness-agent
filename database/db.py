import sqlite3
from datetime import date

def get_connection():
    conn = sqlite3.connect("database/fitness.db")
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Workout table
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

    # User profile table (one entry only)
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
    # Weight log table (one entry per measurement)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weight_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weight_kg REAL NOT NULL,
            date DATE NOT NULL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("Tables created successfully")



def add_timestamps():
    # Add created_at column if it doesn't exist yet
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE workouts ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass
    conn.commit()
    conn.close()

##USER PROFILE FUNCTIONS
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
    print("✅ User profile saved!")

def update_user_goal(new_goal):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_profile 
        SET goal = ?, updated_at = CURRENT_TIMESTAMP
    """, (new_goal,))
    conn.commit()
    conn.close()
    print(f"✅ Goal updated to: {new_goal}")

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
    print(f"✅ Weight logged: {weight_kg}kg")

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

if __name__ == "__main__":
    create_tables()
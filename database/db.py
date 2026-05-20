import sqlite3

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

if __name__ == "__main__":
    create_tables()
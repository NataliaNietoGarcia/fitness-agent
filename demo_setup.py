from database.db import get_connection, create_tables, save_user_profile, log_weight, save_workout
from datetime import date, timedelta

def reset_and_setup_demo():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear all tables
    cursor.execute("DELETE FROM user_profile")
    cursor.execute("DELETE FROM weight_log")
    cursor.execute("DELETE FROM workouts")
    conn.commit()
    conn.close()
    print("🗑️ All tables cleared!")
    print("✅ Database ready for demo!")

"""
def add_demo_history():
    today = date.today()
    
    # Workouts from last weeks (for PR & Plateau demo)
    workouts = [
        (today - timedelta(days=14), [
            {"exercise": "Bankdrücken", "weight_kg": 75, "sets": 3, "reps": 8},
        ]),
        (today - timedelta(days=7), [
            {"exercise": "Bankdrücken", "weight_kg": 77.5, "sets": 3, "reps": 8},
        ]),
        (today - timedelta(days=3), [
            {"exercise": "Bankdrücken", "weight_kg": 80, "sets": 3, "reps": 8},
        ]),
    ]
    
    for workout_date, exercises in workouts:
        save_workout(exercises, workout_date)

    print("✅ Demo workout history added!")
"""

if __name__ == "__main__":
    create_tables()
    reset_and_setup_demo()
    #add_demo_history()
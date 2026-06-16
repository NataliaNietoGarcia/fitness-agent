import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database.db import get_connection


def get_weight_chart_data():
    """Weight over time."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT date, weight_kg FROM weight_log ORDER BY date
    """, conn)
    conn.close()
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'])
    return df.set_index('date')


def get_exercise_progress_data(exercise: str):
    """Max weight per session for one exercise."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT date, MAX(weight_kg) as weight_kg
        FROM workouts
        WHERE exercise = ?
        GROUP BY date
        ORDER BY date
    """, conn, params=(exercise,))
    conn.close()
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'])
    return df.set_index('date')


def get_volume_chart_data(exercise: str):
    """Training volume (sets×reps×weight) per session."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT date, SUM(sets * reps * weight_kg) as volume
        FROM workouts
        WHERE exercise = ?
        GROUP BY date
        ORDER BY date
    """, conn, params=(exercise,))
    conn.close()
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'])
    return df.set_index('date')


def get_all_exercises():
    """List of all logged exercises."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT DISTINCT exercise FROM workouts ORDER BY exercise", conn)
    conn.close()
    return df['exercise'].tolist()
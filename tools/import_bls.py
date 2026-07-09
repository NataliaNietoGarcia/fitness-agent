import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database.db import get_connection

# Path to the BLS Excel file
BLS_FILE = "data/docs/BLS_4_0_Daten_2025_DE.xlsx"

# Relevant columns from the BLS file
COL_NAME = "Lebensmittelbezeichnung"
COL_CALORIES = "ENERCC Energie (Kilokalorien) [kcal/100g]"
COL_PROTEIN = "PROT625 Protein (Nx6,25) [g/100g]"
COL_FAT = "FAT Fett [g/100g]"
COL_CARBS = "CHO Kohlenhydrate, verfügbar [g/100g]"
COL_SUGAR = "SUGAR Zucker (Mono- und Disaccharide), gesamt [g/100g]"

def safe_float(value):
    """Convert BLS values to float, handling text like 'Sp', 'n.b.' etc."""
    if pd.isna(value):
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0  # non-numeric entries (traces, not determined) → treat as 0

def create_food_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS food_database")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_database (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_lower TEXT NOT NULL,
            calories REAL,
            protein_g REAL,
            carbs_g REAL,
            fat_g REAL,
            sugar_g REAL
        )
    """)
    # Index for fast text search
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_name ON food_database(name_lower)")
    conn.commit()
    conn.close()


def import_bls():
    print("📖 Reading BLS Excel file...")
    df = pd.read_excel(BLS_FILE)
    print(f"   Found {len(df)} food items")

    # Keep only relevant columns
    df = df[[COL_NAME, COL_CALORIES, COL_PROTEIN, COL_CARBS, COL_FAT, COL_SUGAR]]
    df = df.dropna(subset=[COL_NAME])  # remove rows without a name

    create_food_table()

    conn = get_connection()
    cursor = conn.cursor()

    # Clear old data
    cursor.execute("DELETE FROM food_database")

    count = 0
    for _, row in df.iterrows():
        name = str(row[COL_NAME]).strip()
        cursor.execute("""
            INSERT INTO food_database (name, name_lower, calories, protein_g, carbs_g, fat_g, sugar_g)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            name.lower(),
            safe_float(row[COL_CALORIES]),
            safe_float(row[COL_PROTEIN]),
            safe_float(row[COL_CARBS]),
            safe_float(row[COL_FAT]),
            safe_float(row[COL_SUGAR])
        ))
        count += 1

    conn.commit()
    conn.close()
    print(f"✅ Imported {count} food items into the database!")


if __name__ == "__main__":
    import_bls()
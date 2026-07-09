import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_connection


def search_food_options(food_name: str, limit=20):
    """Searches the BLS food database. An exact match wins immediately;
    otherwise returns candidates sorted by relevance (starts-with, then length)."""
    conn = get_connection()
    cursor = conn.cursor()
    search = food_name.lower().strip()

    cursor.execute("""
        SELECT name, calories, protein_g, carbs_g, fat_g, sugar_g
        FROM food_database WHERE name_lower = ? LIMIT 1
    """, (search,))
    exact = cursor.fetchone()
    if exact:
        conn.close()
        return [_row_to_dict(exact)]

    words = search.split()
    conditions = " AND ".join(["name_lower LIKE ?" for _ in words])
    params = [f"%{word}%" for word in words] + [f"{search}%", limit]

    cursor.execute(f"""
        SELECT name, calories, protein_g, carbs_g, fat_g, sugar_g
        FROM food_database
        WHERE {conditions}
        ORDER BY
            CASE WHEN name_lower LIKE ? THEN 0 ELSE 1 END,
            LENGTH(name)
        LIMIT ?
    """, params)
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row):
    return {
        "name": row[0],
        "calories_per_100g": row[1],
        "protein_per_100g": row[2],
        "carbs_per_100g": row[3],
        "fat_per_100g": row[4],
        "sugar_per_100g": row[5]
    }


def get_nutrition_by_exact_name(name_query: str, amount_g: float):
    """Looks up a food by (fuzzy) name match and scales nutrition to the given amount."""
    conn = get_connection()
    cursor = conn.cursor()

    words = name_query.lower().strip().split()
    conditions = " AND ".join(["name_lower LIKE ?" for _ in words])
    params = [f"%{word}%" for word in words]

    cursor.execute(f"""
        SELECT name, calories, protein_g, carbs_g, fat_g, sugar_g
        FROM food_database
        WHERE {conditions}
        ORDER BY LENGTH(name)
        LIMIT 1
    """, params)
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    factor = amount_g / 100
    return {
        "name": row[0],
        "amount_g": amount_g,
        "calories": round(row[1] * factor, 1) if row[1] is not None else 0,
        "protein_g": round(row[2] * factor, 1) if row[2] is not None else 0,
        "carbs_g": round(row[3] * factor, 1) if row[3] is not None else 0,
        "fat_g": round(row[4] * factor, 1) if row[4] is not None else 0,
        "sugar_g": round(row[5] * factor, 1) if row[5] is not None else 0,
        "source": "BLS"
    }


if __name__ == "__main__":
    print(get_nutrition_by_exact_name("Hähnchenbrust", 200))
    print(get_nutrition_by_exact_name("Banane", 120))
    print(get_nutrition_by_exact_name("Reis", 150))
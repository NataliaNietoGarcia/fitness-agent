import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from database.db import get_connection


def search_local(food_name: str):
    """Search the BLS food database in SQLite."""
    conn = get_connection()
    cursor = conn.cursor()
    
    search = food_name.lower().strip()
    
    # 1. Try exact match first
    cursor.execute("""
        SELECT name, calories, protein_g, carbs_g, fat_g
        FROM food_database
        WHERE name_lower = ?
        LIMIT 1
    """, (search,))
    row = cursor.fetchone()
    
    # 2. If no exact match, try partial match
    if not row:
        cursor.execute("""
            SELECT name, calories, protein_g, carbs_g, fat_g
            FROM food_database
            WHERE name_lower LIKE ?
            ORDER BY LENGTH(name)
            LIMIT 1
        """, (f"%{search}%",))
        row = cursor.fetchone()
    
    conn.close()
    
    if not row:
        return None
    
    return {
        "name": row[0],
        "calories_per_100g": row[1],
        "protein_per_100g": row[2],
        "carbs_per_100g": row[3],
        "fat_per_100g": row[4],
        "source": "BLS"
    }




def search_api(food_name: str):
    """Search Open Food Facts API as fallback (for branded products)."""
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": food_name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 5,
        "fields": "product_name,nutriments"
    }
    try:
        response = requests.get(url, params=params, timeout=10,
                                headers={"User-Agent": "FitnessAgent/1.0"})
        if response.status_code != 200:
            return None
        data = response.json()
        for product in data.get("products", []):
            nutriments = product.get("nutriments", {})
            calories = nutriments.get("energy-kcal_100g")
            if calories:
                return {
                    "name": product.get("product_name", food_name),
                    "calories_per_100g": calories,
                    "protein_per_100g": nutriments.get("proteins_100g", 0),
                    "carbs_per_100g": nutriments.get("carbohydrates_100g", 0),
                    "fat_per_100g": nutriments.get("fat_100g", 0),
                    "source": "OpenFoodFacts"
                }
        return None
    except Exception as e:
        print(f"API error: {e}")
        return None


def calculate_nutrition(food_name: str, amount_g: float):
    """Get nutrition for a food. Tries BLS database first, then API."""
    
    food = search_local(food_name)       # 1. BLS database (reliable)
    if not food:
        food = search_api(food_name)     # 2. API fallback (branded products)
    
    if not food:
        return None
    
    factor = amount_g / 100
    return {
        "name": food["name"],
        "amount_g": amount_g,
        "calories": round(food["calories_per_100g"] * factor, 1),
        "protein_g": round(food["protein_per_100g"] * factor, 1),
        "carbs_g": round(food["carbs_per_100g"] * factor, 1),
        "fat_g": round(food["fat_per_100g"] * factor, 1),
        "source": food.get("source", "unknown")
    }

def search_food_options(food_name: str, limit=8):
    """Search foods - matches all words in any order."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Split into individual words
    words = food_name.lower().strip().split()
    
    # Build a query that requires ALL words to appear
    conditions = " AND ".join(["name_lower LIKE ?" for _ in words])
    params = [f"%{word}%" for word in words]
    params.append(limit)
    
    cursor.execute(f"""
        SELECT name, calories, protein_g, carbs_g, fat_g
        FROM food_database
        WHERE {conditions}
        ORDER BY LENGTH(name)
        LIMIT ?
    """, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "name": row[0],
            "calories_per_100g": row[1],
            "protein_per_100g": row[2],
            "carbs_per_100g": row[3],
            "fat_per_100g": row[4]
        }
        for row in rows
    ]
def search_food_options(food_name: str, limit=8):
    conn = get_connection()
    cursor = conn.cursor()
    search = food_name.lower().strip()
    
    # 1. Check for EXACT match first
    cursor.execute("""
        SELECT name, calories, protein_g, carbs_g, fat_g
        FROM food_database
        WHERE name_lower = ?
        LIMIT 1
    """, (search,))
    exact = cursor.fetchone()
    
    if exact:
        conn.close()
        return [{
            "name": exact[0],
            "calories_per_100g": exact[1],
            "protein_per_100g": exact[2],
            "carbs_per_100g": exact[3],
            "fat_per_100g": exact[4]
        }]  # only ONE result → no clarification needed
    
    # 2. Otherwise multi-word search
    words = search.split()
    conditions = " AND ".join(["name_lower LIKE ?" for _ in words])
    params = [f"%{word}%" for word in words]
    params.append(limit)
    
    cursor.execute(f"""
        SELECT name, calories, protein_g, carbs_g, fat_g
        FROM food_database
        WHERE {conditions}
        ORDER BY LENGTH(name)
        LIMIT ?
    """, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "name": row[0],
            "calories_per_100g": row[1],
            "protein_per_100g": row[2],
            "carbs_per_100g": row[3],
            "fat_per_100g": row[4]
        }
        for row in rows
    ]

def get_nutrition_by_exact_name(name_query: str, amount_g: float):
    conn = get_connection()
    cursor = conn.cursor()
    
    words = name_query.lower().strip().split()
    conditions = " AND ".join(["name_lower LIKE ?" for _ in words])
    params = [f"%{word}%" for word in words]
    
    cursor.execute(f"""
        SELECT name, calories, protein_g, carbs_g, fat_g
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
        "calories": round(row[1] * factor, 1),
        "protein_g": round(row[2] * factor, 1),
        "carbs_g": round(row[3] * factor, 1),
        "fat_g": round(row[4] * factor, 1),
        "source": "BLS"
    }


if __name__ == "__main__":
    print(calculate_nutrition("Hähnchenbrust", 200))
    print(calculate_nutrition("Banane", 120))
    print(calculate_nutrition("Reis", 150))
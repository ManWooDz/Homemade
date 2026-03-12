import sqlite3
import json
import os
import re

def image_path(name):
    name = name.lower()
    name = re.sub(r"[']", "", name)
    name = name.replace(" ", "_")
    return f"images/ingredients/{name}.jpg"

def generate_ingredients_table():
    db_path = os.path.join(os.path.dirname(__file__), "recipes.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create ingredients table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        image TEXT
    )
    """)

    # Get all ingredients from recipes
    cursor.execute("SELECT ingredients FROM base_recipes")
    rows = cursor.fetchall()

    unique_ingredients = set()

    for row in rows:
        ingredient_list = json.loads(row[0])
        for ingredient in ingredient_list:
            unique_ingredients.add(ingredient.strip().lower())

    # Insert unique ingredients
    for ingredient in sorted(unique_ingredients):
        cursor.execute(
            "INSERT OR IGNORE INTO ingredients (name,image) VALUES (?,?)",
            (ingredient,image_path(ingredient))
        )

    conn.commit()
    conn.close()

    print(f"✅ Inserted {len(unique_ingredients)} unique ingredients into ingredients table")

if __name__ == "__main__":
    generate_ingredients_table()
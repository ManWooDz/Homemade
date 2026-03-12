import sqlite3
import json
import os

def setup_mock_db():
    db_path = os.path.join(os.path.dirname(__file__), 'recipes.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop old table to start fresh with new schema
    cursor.execute('DROP TABLE IF EXISTS base_recipes')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS base_recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        short_description TEXT,
        ratings REAL,
        review INTEGER,
        image TEXT,
        tags TEXT,   
        ingredients TEXT, 
        nutrition TEXT,   
        instructions TEXT 
    )
    ''')
    
    # 6 Requested Menus
    mock_recipes = [
        {
            "name": "Superfood Veggie",
            "short_description": "A vibrant bowl packed with nutrient-dense vegetables and grains.",
            "ratings": 4.8,
            "review": 72,
            "image": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80",
            "tags": ["Healthy / Diet", "Quick & Easy"],
            "ingredients": ["kale", "quinoa", "avocado", "cherry tomatoes", "pumpkin seeds"],
            "nutrition": {"calories": 350, "protein_g": 12, "carbs_g": 35, "fat_g": 18},
            "instructions": ["1. Cook quinoa according to package.", "2. Massage kale with olive oil and lemon juice.", "3. Chop avocado and tomatoes.", "4. Combine all ingredients in a bowl.", "5. Top with pumpkin seeds and desired dressing."]
        },
        {
            "name": "Fresh Power Salad",
            "short_description": "Crisp greens topped with crunchy vegetables and a zesty vinaigrette.",
            "ratings": 4.6,
            "review": 105,
            "image": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80",
            "tags": ["Healthy / Diet", "Quick & Easy"],
            "ingredients": ["spinach", "cucumber", "bell pepper", "red onion", "feta cheese", "balsamic vinaigrette"],
            "nutrition": {"calories": 280, "protein_g": 8, "carbs_g": 15, "fat_g": 22},
            "instructions": ["1. Wash and dry spinach.", "2. Dice cucumber and bell pepper.", "3. Thinly slice the red onion.", "4. Toss greens and veggies together.", "5. Sprinkle with feta and dress before serving."]
        },
        {
            "name": "Rainbow Healthy",
            "short_description": "Eat the rainbow with this colorful and energizing vegetable mix.",
            "ratings": 4.9,
            "review": 210,
            "image": "https://images.unsplash.com/photo-1490645935967-10de6ba17061?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80",
            "tags": ["Healthy / Diet", "Quick & Easy"],
            "ingredients": ["purple cabbage", "carrot", "edamame", "yellow bell pepper", "cherry tomatoes", "sesame dressing"],
            "nutrition": {"calories": 310, "protein_g": 15, "carbs_g": 28, "fat_g": 14},
            "instructions": ["1. Shred the purple cabbage.", "2. Julienne or grate the carrots.", "3. Slice the yellow bell pepper and halve the tomatoes.", "4. Arrange vegetables by color in a bowl.", "5. Drizzle with sesame dressing and toss."]
        },
        {
            "name": "Chashu Ramen",
            "short_description": "Rich pork bone broth served with tender pork belly, noodles, and a soft-boiled egg.",
            "ratings": 4.9,
            "review": 340,
            "image": "https://images.unsplash.com/photo-1557872943-16a5ac26437e?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80",
            "tags": ["Asian Food", "Japanese Food"],
            "ingredients": ["ramen noodles", "pork belly (chashu)", "tonkotsu broth", "soft-boiled egg", "green onion", "nori seaweed", "soy sauce"],
            "nutrition": {"calories": 750, "protein_g": 35, "carbs_g": 65, "fat_g": 40},
            "instructions": ["1. Heat the tonkotsu broth until simmering.", "2. Boil ramen noodles according to package instructions.", "3. Slice the chashu pork belly and warm slightly.", "4. Place cooked noodles in a bowl and pour hot broth over.", "5. Top with chashu, halved egg, green onions, and nori."]
        },
        {
            "name": "Padthai with shrimps",
            "short_description": "Classic Thai stir-fried rice noodles with fresh shrimp, peanuts, and tamarind sauce.",
            "ratings": 4.7,
            "review": 185,
            "image": "https://images.unsplash.com/photo-1559314809-0d155014e29e?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80",
            "tags": ["Asian Food", "Thai Food"],
            "ingredients": ["rice noodles", "shrimp", "egg", "bean sprouts", "chives", "tofu", "tamarind paste", "fish sauce", "palm sugar", "peanuts"],
            "nutrition": {"calories": 520, "protein_g": 25, "carbs_g": 60, "fat_g": 18},
            "instructions": ["1. Soak rice noodles until pliable.", "2. Mix tamarind, fish sauce, and palm sugar for the sauce.", "3. Stir-fry shrimp and tofu, then push to the side and scramble the egg.", "4. Add noodles and sauce, stir-frying until absorbed.", "5. Toss in bean sprouts and chives, then serve with crushed peanuts."]
        },
        {
            "name": "Stir-Fried Basil with pork",
            "short_description": "Spicy minced pork stir-fried with holy basil, garlic, and chilies (Pad Kra Pao).",
            "ratings": 4.8,
            "review": 450,
            "image": "https://thewoksoflife.com/wp-content/uploads/2016/08/pad-kra-pao-7.jpg",
            "tags": ["Asian Food", "Thai Food"],
            "ingredients": ["minced pork", "holy basil leaves", "garlic", "bird's eye chilies", "oyster sauce", "soy sauce", "fish sauce", "sugar", "vegetable oil"],
            "nutrition": {"calories": 480, "protein_g": 28, "carbs_g": 12, "fat_g": 35},
            "instructions": ["1. Pound garlic and chilies in a mortar.", "2. Heat oil in a wok and fry the garlic-chili mixture until fragrant.", "3. Add minced pork and stir-fry until almost cooked.", "4. Season with oyster sauce, soy sauce, fish sauce, and sugar.", "5. Toss in holy basil leaves, stir quickly, and remove from heat."]
        }
    ]

    for recipe in mock_recipes:
        cursor.execute('''
        INSERT INTO base_recipes (name, short_description, ratings, review, image, tags, ingredients, nutrition, instructions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            recipe["name"],
            recipe["short_description"],
            recipe["ratings"],
            recipe["review"],
            recipe["image"],
            json.dumps(recipe["tags"], ensure_ascii=False),
            json.dumps(recipe["ingredients"], ensure_ascii=False),
            json.dumps(recipe["nutrition"], ensure_ascii=False),
            json.dumps(recipe["instructions"], ensure_ascii=False)
        ))

    conn.commit()
    conn.close()
    print("✅ อัปเดต SQLite Database สำหรับเมนูใหม่ 6 เมนูเรียบร้อยแล้ว!")

if __name__ == "__main__":
    setup_mock_db()
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
            "image": "images/menus/superfood_veggie.png",
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
            "image": "images/menus/fresh_power_salad.png",
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
            "image": "images/menus/rainbow_healthy.png",
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
            "image": "images/menus/chashu_ramen.png",
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
            "image": "images/menus/padthai.png",
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
            "image": "images/menus/pad_kra_pao.png",
            "tags": ["Asian Food", "Thai Food"],
            "ingredients": ["minced pork", "holy basil leaves", "garlic", "bird's eye chilies", "oyster sauce", "soy sauce", "fish sauce", "sugar", "vegetable oil"],
            "nutrition": {"calories": 480, "protein_g": 28, "carbs_g": 12, "fat_g": 35},
            "instructions": ["1. Pound garlic and chilies in a mortar.", "2. Heat oil in a wok and fry the garlic-chili mixture until fragrant.", "3. Add minced pork and stir-fry until almost cooked.", "4. Season with oyster sauce, soy sauce, fish sauce, and sugar.", "5. Toss in holy basil leaves, stir quickly, and remove from heat."]
        },
        {
            "name": "Greek Salad",
            "short_description": "A refreshing traditional Mediterranean salad with feta and olives.",
            "ratings": 4.5,
            "review": 89,
            "image": "images/menus/greek_salad.png",
            "tags": ["Healthy / Diet", "Western Food", "Quick & Easy"],
            "ingredients": ["feta cheese", "kalamata olives", "cucumber", "cherry tomatoes", "red onion", "olive oil", "oregano"],
            "nutrition": {"calories": 250, "protein_g": 6, "carbs_g": 12, "fat_g": 20},
            "instructions": ["1. Chop cucumber, tomatoes, and red onion.", "2. Combine in a bowl with olives.", "3. Top with blocks of feta cheese.", "4. Drizzle generously with olive oil and sprinkle with oregano."]
        },
        {
            "name": "Grilled Steak",
            "short_description": "Juicy and tender beef steak seared to perfection with garlic butter.",
            "ratings": 4.9,
            "review": 512,
            "image": "images/menus/grilled_steak.png",
            "tags": ["Western Food", "High Protein"],
            "ingredients": ["beef steak", "garlic", "rosemary", "butter", "black pepper", "salt", "olive oil"],
            "nutrition": {"calories": 600, "protein_g": 50, "carbs_g": 2, "fat_g": 45},
            "instructions": ["1. Pat steak dry and season generously with salt and black pepper.", "2. Heat olive oil in a skillet over high heat.", "3. Sear steak for a few minutes on each side.", "4. Add butter, garlic, and rosemary to the pan.", "5. Baste the steak with melted butter until cooked to desired doneness.", "6. Rest for 5 minutes before slicing."]
        },
        {
            "name": "Tom Yum Kung",
            "short_description": "Spicy, sour, and aromatic Thai shrimp soup with fresh herbs.",
            "ratings": 4.8,
            "review": 405,
            "image": "images/menus/tom_yum_kung.png",
            "tags": ["Asian Food", "Thai Food", "Spicy"],
            "ingredients": ["shrimp", "lemongrass", "galangal", "kaffir lime leaves", "bird's eye chilies", "fish sauce", "lime juice", "mushrooms", "cilantro", "chili paste"],
            "nutrition": {"calories": 220, "protein_g": 24, "carbs_g": 18, "fat_g": 8},
            "instructions": ["1. Bring water or broth to a boil and add smashed lemongrass, galangal, and kaffir lime leaves.", "2. Add mushrooms and simmer for a few minutes.", "3. Add shrimp and cook until just pink.", "4. Stir in chili paste, fish sauce, and fresh chilies.", "5. Turn off heat and add lime juice.", "6. Garnish with cilantro and serve hot."]
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
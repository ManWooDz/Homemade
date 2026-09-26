"""Seeds the Postgres dev database: base_recipes, recipe_ingredient_images,
and one dev user (see main.py DEV_USER_EMAIL — bridge until step 8 JWT auth
lands, see spec.md). Ports the mock-recipe data that used to live in
setup_db.py / setup_ingredients.py (SQLite, now deprecated).

Usage: python database/seed_postgres.py (run from backend/, with venv active)
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.db import SessionLocal
from database.models import BaseRecipe, RecipeIngredientImage, User
from nutrition.calculator import compute_from_quantities

DEV_USER_EMAIL = "dev@local"

# `ingredient_quantities` gram amounts are team-estimated typical portions,
# not cited from any specific real source recipe.
MOCK_RECIPES = [
    {
        "name": "Superfood Veggie",
        "short_description": "A vibrant bowl packed with nutrient-dense vegetables and grains.",
        "ratings": 4.8,
        "review": 72,
        "image": "images/menus/superfood_veggie.png",
        "tags": ["Healthy / Diet", "Quick & Easy"],
        "ingredients": ["kale", "quinoa", "avocado", "cherry tomatoes", "pumpkin seeds"],
        "servings": 1,
        "ingredient_quantities": [
            {"name": "kale", "quantity_g": 50},
            {"name": "quinoa", "quantity_g": 100},
            {"name": "avocado", "quantity_g": 75},
            {"name": "cherry tomatoes", "quantity_g": 60},
            {"name": "pumpkin seeds", "quantity_g": 15},
        ],
        "nutrition": {"calories": 350, "protein_g": 12, "carbs_g": 35, "fat_g": 18},
        "instructions": ["1. Cook quinoa according to package.", "2. Massage kale with olive oil and lemon juice.", "3. Chop avocado and tomatoes.", "4. Combine all ingredients in a bowl.", "5. Top with pumpkin seeds and desired dressing."],
    },
    {
        "name": "Fresh Power Salad",
        "short_description": "Crisp greens topped with crunchy vegetables and a zesty vinaigrette.",
        "ratings": 4.6,
        "review": 105,
        "image": "images/menus/fresh_power_salad.png",
        "tags": ["Healthy / Diet", "Quick & Easy"],
        "ingredients": ["spinach", "cucumber", "bell pepper", "red onion", "feta cheese", "balsamic vinaigrette"],
        "servings": 1,
        "ingredient_quantities": [
            {"name": "spinach", "quantity_g": 60},
            {"name": "cucumber", "quantity_g": 50},
            {"name": "bell pepper", "quantity_g": 40},
            {"name": "red onion", "quantity_g": 20},
            {"name": "feta cheese", "quantity_g": 40},
            {"name": "balsamic vinaigrette", "quantity_g": 15},
        ],
        "nutrition": {"calories": 280, "protein_g": 8, "carbs_g": 15, "fat_g": 22},
        "instructions": ["1. Wash and dry spinach.", "2. Dice cucumber and bell pepper.", "3. Thinly slice the red onion.", "4. Toss greens and veggies together.", "5. Sprinkle with feta and dress before serving."],
    },
    {
        "name": "Rainbow Healthy",
        "short_description": "Eat the rainbow with this colorful and energizing vegetable mix.",
        "ratings": 4.9,
        "review": 210,
        "image": "images/menus/rainbow_healthy.png",
        "tags": ["Healthy / Diet", "Quick & Easy"],
        "ingredients": ["purple cabbage", "carrot", "edamame", "yellow bell pepper", "cherry tomatoes", "sesame dressing"],
        "servings": 1,
        "ingredient_quantities": [
            {"name": "purple cabbage", "quantity_g": 60},
            {"name": "carrot", "quantity_g": 40},
            {"name": "edamame", "quantity_g": 50},
            {"name": "yellow bell pepper", "quantity_g": 40},
            {"name": "cherry tomatoes", "quantity_g": 50},
            {"name": "sesame dressing", "quantity_g": 15},
        ],
        "nutrition": {"calories": 310, "protein_g": 15, "carbs_g": 28, "fat_g": 14},
        "instructions": ["1. Shred the purple cabbage.", "2. Julienne or grate the carrots.", "3. Slice the yellow bell pepper and halve the tomatoes.", "4. Arrange vegetables by color in a bowl.", "5. Drizzle with sesame dressing and toss."],
    },
    {
        "name": "Chashu Ramen",
        "short_description": "Rich pork bone broth served with tender pork belly, noodles, and a soft-boiled egg.",
        "ratings": 4.9,
        "review": 340,
        "image": "images/menus/chashu_ramen.png",
        "tags": ["Asian Food", "Japanese Food"],
        "ingredients": ["ramen noodles", "pork belly (chashu)", "tonkotsu broth", "soft-boiled egg", "green onion", "nori seaweed", "soy sauce"],
        "servings": 1,
        "ingredient_quantities": [
            {"name": "ramen noodles", "quantity_g": 150},
            {"name": "pork belly (chashu)", "quantity_g": 60},
            {"name": "tonkotsu broth", "quantity_g": 400},
            {"name": "soft-boiled egg", "quantity_g": 55},
            {"name": "green onion", "quantity_g": 10},
            {"name": "nori seaweed", "quantity_g": 3},
            {"name": "soy sauce", "quantity_g": 15},
        ],
        "nutrition": {"calories": 750, "protein_g": 35, "carbs_g": 65, "fat_g": 40},
        "instructions": ["1. Heat the tonkotsu broth until simmering.", "2. Boil ramen noodles according to package instructions.", "3. Slice the chashu pork belly and warm slightly.", "4. Place cooked noodles in a bowl and pour hot broth over.", "5. Top with chashu, halved egg, green onions, and nori."],
    },
    {
        "name": "Padthai with shrimps",
        "short_description": "Classic Thai stir-fried rice noodles with fresh shrimp, peanuts, and tamarind sauce.",
        "ratings": 4.7,
        "review": 185,
        "image": "images/menus/padthai.png",
        "tags": ["Asian Food", "Thai Food"],
        "ingredients": ["rice noodles", "shrimp", "egg", "bean sprouts", "chives", "tofu", "tamarind paste", "fish sauce", "palm sugar", "peanuts"],
        "servings": 1,
        "ingredient_quantities": [
            {"name": "rice noodles", "quantity_g": 120},
            {"name": "shrimp", "quantity_g": 80},
            {"name": "egg", "quantity_g": 50},
            {"name": "bean sprouts", "quantity_g": 40},
            {"name": "chives", "quantity_g": 10},
            {"name": "tofu", "quantity_g": 40},
            {"name": "tamarind paste", "quantity_g": 20},
            {"name": "fish sauce", "quantity_g": 15},
            {"name": "palm sugar", "quantity_g": 15},
            {"name": "peanuts", "quantity_g": 15},
        ],
        "nutrition": {"calories": 520, "protein_g": 25, "carbs_g": 60, "fat_g": 18},
        "instructions": ["1. Soak rice noodles until pliable.", "2. Mix tamarind, fish sauce, and palm sugar for the sauce.", "3. Stir-fry shrimp and tofu, then push to the side and scramble the egg.", "4. Add noodles and sauce, stir-frying until absorbed.", "5. Toss in bean sprouts and chives, then serve with crushed peanuts."],
    },
    {
        "name": "Stir-Fried Basil with pork",
        "short_description": "Spicy minced pork stir-fried with holy basil, garlic, and chilies (Pad Kra Pao).",
        "ratings": 4.8,
        "review": 450,
        "image": "images/menus/pad_kra_pao.png",
        "tags": ["Asian Food", "Thai Food"],
        "ingredients": ["minced pork", "holy basil leaves", "garlic", "bird's eye chilies", "oyster sauce", "soy sauce", "fish sauce", "sugar", "vegetable oil"],
        "servings": 1,
        "ingredient_quantities": [
            {"name": "minced pork", "quantity_g": 150},
            {"name": "holy basil leaves", "quantity_g": 20},
            {"name": "garlic", "quantity_g": 10},
            {"name": "bird's eye chilies", "quantity_g": 5},
            {"name": "oyster sauce", "quantity_g": 15},
            {"name": "soy sauce", "quantity_g": 10},
            {"name": "fish sauce", "quantity_g": 10},
            {"name": "sugar", "quantity_g": 5},
            {"name": "vegetable oil", "quantity_g": 15},
        ],
        "nutrition": {"calories": 480, "protein_g": 28, "carbs_g": 12, "fat_g": 35},
        "instructions": ["1. Pound garlic and chilies in a mortar.", "2. Heat oil in a wok and fry the garlic-chili mixture until fragrant.", "3. Add minced pork and stir-fry until almost cooked.", "4. Season with oyster sauce, soy sauce, fish sauce, and sugar.", "5. Toss in holy basil leaves, stir quickly, and remove from heat."],
    },
    {
        "name": "Greek Salad",
        "short_description": "A refreshing traditional Mediterranean salad with feta and olives.",
        "ratings": 4.5,
        "review": 89,
        "image": "images/menus/greek_salad.png",
        "tags": ["Healthy / Diet", "Western Food", "Quick & Easy"],
        "ingredients": ["feta cheese", "kalamata olives", "cucumber", "cherry tomatoes", "red onion", "olive oil", "oregano"],
        "servings": 1,
        "ingredient_quantities": [
            {"name": "feta cheese", "quantity_g": 50},
            {"name": "kalamata olives", "quantity_g": 30},
            {"name": "cucumber", "quantity_g": 60},
            {"name": "cherry tomatoes", "quantity_g": 60},
            {"name": "red onion", "quantity_g": 20},
            {"name": "olive oil", "quantity_g": 15},
            {"name": "oregano", "quantity_g": 1},
        ],
        "nutrition": {"calories": 250, "protein_g": 6, "carbs_g": 12, "fat_g": 20},
        "instructions": ["1. Chop cucumber, tomatoes, and red onion.", "2. Combine in a bowl with olives.", "3. Top with blocks of feta cheese.", "4. Drizzle generously with olive oil and sprinkle with oregano."],
    },
    {
        "name": "Grilled Steak",
        "short_description": "Juicy and tender beef steak seared to perfection with garlic butter.",
        "ratings": 4.9,
        "review": 512,
        "image": "images/menus/grilled_steak.png",
        "tags": ["Western Food", "High Protein"],
        "ingredients": ["beef steak", "garlic", "rosemary", "butter", "black pepper", "salt", "olive oil"],
        "servings": 1,
        "ingredient_quantities": [
            {"name": "beef steak", "quantity_g": 200},
            {"name": "garlic", "quantity_g": 5},
            {"name": "rosemary", "quantity_g": 2},
            {"name": "butter", "quantity_g": 15},
            {"name": "black pepper", "quantity_g": 1},
            {"name": "salt", "quantity_g": 2},
            {"name": "olive oil", "quantity_g": 10},
        ],
        "nutrition": {"calories": 600, "protein_g": 50, "carbs_g": 2, "fat_g": 45},
        "instructions": ["1. Pat steak dry and season generously with salt and black pepper.", "2. Heat olive oil in a skillet over high heat.", "3. Sear steak for a few minutes on each side.", "4. Add butter, garlic, and rosemary to the pan.", "5. Baste the steak with melted butter until cooked to desired doneness.", "6. Rest for 5 minutes before slicing."],
    },
    {
        "name": "Tom Yum Kung",
        "short_description": "Spicy, sour, and aromatic Thai shrimp soup with fresh herbs.",
        "ratings": 4.8,
        "review": 405,
        "image": "images/menus/tom_yum_kung.png",
        "tags": ["Asian Food", "Thai Food", "Spicy"],
        "ingredients": ["shrimp", "lemongrass", "galangal", "kaffir lime leaves", "bird's eye chilies", "fish sauce", "lime juice", "mushrooms", "cilantro", "chili paste"],
        "servings": 1,
        "ingredient_quantities": [
            {"name": "shrimp", "quantity_g": 100},
            {"name": "lemongrass", "quantity_g": 10},
            {"name": "galangal", "quantity_g": 5},
            {"name": "kaffir lime leaves", "quantity_g": 2},
            {"name": "bird's eye chilies", "quantity_g": 5},
            {"name": "fish sauce", "quantity_g": 15},
            {"name": "lime juice", "quantity_g": 15},
            {"name": "mushrooms", "quantity_g": 50},
            {"name": "cilantro", "quantity_g": 5},
            {"name": "chili paste", "quantity_g": 15},
        ],
        "nutrition": {"calories": 220, "protein_g": 24, "carbs_g": 18, "fat_g": 8},
        "instructions": ["1. Bring water or broth to a boil and add smashed lemongrass, galangal, and kaffir lime leaves.", "2. Add mushrooms and simmer for a few minutes.", "3. Add shrimp and cook until just pink.", "4. Stir in chili paste, fish sauce, and fresh chilies.", "5. Turn off heat and add lime juice.", "6. Garnish with cilantro and serve hot."],
    },
]


def image_path(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[']", "", name)
    name = name.replace(" ", "_")

    base_dir = os.path.join(os.path.dirname(__file__), "..", "images", "ingredients")
    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        if os.path.exists(os.path.join(base_dir, f"{name}{ext}")):
            return f"images/ingredients/{name}{ext}"
    return f"images/ingredients/{name}.jpg"


def seed():
    db = SessionLocal()
    try:
        if db.query(User).filter_by(email=DEV_USER_EMAIL).first() is None:
            db.add(User(email=DEV_USER_EMAIL, hashed_password=None))
        # Committed on its own so the dev user survives even if a later
        # step (recipes/images) fails.
        db.commit()

        fallback_recipes: list[str] = []
        for recipe in MOCK_RECIPES:
            try:
                nutrition = compute_from_quantities(db, recipe["ingredient_quantities"], recipe["servings"])
            except ValueError as e:
                # Typically: USDA import hasn't run yet (no USDA_API_KEY) or
                # a DB row is incomplete. Degrade for THIS recipe only, and
                # loudly -- the hand-typed dict is not grounded.
                print(
                    f"[seed] WARNING: could not compute nutrition for '{recipe['name']}': {e} "
                    "-- falling back to the hand-typed nutrition dict for this recipe only"
                )
                nutrition = recipe["nutrition"]
                fallback_recipes.append(recipe["name"])
            existing = db.query(BaseRecipe).filter_by(name=recipe["name"]).first()
            if existing:
                existing.servings = recipe["servings"]
                existing.ingredient_quantities = recipe["ingredient_quantities"]
                existing.nutrition = nutrition
            else:
                recipe_data = dict(recipe)
                recipe_data["nutrition"] = nutrition
                db.add(BaseRecipe(**recipe_data))

        unique_ingredients = {
            ing.strip().lower() for recipe in MOCK_RECIPES for ing in recipe["ingredients"]
        }
        existing_images = {row.name for row in db.query(RecipeIngredientImage).all()}
        for ingredient in sorted(unique_ingredients - existing_images):
            db.add(RecipeIngredientImage(name=ingredient, image=image_path(ingredient)))

        db.commit()
        print(f"seeded: dev user, {len(MOCK_RECIPES)} base_recipes, {len(unique_ingredients)} recipe_ingredient_images")
        if fallback_recipes:
            print(
                f"[seed] WARNING: {len(fallback_recipes)} of {len(MOCK_RECIPES)} base_recipes use the "
                f"hand-typed (NOT computed) nutrition fallback: {fallback_recipes}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    seed()

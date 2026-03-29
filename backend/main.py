from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import sqlite3
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List, Dict, Any

#
#       uvicorn main:app --reload
# 

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Gemini API
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    print("Warning: ไม่พบ GEMINI_API_KEY ในไฟล์ .env")
    client = None

app = FastAPI(title="Homemade Recipe API")

origins =[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    db_path = os.path.join(os.path.dirname(__file__), "database", "recipes.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'Other',
                quantity TEXT DEFAULT '1',
                image TEXT
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"Error initializing DB: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# Serves local images directory
app.mount("/images", StaticFiles(directory="images"), name="images")


BASIC_INGREDIENTS = ["salt", "pepper", "oil", "soy sauce", "fish sauce", "sugar", "water"]

BAD_FLAVOR_PAIRS = [
    ("milk", "fish sauce"),
    ("chocolate", "garlic"),
]

# -------------------------------
# 1. Ingredient Check (No hallucination)
# -------------------------------
def check_ingredients(recipe, user_ingredients):
    for item in recipe["adjusted_ingredients"]:
        # The LLM writes adjusted_ingredients in Thai (non-ASCII).
        # We can only validate English/ASCII ingredient names, so skip Thai-script lines.
        if not item.isascii():
            continue
        name = item.lower()
        if not any(ing in name for ing in user_ingredients + BASIC_INGREDIENTS):
            return False, f"Invalid ingredient found: {item}"
    return True, "OK"


# -------------------------------
# 2. Flavor Check
# -------------------------------
def check_flavor(recipe):
    ingredients_text = " ".join(recipe["adjusted_ingredients"]).lower()
    
    for a, b in BAD_FLAVOR_PAIRS:
        if a in ingredients_text and b in ingredients_text:
            return False, f"Bad flavor combination: {a} + {b}"
    
    return True, "OK"


# -------------------------------
# 3. Cooking Logic Check
# -------------------------------
def check_logic(recipe):
    instructions = " ".join(recipe["instructions"]).lower()

    has_oil = "oil" in instructions or "น้ำมัน" in instructions

    if "ทอด" in instructions and not has_oil:
        return False, "Frying without oil"

    if "ผัด" in instructions and not has_oil:
        return False, "Stir-fry without oil"

    return True, "OK"


# -------------------------------
# 4. Nutrition Check
# -------------------------------
def check_nutrition(recipe):
    nutrition = recipe["nutrition"]

    if nutrition["calories"] <= 0 or nutrition["calories"] > 1500:
        return False, "Unrealistic calories"

    if nutrition["protein_g"] < 0:
        return False, "Invalid protein value"

    return True, "OK"


# -------------------------------
# 5. Allergy Check
# -------------------------------
def check_allergy(recipe, user_prefs):
    ingredients_text = " ".join(recipe["adjusted_ingredients"]).lower()
    
    if "allergic to shrimp" in str(user_prefs).lower() and "shrimp" in ingredients_text:
        return False, "Allergy violation: shrimp found"

    return True, "OK"


# -------------------------------
# 6. Core Ingredient Check
# -------------------------------
def check_core(recipe, user_ingredients):
    name = recipe["recipe_name"].lower()

    if "steak" in name and not any("beef" in ing for ing in user_ingredients):
        return False, "Missing core ingredient: beef for steak"

    return True, "OK"


# -------------------------------
# Main Validation Pipeline
# -------------------------------
def validate_recipe(recipe, user_ingredients, user_prefs):
    checks = [
        check_ingredients,
        check_flavor,
        check_logic,
        check_nutrition,
        check_allergy,
        check_core
    ]

    # Map each check to how it should be called
    single_arg_checks = {check_flavor, check_logic, check_nutrition}

    for check in checks:
        if check in single_arg_checks:
            valid, msg = check(recipe)
        elif check == check_allergy:
            valid, msg = check(recipe, user_prefs)
        else:  # check_ingredients, check_core
            valid, msg = check(recipe, user_ingredients)

        if not valid:
            return {
                "status": "fail",
                "reason": msg
            }

    return {
        "status": "pass",
        "recipe": recipe
    }

# ==========================================
# LLM Agent
# ==========================================
def call_agentic_llm(ingredients, user_prefs, base_recipe):
    print("Agentic LLM (Gemini) is thinking and calculating...")
    
    if not client:
        return {"error": "API Key is missing. Please check your .env file."}
    
    try:
        prompt = f"""
        คุณคือ Executive Chef และนักโภชนาการคลินิกที่มีประสบการณ์สูง
        หน้าที่ของคุณคือการนำ "สูตรอาหารตั้งต้น" มาดัดแปลงให้เข้ากับ "วัตถุดิบที่ผู้ใช้มี" และ "เงื่อนไขโภชนาการ" 
        โดยต้องคำนึงถึงความปลอดภัยทางอาหาร (Food Safety) และหลักการทำอาหารที่ถูกต้องเป็นอันดับหนึ่ง

        ข้อมูลของคุณมีดังนี้:
        1. วัตถุดิบที่ผู้ใช้มี : {ingredients}
        2. เงื่อนไขและข้อควรระวังของผู้ใช้: {user_prefs}
        3. สูตรอาหารตั้งต้น (อ้างอิงโภชนาการจากสูตรนี้): {base_recipe}
        
        กฎเหล็กด้านความปลอดภัยและคุณภาพ (MUST FOLLOW STRICTLY):
        1. ความปลอดภัยอาหาร (Food Safety): ห้ามแนะนำให้รับประทานเนื้อสัตว์ดิบ (ยกเว้นวัตถุดิบที่ระบุว่าทานดิบได้) ต้องระบุการทำเนื้อสัตว์ ไก่ หมู หรืออาหารทะเลให้สุกอย่างชัดเจน และห้ามมีขั้นตอนที่เสี่ยงต่อการปนเปื้อนข้าม (Cross-contamination)
        2. ข้อควรระวังการแพ้ (Allergy Risks): ต้องตรวจสอบและปฏิบัติตาม {user_prefs} อย่างเคร่งครัด หากมีการแพ้อาหาร ห้ามใส่วัตถุดิบนั้นและวัตถุดิบแฝงเด็ดขาด
        3. ปริมาณและสัดส่วน (Logical Proportions): กำหนดปริมาณวัตถุดิบและเครื่องปรุงให้อยู่ในเกณฑ์มาตรฐานที่มนุษย์ทานได้จริง ห้ามใส่เครื่องปรุงรสจัดเกินไป (เช่น เกลือ 5 ช้อนโต๊ะ หรือน้ำมัน 1 ถ้วย)
        4. ขั้นตอนสมเหตุสมผล (Logical Workflow): ลำดับขั้นตอนการทำอาหารต้องถูกต้องตามหลักฟิสิกส์การทำอาหาร (เช่น ต้องเจียวกระเทียมกับน้ำมันก่อนใส่น้ำ, ทอดต้องใช้น้ำมัน, รวนเนื้อสัตว์ก่อนใส่ผักที่สุกง่าย)
        5. ความเข้ากันของรสชาติ (Flavor Pairing): หากวัตถุดิบที่มีจับคู่กันแล้วรสชาติจะแย่มาก (เช่น นม + น้ำปลา) ให้เลือกตัดวัตถุดิบบางอย่างออกอย่างสมเหตุสมผล ดีกว่าฝืนผสมกัน
        6. ห้ามมโนวัตถุดิบ (No Hallucination): ใช้วัตถุดิบเฉพาะที่มีใน {ingredients} และสามารถเสริมด้วยเครื่องปรุงพื้นฐานสามัญประจำบ้าน (เกลือ, พริกไทย, น้ำมัน, น้ำปลา, ซีอิ๊ว, น้ำตาล, น้ำเปล่า) ได้เท่านั้น ห้ามคิดค้นวัตถุดิบขึ้นมาเอง

        คำสั่ง:
        - ปรับปรุงขั้นตอนและคำนวณโภชนาการใหม่ (Calories, Protein, Carbs, Fat) ให้ใกล้เคียงความเป็นจริงที่สุด
        - ตอบกลับมาเป็นรูปแบบ JSON เท่านั้น ห้ามมีข้อความอื่นปนเด็ดขาด โดยใช้โครงสร้างดังนี้:
        
        {{
            "recipe_name": "ชื่อเมนูที่สมเหตุสมผล (MUST BE IN ENGLISH)",
            "adjusted_ingredients": ["วัตถุดิบ 1 (พร้อมระบุปริมาณที่ถูกต้อง IN THAI)", "วัตถุดิบ 2 (IN THAI)"],
            "diet_tags": ["tag1 (MUST BE IN ENGLISH)", "tag2 (MUST BE IN ENGLISH)"],
            "nutrition": {{
                "calories": ตัวเลข,
                "protein_g": ตัวเลข,
                "carbs_g": ตัวเลข,
                "fat_g": ตัวเลข
            }},
            "instructions": ["1. ขั้นตอนแรก (IN THAI)...", "2. ขั้นตอนต่อไป (IN THAI)..."],
            "safety_warning": "คำเตือนความปลอดภัย (IN THAI) เช่น เรื่องการแพ้อาหาร (หากไม่มีให้ใส่ข้อความว่า 'ระวังความร้อนขณะประกอบอาหาร')"
        }}
        """
        
        # API to Gemini
        response = client.models.generate_content(
            # model='gemini-2.5-flash-lite',
            model='gemini-3.1-flash-lite-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        
        result_json = json.loads(response.text)
        return result_json

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return {
            "error": "ไม่สามารถสร้างสูตรอาหารได้ในขณะนี้",
            "details": str(e)
        }

# ==========================================
#  API Endpoint (ช่องทางรับส่งข้อมูล)
# ==========================================

# get recipes from database(SQLite)
@app.get("/api/recipes")
async def get_all_recipes():
    db_path = os.path.join(os.path.dirname(__file__), "database", "recipes.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, image FROM ingredients")
        ingredient_rows = cursor.fetchall()
        ingredient_map = {row[0].lower().strip(): row[1] for row in ingredient_rows}

        cursor.execute("SELECT * FROM base_recipes")
        rows = cursor.fetchall()
        
        recipes = []
        for row in rows:
            raw_ingredients = json.loads(row[7])
            mapped_ingredients = []
            for ing in raw_ingredients:
                img_path = ingredient_map.get(ing.lower().strip())
                img_url = f"http://localhost:8000/{img_path}" if img_path else "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=150"
                mapped_ingredients.append({
                    "name": ing,
                    "image": img_url
                })

            image_val = row[5]
            if image_val and not image_val.startswith("http"):
                image_val = f"http://localhost:8000/{image_val}"

            recipes.append({
                "id": row[0],
                "name": row[1],
                "short_description": row[2],
                "ratings": row[3],
                "review": row[4],
                "image": image_val,
                "tags": json.loads(row[6]),
                "ingredients": mapped_ingredients,
                "nutrition": json.loads(row[8]),
                "instructions": json.loads(row[9])
            })
        conn.close()
        return {"status": "success", "data": recipes}
    except Exception as e:
        return {"status": "error", "message": str(e)}



class UserIngredientCreate(BaseModel):
    name: str
    category: str = "Other"
    quantity: str = "1"
    image: str = "http://localhost:8000/images/No-image-available.png"

# get ingredient images from folder images/ingredients
@app.get("/api/ingredient-images")
async def get_ingredient_images():
    images_dir = os.path.join(os.path.dirname(__file__), "images", "ingredients")
    try:
        images = []
        if os.path.exists(images_dir):
            for file in os.listdir(images_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    images.append(f"http://localhost:8000/images/ingredients/{file}")
        
        fallback = "http://localhost:8000/images/No-image-available.png"
        return {"status": "success", "data": {"images": images, "fallback": fallback}}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# get user ingredients from database(user_ingredients table)
@app.get("/api/user-ingredients")
async def get_user_ingredients():
    db_path = os.path.join(os.path.dirname(__file__), "database", "recipes.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, quantity, image FROM user_ingredients")
        rows = cursor.fetchall()
        ingredients = [{"id": row[0], "name": row[1], "category": row[2], "quantity": row[3], "image": row[4], "selected": True} for row in rows]
        conn.close()
        return {"status": "success", "data": ingredients}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# add user ingredients to database(user_ingredients table)
@app.post("/api/user-ingredients")
async def add_user_ingredient(ingredient: UserIngredientCreate):
    db_path = os.path.join(os.path.dirname(__file__), "database", "recipes.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user_ingredients (name, category, quantity, image) VALUES (?, ?, ?, ?)", 
                       (ingredient.name, ingredient.category, ingredient.quantity, ingredient.image))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return {"status": "success", "data": {"id": new_id, "name": ingredient.name, "category": ingredient.category, "quantity": ingredient.quantity, "image": ingredient.image, "selected": True}}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# delete user ingredients from database(user_ingredients table)
@app.delete("/api/user-ingredients/{ingredient_id}")
async def delete_user_ingredient(ingredient_id: int):
    db_path = os.path.join(os.path.dirname(__file__), "database", "recipes.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_ingredients WHERE id = ?", (ingredient_id,))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class GenerateRecipeTextRequest(BaseModel):
    recipe: Dict[str, Any]
    ingredients: List[Any]
    preferences: Dict[str, str]

# generate recipe text from base recipe and user ingredients
@app.post("/api/generate-recipe-text")
async def generate_recipe_text(request: GenerateRecipeTextRequest):
    try:
        user_prefs = request.preferences
        # Extract ingredient names (and quantity if available) if they are dicts
        ingredients_list_for_llm = [f"{ing.get('name', ing)} ({ing.get('quantity', 'N/A')})" if isinstance(ing, dict) else ing for ing in request.ingredients]
        # สกัดเฉพาะชื่อวัตถุดิบเพื่อเอาไปใช้ validate
        ingredients_name_only = [ing.get('name', ing).lower() if isinstance(ing, dict) else ing.lower() for ing in request.ingredients]
        
        base_recipe = request.recipe
        
        print(f"\n[1] Text Request | Prefs: {user_prefs}")
        print(f"[2] Text Ingredients: {ingredients_list_for_llm}")
        print(f"[3] Base Recipe: {base_recipe.get('name', 'Unknown')}")

        max_retries = 3
        attempt = 0
        final_output = None
        
        while attempt < max_retries:
            attempt += 1
            print(f"Generation Attempt: {attempt}/{max_retries}")
            
            recipe = call_agentic_llm(ingredients_list_for_llm, user_prefs, base_recipe)
            
            if "error" in recipe:
                final_output = recipe
                break
                
            result = validate_recipe(recipe, ingredients_name_only, user_prefs)
            
            if result["status"] == "fail":
                print(f"Recipe rejected: {result['reason']}")
            else:
                print("Recipe approved")
                final_output = recipe
                break
                
        if not final_output:
             return {"status": "error", "message": "Failed to generate a valid recipe after multiple attempts due to validation failures."}
        elif "error" in final_output:
             return {"status": "error", "message": final_output["error"]}

        print(f"[4] Final Output: {final_output}");
        
        return {
            "status": "success",
            "data": final_output
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import sqlite3
import os
import uuid
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List, Dict, Any

from fridge_repository import insert_user_ingredient, list_user_ingredients
from recipe_contracts import ingredient_names, validate_generated_recipe_shape

#
#       uvicorn main:app --reload
# 

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
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

ALLERGEN_MAP = {
    "shrimp":    {"triggers": ["shrimp", "prawn", "กุ้ง"],
                  "blocks":   ["shrimp", "prawn", "กุ้ง"]},
    "peanut":    {"triggers": ["peanut", "peanuts", "ถั่วลิสง", "ถั่ว"],
                  "blocks":   ["peanut", "peanuts", "ถั่วลิสง", "เนยถั่ว"]},
    "milk":      {"triggers": ["milk", "dairy", "cream", "butter", "cheese", "นม", "เนย", "ครีม"],
                  "blocks":   ["milk", "dairy", "cream", "butter", "cheese", "นม", "เนย", "ครีม"]},
    "egg":       {"triggers": ["egg", "eggs", "ไข่"],
                  "blocks":   ["egg", "eggs", "ไข่"]},
    "gluten":    {"triggers": ["wheat", "flour", "gluten", "แป้งสาลี", "แป้ง"],
                  "blocks":   ["wheat", "flour", "gluten", "แป้งสาลี", "แป้ง"]},
    "shellfish": {"triggers": ["crab", "lobster", "clam", "oyster", "ปู", "หอย", "กั้ง"],
                  "blocks":   ["crab", "lobster", "clam", "oyster", "ปู", "หอย", "กั้ง"]},
    "fish":      {"triggers": ["fish", "ปลา"],
                  "blocks":   ["fish", "ปลา"]},
    "soy":       {"triggers": ["soy", "ถั่วเหลือง", "เต้าหู้", "ถั่ว"],
                  "blocks":   ["soy sauce", "soy", "tofu", "เต้าหู้", "ถั่วเหลือง", "ซีอิ๊ว", "ซอสถั่วเหลือง"]},
    "nut":       {"triggers": ["almond", "cashew", "walnut", "hazelnut", "อัลมอนด์", "มะม่วงหิมพานต์"],
                  "blocks":   ["almond", "cashew", "walnut", "hazelnut", "อัลมอนด์", "มะม่วงหิมพานต์"]},
}
ALLERGY_TRIGGER_KEYWORDS = ["allergic to", "allergy", "แพ้", "ห้ามใส่", "ไม่ทาน"]

# -------------------------------
# 1. Ingredient Check (No hallucination)
# -------------------------------
def check_ingredients(recipe, user_ingredients):
    for item in recipe["adjusted_ingredients"]:
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
    safety_warning = recipe.get("safety_warning", "")
    if not isinstance(safety_warning, str):
        safety_warning = ""
    cooking_text = f"{instructions} {safety_warning.lower()}"

    prohibited_stock_conclusions = (
        "วัตถุดิบไม่พอ",
        "วัตถุดิบไม่เพียงพอ",
        "ต้องซื้อเพิ่ม",
        "ต้องซื้อวัตถุดิบเพิ่ม",
        "วัตถุดิบเพียงพอ",
        "มีวัตถุดิบเพียงพอ",
        "not enough ingredients",
        "insufficient ingredients",
        "have enough ingredients",
        "enough ingredients",
        "ingredients are sufficient",
        "need to buy more",
        "needs to buy more",
        "must buy more",
        "have to buy more",
        "buy more ingredients",
    )
    if any(claim in cooking_text for claim in prohibited_stock_conclusions):
        return False, "Prohibited stock conclusion"

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
    valid, reason = validate_generated_recipe_shape(recipe)
    if not valid:
        return False, reason

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
    
    # ดึงเฉพาะ field 'allergy' จาก preferences
    allergy_str = ""
    if isinstance(user_prefs, dict):
        allergy_str = user_prefs.get("allergy", "").lower().strip()
    else:
        allergy_str = str(user_prefs).lower()

    # ถ้าไม่มีการระบุการแพ้อาหาร ผ่านทันที
    if not allergy_str or allergy_str in ("", "none", "ไม่มี", "ไม่แพ้อาหาร", "no allergy"):
        return True, "OK"

    # ตรวจว่ามีคำที่บ่งบอกการแพ้ไหม
    has_allergy_mention = any(kw in allergy_str for kw in ALLERGY_TRIGGER_KEYWORDS)
    if not has_allergy_mention:
        return True, "OK"

    # ตรวจสอบด้วย triggers/blocks แยกกัน
    for allergen_key, mapping in ALLERGEN_MAP.items():
        # ใช้ triggers เพื่อ detect ว่า user แพ้กลุ่มนี้ไหม
        user_is_allergic = any(trigger in allergy_str for trigger in mapping["triggers"])
        if user_is_allergic:
            # ใช้ blocks เพื่อตรวจว่ามีวัตถุดิบต้องห้ามใน recipe ไหม
            for block_term in mapping["blocks"]:
                if block_term in ingredients_text:
                    return False, f"Allergy violation: พบ '{block_term}' ในสูตร (ผู้ใช้แพ้ {allergen_key})"

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
    valid, msg = validate_generated_recipe_shape(recipe)
    if not valid:
        return {
            "status": "fail",
            "reason": msg
        }

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
def call_agentic_llm(ingredients, user_prefs, base_recipe, feedback=None):
    print("Agentic LLM (Gemini) is thinking and calculating...")

    if not client:
        return {"error": "API Key is missing. Please check your .env file."}

    try:
        feedback_section = ""
        if feedback:
            feedback_section = f"""
        ผลตรวจสอบจากรอบก่อนหน้า (MUST FIX): สูตรที่คุณสร้างในรอบก่อนไม่ผ่านการตรวจสอบ เนื่องจาก: "{feedback}"
        กรุณาแก้ไขปัญหานี้โดยเฉพาะในรอบนี้ โดยยังคงรักษาส่วนอื่นที่ถูกต้องไว้เหมือนเดิม
        """

        prompt = f"""
        คุณคือ Executive Chef และนักโภชนาการคลินิกที่มีประสบการณ์สูง
        หน้าที่ของคุณคือการนำ "สูตรอาหารตั้งต้น" มาดัดแปลงให้เข้ากับ "วัตถุดิบที่ผู้ใช้มี" และ "เงื่อนไขโภชนาการ"
        โดยต้องคำนึงถึงความปลอดภัยทางอาหาร (Food Safety) และหลักการทำอาหารที่ถูกต้องเป็นอันดับหนึ่ง

        ข้อมูลของคุณมีดังนี้:
        1. วัตถุดิบที่ผู้ใช้มี : {ingredients}
        2. เงื่อนไขและข้อควรระวังของผู้ใช้: {user_prefs}
        3. สูตรอาหารตั้งต้น (อ้างอิงโภชนาการจากสูตรนี้): {base_recipe}
        รายการวัตถุดิบนี้บอกเฉพาะชนิดที่ผู้ใช้ระบุว่ามี ไม่ได้ระบุปริมาณคงเหลือจริง
        ห้ามสรุปว่าวัตถุดิบเพียงพอ ไม่เพียงพอ หรือต้องซื้อเพิ่มจากรายการนี้
        servings คือจำนวนที่เสิร์ฟของสูตรนี้
        ปริมาณใน adjusted_ingredients ต้องเป็นปริมาณรวมสำหรับทั้งสูตร ซึ่งครอบคลุมจำนวนที่เสิร์ฟตาม servings
        ค่า calories, protein_g, carbs_g และ fat_g ใน nutrition ต้องเป็นค่าต่อ 1 ที่เสิร์ฟ
        หากประมาณค่าโภชนาการเป็นค่ารวมทั้งสูตร ต้องหารด้วย servings ก่อนตอบ
        {feedback_section}
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
            "servings": 2,
            "adjusted_ingredients": ["วัตถุดิบ 1 (พร้อมระบุปริมาณที่ถูกต้อง IN THAI)", "วัตถุดิบ 2 (IN THAI)"],
            "diet_tags": ["tag1 (MUST BE IN ENGLISH)", "tag2 (MUST BE IN ENGLISH)"],
            "nutrition": {{
                "basis": "per_serving",
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

# search online ingredient images via Pexels
@app.get("/api/ingredient-images/search")
async def search_ingredient_images(q: str):
    if not PEXELS_API_KEY:
        return {"status": "error", "message": "PEXELS_API_KEY not configured"}
    if not q.strip():
        return {"status": "success", "data": {"images": []}}
    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": q, "per_page": 12},
            timeout=10,
        )
        response.raise_for_status()
        photos = response.json().get("photos", [])
        images = [photo["src"]["medium"] for photo in photos]
        return {"status": "success", "data": {"images": images}}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# upload/capture a custom ingredient image, saved to images/ingredients
@app.post("/api/ingredient-images/upload")
async def upload_ingredient_image(file: UploadFile = File(...)):
    images_dir = os.path.join(os.path.dirname(__file__), "images", "ingredients")
    allowed_ext = {".png", ".jpg", ".jpeg", ".webp"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_ext:
        return {"status": "error", "message": f"Unsupported file type: {ext or 'unknown'}"}
    try:
        os.makedirs(images_dir, exist_ok=True)
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(images_dir, filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        url = f"http://localhost:8000/images/ingredients/{filename}"
        return {"status": "success", "data": {"image": url}}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# get user ingredients from database(user_ingredients table)
@app.get("/api/user-ingredients")
async def get_user_ingredients():
    db_path = os.path.join(os.path.dirname(__file__), "database", "recipes.db")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        ingredients = list_user_ingredients(conn)
        return {"status": "success", "data": ingredients}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn is not None:
            conn.close()

# add user ingredients to database(user_ingredients table)
@app.post("/api/user-ingredients")
async def add_user_ingredient(ingredient: UserIngredientCreate):
    db_path = os.path.join(os.path.dirname(__file__), "database", "recipes.db")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        created = insert_user_ingredient(
            conn,
            name=ingredient.name,
            category=ingredient.category,
            image=ingredient.image,
        )
        return {"status": "success", "data": created}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn is not None:
            conn.close()

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
        ingredients_list_for_llm = ingredient_names(request.ingredients)
        ingredients_name_only = [name.lower() for name in ingredients_list_for_llm]
        
        base_recipe = request.recipe
        
        print(f"\n[1] Text Request | Prefs: {user_prefs}")
        print(f"[2] Text Ingredients: {ingredients_list_for_llm}")
        print(f"[3] Base Recipe: {base_recipe.get('name', 'Unknown')}")

        max_retries = 3
        attempt = 0
        final_output = None
        feedback = None

        while attempt < max_retries:
            attempt += 1
            print(f"Generation Attempt: {attempt}/{max_retries}")

            recipe = call_agentic_llm(ingredients_list_for_llm, user_prefs, base_recipe, feedback=feedback)

            if isinstance(recipe, dict) and "error" in recipe:
                final_output = recipe
                break

            result = validate_recipe(recipe, ingredients_name_only, user_prefs)

            if result["status"] == "fail":
                feedback = result["reason"]
                print(f"Recipe rejected: {feedback}")
            else:
                print("Recipe approved")
                final_output = recipe
                break
                
        if not final_output:
             return {"status": "error", "message": "Failed to generate a valid recipe after multiple attempts due to validation failures."}
        elif isinstance(final_output, dict) and "error" in final_output:
             return {"status": "error", "message": final_output["error"]}

        # Pretty JSON Output
        print(f"[4] Final Output: {json.dumps(final_output, ensure_ascii=False, indent=2)}")
        
        return {
            "status": "success",
            "data": final_output
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

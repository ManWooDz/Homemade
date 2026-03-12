from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import sqlite3
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from model.yolo_services import detect_ingredients_from_image
from pydantic import BaseModel
from typing import List, Dict, Any

#
#       uvicorn main:app --reload
# 

# โหลด API Key จากไฟล์ .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# ตั้งค่า Gemini API
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

# Serves local images directory
app.mount("/images", StaticFiles(directory="images"), name="images")

# ==========================================
# 🔍 ฟังก์ชัน RAG: Match Scoring (ค้นหาสูตร)
# ==========================================
def retrieve_base_recipe(detected_ingredients, user_prefs):
    """
    รับ Array วัตถุดิบจาก YOLO ไปค้นหาสูตรใน SQLite ที่ตรงกันมากที่สุด
    """
    db_path = os.path.join(os.path.dirname(__file__), "database", "recipes.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # ดึงสูตรอาหารทั้งหมดออกมาจาก Database
        cursor.execute("SELECT * FROM base_recipes")
        rows = cursor.fetchall()
        
        best_recipe = None
        highest_score = -1
        
        # ทำ Match Scoring ด้วยการนับจำนวนจุดตัด (Intersection)
        detected_set = set([item.lower() for item in detected_ingredients])
        
        for row in rows:
            recipe_id = row[0]
            recipe_name = row[1]
            recipe_short_description = row[2]
            recipe_ratings = row[3]
            recipe_review = row[4]
            recipe_image = row[5]
            recipe_tags = json.loads(row[6])
            recipe_ingredients = json.loads(row[7])
            recipe_nutrition = json.loads(row[8])
            recipe_instructions = json.loads(row[9])
            
            recipe_set = set([item.lower() for item in recipe_ingredients])
            
            # คำนวณคะแนน: เจอวัตถุดิบตรงกันกี่ชิ้น?
            match_score = len(detected_set.intersection(recipe_set))
            
            # (Option เสริม) ถ้าผู้ใช้มีเงื่อนไข เช่น Diet: Keto แล้วสูตรนี้เป็น Keto ให้คะแนนบวกเพิ่ม!
            diet_pref = user_prefs.get("diet", "")
            if diet_pref and diet_pref in recipe_tags:
                match_score += 1 
                
            # เก็บสูตรที่คะแนนสูงสุดไว้
            if match_score > highest_score:
                highest_score = match_score
                best_recipe = {
                    "id": recipe_id,
                    "recipe_name": recipe_name,
                    "short_description": recipe_short_description,
                    "ratings": recipe_ratings,
                    "review": recipe_review,
                    "image": recipe_image,
                    "base_ingredients": recipe_ingredients,
                    "base_nutrition": recipe_nutrition,
                    "diet_tags": recipe_tags,
                    "instructions": recipe_instructions,
                    "match_score": match_score
                }
                
        conn.close()
        
        # ถ้าคะแนนเป็น 0 (หาของไม่ตรงกับเมนูไหนเลย) ส่งค่า Default กลับไป
        if highest_score == 0:
            return {"error": "ไม่พบสูตรอาหารที่ตรงกับวัตถุดิบนี้ในระบบ กรุณาลองรูปอื่น"}
            
        return best_recipe
        
    except Exception as e:
        return {"error": f"Database Error: {str(e)}"}

# ==========================================
# 🧠 ฟังก์ชัน AI (รอเชื่อมต่อ Gemini สัปดาห์หน้า)
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
        
        # ยิง API ด้วย Syntax แบบใหม่
        response = client.models.generate_content(
            # model='gemini-2.5-flash-lite',
            model='gemini-3.1-flash-lite-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        
        # แปลงข้อความ JSON ที่ได้มา
        result_json = json.loads(response.text)
        return result_json

    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return {
            "error": "ไม่สามารถสร้างสูตรอาหารได้ในขณะนี้",
            "details": str(e)
        }

# ==========================================
# 🚀 API Endpoint (ช่องทางรับส่งข้อมูล)
# ==========================================
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

            recipes.append({
                "id": row[0],
                "name": row[1],
                "short_description": row[2],
                "ratings": row[3],
                "review": row[4],
                "image": row[5],
                "tags": json.loads(row[6]),
                "ingredients": mapped_ingredients,
                "nutrition": json.loads(row[8]),
                "instructions": json.loads(row[9])
            })
        conn.close()
        return {"status": "success", "data": recipes}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/generate-recipe")
async def generate_recipe(
    image: UploadFile = File(...), 
    preferences: str = Form("{}") 
):
    try:
        image_bytes = await image.read()
        user_prefs = json.loads(preferences)
        print(f"\n📥 [1] Received Request | Prefs: {user_prefs}")

        # สเตป 2: ให้ YOLO ดูรูป
        detected_ingredients = detect_ingredients_from_image(image_bytes)
        print(f"👀 [2] YOLO Detected: {detected_ingredients}")

        # สเตป 3: ให้ RAG ค้นหาสูตร
        base_recipe = retrieve_base_recipe(detected_ingredients, user_prefs)
        
        if "error" in base_recipe:
            return {"status": "error", "message": base_recipe["error"]}
            
        print(f"🔍 [3] RAG Found Match: {base_recipe['recipe_name']} (Score: {base_recipe['match_score']})")

        # สเตป 4: ส่งให้ LLM (ตอนนี้เป็น Mock)
        final_output = call_agentic_llm(detected_ingredients, user_prefs, base_recipe)

        return {
            "status": "success",
            "data": final_output
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

class GenerateRecipeTextRequest(BaseModel):
    recipe: Dict[str, Any]
    ingredients: List[Any]
    preferences: Dict[str, str]

@app.post("/api/generate-recipe-text")
async def generate_recipe_text(request: GenerateRecipeTextRequest):
    try:
        user_prefs = request.preferences
        # Extract just the ingredient names if they are dicts
        ingredients_list = [ing.get("name", ing) if isinstance(ing, dict) else ing for ing in request.ingredients]
        base_recipe = request.recipe
        
        print(f"\n📥 [1] Text Request | Prefs: {user_prefs}")
        print(f"👀 [2] Text Ingredients: {ingredients_list}")
        print(f"🔍 [3] Base Recipe: {base_recipe.get('name', 'Unknown')}")

        final_output = call_agentic_llm(ingredients_list, user_prefs, base_recipe)

        return {
            "status": "success",
            "data": final_output
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
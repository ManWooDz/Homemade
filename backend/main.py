from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import sqlite3
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from model.yolo_services import detect_ingredients_from_image

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
    print("⚠️ Warning: ไม่พบ GEMINI_API_KEY ในไฟล์ .env")
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
        คุณคือเชฟและนักโภชนาการอัจฉริยะ 
        หน้าที่ของคุณคือการนำ "สูตรอาหารตั้งต้น" มาดัดแปลงให้เข้ากับ "วัตถุดิบที่ผู้ใช้มี" และ "เงื่อนไขโภชนาการ"
        
        ข้อมูลของคุณมีดังนี้:
        1. วัตถุดิบที่ผู้ใช้มี (จาก AI Vision): {ingredients}
        2. เงื่อนไขของผู้ใช้: {user_prefs}
        3. สูตรอาหารตั้งต้น (อ้างอิงโภชนาการจากสูตรนี้): {base_recipe}
        
        คำสั่ง:
        - ให้ดัดแปลงสูตรอาหารตั้งต้น โดยใช้วัตถุดิบที่ผู้ใช้มีให้มากที่สุด (อะไรไม่มี ให้หาของทดแทนหรือตัดออกอย่างสมเหตุสมผล)
        - ปรับปรุงขั้นตอนการทำอาหารให้สอดคล้องกับวัตถุดิบใหม่
        - คำนวณโภชนาการใหม่ (Calories, Protein, Carbs, Fat) โดยอิงจากฐานข้อมูลเดิมและบวกลบตามวัตถุดิบที่เปลี่ยนไป
        - ตอบกลับมาเป็นรูปแบบ JSON เท่านั้น ห้ามมีข้อความอื่นปนเด็ดขาด โดยใช้โครงสร้างดังนี้:
        
        {{
            "recipe_name": "ชื่อเมนูที่ดัดแปลงแล้ว",
            "adjusted_ingredients": ["รายการวัตถุดิบ 1", "รายการวัตถุดิบ 2"],
            "diet_tags": ["tag1", "tag2"],
            "nutrition": {{
                "calories": ตัวเลข,
                "protein_g": ตัวเลข,
                "carbs_g": ตัวเลข,
                "fat_g": ตัวเลข
            }},
            "instructions": ["1. ขั้นตอนแรก", "2. ขั้นตอนต่อไป"]
        }}
        """
        
        # ยิง API ด้วย Syntax แบบใหม่
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
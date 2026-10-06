from datetime import date, datetime, timedelta, timezone
from contextlib import asynccontextmanager
import logging
import math

logging.basicConfig(level=logging.INFO)

from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response, UploadFile, File, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from sqlalchemy import update
from sqlalchemy.orm import Session
import uvicorn
import json
import os
import re
import sys
import uuid
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Annotated, List, Dict, Any, Optional, Literal

from auth import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    hash_token,
    revoke_refresh_token,
    rotate_refresh_token,
    set_auth_cookies,
    verify_password,
)
from csrf import verify_same_origin
from database.db import get_db, SessionLocal
from database.models import BaseRecipe, RecipeIngredientImage, RefreshToken, User, UserPreference
from nutrition.calculator import compute_recipe_nutrition
from nutrition.llm_fallback import NutritionLLMEstimator
from email_sender import send_otp_email, validate_email_config
import otp
from fridge_repository import delete_user_ingredient, insert_user_ingredient, list_user_ingredients
from recipe_contracts import ingredient_names, validate_generated_recipe_shape
from image_urls import public_image_url
from history_repository import (
    get_history_embedding_snapshot,
    insert_generate_history,
    list_history,
    set_favorite,
    set_history_embedding_if_missing,
    upsert_rating,
)
from base_favorites_repository import list_base_favorite_ids, set_base_favorite
from embeddings import build_history_document, build_request_query, embed_history_documents, embed_request_queries
from personalization.context import PersonalizationContext, build_personalization_context
from personalization.repository import count_embedded_signals


def _harden_stdio(streams):
    # On Windows, stdout/stderr are cp874/cp1252 when piped or redirected, so any
    # print() of a character outside that codepage (KG reason arrows, emoji in
    # user prefs or LLM output) raises UnicodeEncodeError, and the endpoint's
    # outer except turns a good request into {"status":"error"}. Degrade to
    # backslash escapes once, at startup, instead of guarding every print.
    # Streams without .reconfigure (test runners swap in StringIO) are left alone.
    for stream in streams:
        try:
            stream.reconfigure(errors="backslashreplace")
        except Exception:
            pass


_harden_stdio([sys.stdout, sys.stderr])

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

@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_email_config()
    yield


app = FastAPI(title="Homemade Recipe API", lifespan=lifespan)

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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # FastAPI's default handler for this exception echoes the rejected
    # value back in each error's "input" field, then serializes the whole
    # error list with json.dumps(..., allow_nan=False) -- if the rejected
    # value is itself NaN/Infinity (e.g. a float field with
    # allow_inf_nan=False, sent a literal NaN/Infinity JSON token), that
    # serialization step raises ValueError and the request 500s instead of
    # returning the clean 422 the validation logic already decided on.
    # Verified directly against a real server, not assumed: a raw NaN body
    # produces exactly this crash without this handler.
    #
    # Must recurse: "input" isn't always the bare rejected scalar. A
    # missing-field error's "input" is the whole parent dict, and a nested
    # model's (e.g. NutritionData) failing field carries the whole nested
    # dict — either can contain a NaN/Infinity buried inside, not just at
    # the top level. A body missing "name" alongside a NaN quantity_amount,
    # or a NutritionData.calories of NaN, both reach this path with the
    # bad float nested inside "input", not equal to it.
    def sanitize(value):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return str(value)
        if isinstance(value, dict):
            return {k: sanitize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [sanitize(v) for v in value]
        return value

    errors = []
    for error in exc.errors():
        error = dict(error)
        if "input" in error:
            error["input"] = sanitize(error["input"])
        errors.append(error)
    # jsonable_encoder for everything else, matching FastAPI's own default
    # handler exactly (dates, enums, etc.) -- only the non-finite-float
    # "input" case needed a special case above.
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


BASIC_INGREDIENTS = ["salt", "pepper", "oil", "soy sauce", "fish sauce", "sugar", "water"]

BAD_FLAVOR_PAIRS = [
    ("milk", "fish sauce"),
    ("chocolate", "garlic"),
]

from allergen_kg.floor import ALLERGEN_LABELS, ALLERGEN_MAP, ALLERGY_TRIGGER_KEYWORDS, detect_flagged_allergens
from allergen_kg.match import find_allergy_violation, format_violation_reason
from allergen_kg.resolve import resolve_allergy_blocks, unavailable_blocks

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
def _legacy_check_allergy(recipe, user_prefs):
    ingredients_text = " ".join(recipe["adjusted_ingredients"]).lower()
    for allergen_key in detect_flagged_allergens(user_prefs):
        for block_term in ALLERGEN_MAP[allergen_key]["blocks"]:
            if block_term in ingredients_text:
                return False, f"Allergy violation: พบ '{block_term}' ในสูตร (ผู้ใช้แพ้ {allergen_key})"
    return True, "OK"


def check_allergy(recipe, user_prefs, resolved_blocks=None):
    # resolved_blocks=None is the legacy path for callers not yet passing
    # resolved blocks; the endpoint always passes a dict (see resolve_blocks_for_request).
    if resolved_blocks is None:
        return _legacy_check_allergy(recipe, user_prefs)
    violation = find_allergy_violation(recipe, user_prefs, resolved_blocks)
    if violation is None:
        return True, "OK"
    return False, format_violation_reason(violation)


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
def validate_recipe(recipe, user_ingredients, user_prefs, resolved_blocks=None):
    valid, msg = validate_generated_recipe_shape(recipe)
    if not valid:
        return {
            "status": "fail",
            "reason": msg
        }

    # check_allergy runs right after check_ingredients, ahead of the
    # quality checks (flavor/logic/nutrition) -- this pipeline is
    # fail-fast (stops at the first failing stage), so a safety check
    # must not be ordered behind a quality check: otherwise a recipe
    # that fails an earlier quality check never has its allergy content
    # evaluated at all, silently hiding a real violation. Found via the
    # local-LLM-generator benchmark (2026-09-20), see spec.md.
    checks = [
        check_ingredients,
        check_allergy,
        check_flavor,
        check_logic,
        check_nutrition,
        check_core
    ]

    # Map each check to how it should be called
    single_arg_checks = {check_flavor, check_logic, check_nutrition}

    for check in checks:
        if check in single_arg_checks:
            valid, msg = check(recipe)
        elif check == check_allergy:
            valid, msg = check(recipe, user_prefs, resolved_blocks)
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
_PERSONALIZATION_CONTEXT_KEY = "__personalization_context"


def call_agentic_llm(ingredients, user_prefs, base_recipe, feedback=None):
    print("Agentic LLM (Gemini) is thinking and calculating...")

    if not client:
        return {"error": "API Key is missing. Please check your .env file."}

    try:
        personalization_block = None
        prompt_prefs = user_prefs
        if isinstance(user_prefs, dict) and _PERSONALIZATION_CONTEXT_KEY in user_prefs:
            personalization_block = user_prefs[_PERSONALIZATION_CONTEXT_KEY]
            prompt_prefs = {
                key: value
                for key, value in user_prefs.items()
                if key != _PERSONALIZATION_CONTEXT_KEY
            }

        feedback_section = ""
        if feedback:
            feedback_section = f"""
        ผลตรวจสอบจากรอบก่อนหน้า (MUST FIX): สูตรที่คุณสร้างในรอบก่อนไม่ผ่านการตรวจสอบ เนื่องจาก: "{feedback}"
        กรุณาแก้ไขปัญหานี้โดยเฉพาะในรอบนี้ โดยยังคงรักษาส่วนอื่นที่ถูกต้องไว้เหมือนเดิม
        """

        prompt_additions = feedback_section
        if personalization_block:
            prompt_additions = f"{personalization_block}\n{feedback_section}"

        prompt = f"""
        คุณคือ Executive Chef และนักโภชนาการคลินิกที่มีประสบการณ์สูง
        หน้าที่ของคุณคือการนำ "สูตรอาหารตั้งต้น" มาดัดแปลงให้เข้ากับ "วัตถุดิบที่ผู้ใช้มี" และ "เงื่อนไขโภชนาการ"
        โดยต้องคำนึงถึงความปลอดภัยทางอาหาร (Food Safety) และหลักการทำอาหารที่ถูกต้องเป็นอันดับหนึ่ง

        ข้อมูลของคุณมีดังนี้:
        1. วัตถุดิบที่ผู้ใช้มี : {ingredients}
        2. เงื่อนไขและข้อควรระวังของผู้ใช้: {prompt_prefs}
        3. สูตรอาหารตั้งต้น (อ้างอิงโภชนาการจากสูตรนี้): {base_recipe}
        รายการวัตถุดิบนี้บอกเฉพาะชนิดที่ผู้ใช้ระบุว่ามี ไม่ได้ระบุปริมาณคงเหลือจริง
        ห้ามสรุปว่าวัตถุดิบเพียงพอ ไม่เพียงพอ หรือต้องซื้อเพิ่มจากรายการนี้
        servings คือจำนวนที่เสิร์ฟของสูตรนี้
        ปริมาณใน adjusted_ingredients ต้องเป็นปริมาณรวมสำหรับทั้งสูตร ซึ่งครอบคลุมจำนวนที่เสิร์ฟตาม servings
        ค่า calories, protein_g, carbs_g และ fat_g ใน nutrition ต้องเป็นค่าต่อ 1 ที่เสิร์ฟ
        หากประมาณค่าโภชนาการเป็นค่ารวมทั้งสูตร ต้องหารด้วย servings ก่อนตอบ
        {prompt_additions}
        กฎเหล็กด้านความปลอดภัยและคุณภาพ (MUST FOLLOW STRICTLY):
        1. ความปลอดภัยอาหาร (Food Safety): ห้ามแนะนำให้รับประทานเนื้อสัตว์ดิบ (ยกเว้นวัตถุดิบที่ระบุว่าทานดิบได้) ต้องระบุการทำเนื้อสัตว์ ไก่ หมู หรืออาหารทะเลให้สุกอย่างชัดเจน และห้ามมีขั้นตอนที่เสี่ยงต่อการปนเปื้อนข้าม (Cross-contamination)
        2. ข้อควรระวังการแพ้ (Allergy Risks): ต้องตรวจสอบและปฏิบัติตาม {prompt_prefs} อย่างเคร่งครัด หากมีการแพ้อาหาร ห้ามใส่วัตถุดิบนั้นและวัตถุดิบแฝงเด็ดขาด
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
        print(f"Gemini API Error: {type(e).__name__}")
        return {
            "error": "ไม่สามารถสร้างสูตรอาหารได้ในขณะนี้",
            "details": str(e)
        }

# ==========================================
#  API Endpoint (ช่องทางรับส่งข้อมูล)
# ==========================================

# get recipes from database (PostgreSQL: base_recipes + recipe_ingredient_images)
@app.get("/api/recipes")
async def get_all_recipes(db: Session = Depends(get_db)):
    try:
        ingredient_map = {row.name: row.image for row in db.query(RecipeIngredientImage).all()}

        recipes = []
        for recipe in db.query(BaseRecipe).order_by(BaseRecipe.id).all():
            mapped_ingredients = []
            for ing in recipe.ingredients:
                img_path = ingredient_map.get(ing.lower().strip())
                img_url = f"http://localhost:8000/{img_path}" if img_path else "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=150"
                mapped_ingredients.append({
                    "name": ing,
                    "image": img_url
                })

            image_val = public_image_url(recipe.image)

            recipes.append({
                "id": recipe.id,
                "name": recipe.name,
                "short_description": recipe.short_description,
                "ratings": recipe.ratings,
                "review": recipe.review,
                "image": image_val,
                "tags": recipe.tags,
                "ingredients": mapped_ingredients,
                "nutrition": recipe.nutrition,
                "instructions": recipe.instructions,
            })
        return {"status": "success", "data": recipes}
    except Exception as e:
        return {"status": "error", "message": str(e)}



class NutritionData(BaseModel):
    # System boundary (client-writable via POST /api/user-ingredients), not
    # just a UI-read-only display value — reject unknown fields, coerce
    # nothing implicitly. allow_inf_nan=False (model-level, applies to every
    # float field here) closes the same NaN/Infinity boundary gap fixed on
    # quantity_amount -- a literal NaN in calories/protein_g/etc. would
    # otherwise pass field validation and only surface later as a nested
    # NaN inside a DIFFERENT error's "input" (see the global
    # RequestValidationError handler's docstring for why that matters).
    model_config = {"extra": "forbid", "allow_inf_nan": False}
    basis: Literal["per_100g_or_ml"]
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None


QuantityUnit = Literal[
    "ชิ้น", "กรัม", "กก.", "มล.", "ลิตร", "ขวด", "ถุง", "แพ็ค", "ฟอง", "หัว", "ลูก", "ห่อ",
]


class UserIngredientCreate(BaseModel):
    name: str
    category: str = "Other"
    image: str = "http://localhost:8000/images/No-image-available.png"
    expiry_date: Optional[date] = None
    nutrition_data: Optional[NutritionData] = None
    # Real, user-entered quantity — distinct from the legacy `quantity`
    # string column, left untouched/unused. amount is a client-writable
    # system boundary: reject non-positive/NaN/Infinity/absurd values here,
    # not just in the frontend's number input, since a stored NaN would
    # break JSON serialization on every future GET for this user.
    quantity_amount: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False, le=100000)
    quantity_unit: Optional[QuantityUnit] = None

    @model_validator(mode="after")
    def _quantity_unit_requires_amount(self):
        if self.quantity_unit is not None and self.quantity_amount is None:
            raise ValueError("quantity_unit requires quantity_amount")
        return self

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

BARCODE_CODE_PATTERN = re.compile(r"^\d{8,14}$")

CATEGORY_KEYWORD_MAP = {
    "Meat & poultry": ["meat", "poultry", "meats", "fish", "seafood"],
    "Vegetables": ["vegetable", "vegetables"],
    "Fruits": ["fruit", "fruits"],
}

def _map_off_category(categories_tags):
    tags = " ".join(categories_tags or []).lower()
    for category, keywords in CATEGORY_KEYWORD_MAP.items():
        if any(keyword in tags for keyword in keywords):
            return category
    return "Other"


def _off_float(nutriments, key):
    value = nutriments.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _map_off_nutrition(nutriments):
    """Raw per-100g/100ml nutrition from Open Food Facts, kept separate from
    (never fed into) the nutrition engine's own computed/estimated nutrition.
    Real OFF data is often partial — a missing individual macro stays None
    rather than dropping the whole record."""
    if not nutriments:
        return None
    calories = _off_float(nutriments, "energy-kcal_100g")
    if calories is None:
        # Some products only carry energy in kJ, not kcal directly.
        energy_kj = _off_float(nutriments, "energy-kj_100g") or _off_float(nutriments, "energy_100g")
        if energy_kj is not None:
            calories = round(energy_kj / 4.184, 1)
    if calories is None:
        return None
    return {
        "basis": "per_100g_or_ml",
        "calories": calories,
        "protein_g": _off_float(nutriments, "proteins_100g"),
        "carbs_g": _off_float(nutriments, "carbohydrates_100g"),
        "fat_g": _off_float(nutriments, "fat_100g"),
    }

# lookup ingredient info from Open Food Facts by barcode
@app.get("/api/barcode-lookup")
def barcode_lookup(code: str, current_user: User = Depends(get_current_user)):
    if not BARCODE_CODE_PATTERN.match(code):
        return {"status": "error", "message": "Invalid barcode format"}
    try:
        response = requests.get(
            f"https://world.openfoodfacts.org/api/v2/product/{code}.json",
            params={
                "fields": "product_name_th,product_name,generic_name,brands,image_front_url,categories_tags,nutriments"
            },
            headers={"User-Agent": "Homemade-Capstone/1.0 (student capstone project)"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != 1:
            return {"status": "error", "message": "Product not found"}
        product = payload.get("product", {})
        name = (
            product.get("product_name_th")
            or product.get("product_name")
            or product.get("generic_name")
            or product.get("brands")
        )
        if not name:
            return {"status": "error", "message": "Product not found"}
        category = _map_off_category(product.get("categories_tags"))
        image = product.get("image_front_url") or ""
        nutrition_data = _map_off_nutrition(product.get("nutriments"))
        return {
            "status": "success",
            "data": {
                "name": name,
                "category": category,
                "image": image,
                "nutrition_data": nutrition_data,
            },
        }
    except requests.RequestException as e:
        return {"status": "error", "message": f"Could not reach Open Food Facts: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# get user ingredients from database (PostgreSQL: user_ingredients table)
@app.get("/api/user-ingredients")
async def get_user_ingredients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ingredients = list_user_ingredients(db, current_user.id)
        return {"status": "success", "data": ingredients}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# add user ingredients to database (PostgreSQL: user_ingredients table)
@app.post("/api/user-ingredients", dependencies=[Depends(verify_same_origin)])
async def add_user_ingredient(
    ingredient: UserIngredientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        created = insert_user_ingredient(
            db,
            user_id=current_user.id,
            name=ingredient.name,
            category=ingredient.category,
            image=ingredient.image,
            expiry_date=ingredient.expiry_date,
            nutrition_data=ingredient.nutrition_data.model_dump() if ingredient.nutrition_data else None,
            quantity_amount=ingredient.quantity_amount,
            quantity_unit=ingredient.quantity_unit,
        )
        return {"status": "success", "data": created}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# delete user ingredients from database (PostgreSQL: user_ingredients table)
@app.delete("/api/user-ingredients/{ingredient_id}", dependencies=[Depends(verify_same_origin)])
async def remove_user_ingredient(
    ingredient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        deleted = delete_user_ingredient(db, user_id=current_user.id, ingredient_id=ingredient_id)
        if not deleted:
            return {"status": "error", "message": "Ingredient not found"}
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


RatingTag = Literal["Delicious", "Great", "Tasty", "Not Bad", "Meh"]


class RatingRequest(BaseModel):
    model_config = {"extra": "forbid"}
    stars: int = Field(ge=1, le=5, strict=True)
    tag: Optional[RatingTag] = None
    feedback: Optional[str] = Field(default=None, max_length=240)

    @field_validator("feedback")
    @classmethod
    def _blank_feedback_is_null(cls, value):
        if value is None or not value.strip():
            return None
        return value


@app.get("/api/history")
async def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"status": "success", "data": list_history(db, current_user.id)}


# Postgres binds ids as INTEGER: anything above 2**31-1 would raise DataError
# (a 500) if it reached the DB, so out-of-range ids are rejected as 422 here.
PositiveInt32Id = Annotated[int, Path(ge=1, le=2_147_483_647)]


async def embed_rated_history_best_effort(db, *, user_id, history_id, rating) -> None:
    """Embed a signal after its rating commits, without holding a remote-work transaction."""
    if os.getenv("PERSONALIZATION_ENABLED", "1") == "0" or rating["stars"] not in (1, 2, 4, 5):
        return

    stage = "history_snapshot"
    try:
        snapshot = get_history_embedding_snapshot(db, user_id=user_id, history_id=history_id)
        stage = "history_snapshot_close"
        db.close()
        if snapshot is None or snapshot.embedding is not None:
            return

        stage = "history_embedding"
        document = build_history_document(
            snapshot.recipe_name, snapshot.adjusted_ingredients, snapshot.diet_tags
        )
        embedding = (await run_in_threadpool(embed_history_documents, [document]))[0]
        stage = "history_embedding_update"
        # Session.close() releases the refresh/read transaction; reusing the
        # session here opens a new transaction only for the conditional update.
        set_history_embedding_if_missing(
            db, user_id=user_id, history_id=history_id, embedding=embedding
        )
    except Exception as error:
        try:
            db.rollback()
        except Exception:
            pass
        logging.getLogger("personalization").warning(
            "[personalization] stage=%s user_id=%s history_id=%s error=%s",
            stage, user_id, history_id, type(error).__name__,
        )
    finally:
        try:
            db.close()
        except Exception:
            pass


@app.put("/api/history/{history_id}/rating", dependencies=[Depends(verify_same_origin)])
async def put_history_rating(
    history_id: PositiveInt32Id,
    body: RatingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user.id
    saved = upsert_rating(
        db,
        user_id=user_id,
        history_id=history_id,
        stars=body.stars,
        tag=body.tag,
        feedback=body.feedback,
    )
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History not found")
    await embed_rated_history_best_effort(
        db, user_id=user_id, history_id=history_id, rating=saved
    )
    return {"status": "success", "data": saved}


def _set_history_favorite(db, user, history_id, favorite):
    if not set_favorite(db, user_id=user.id, history_id=history_id, favorite=favorite):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History not found")
    return {"status": "success", "data": {"is_favorite": favorite}}


@app.put("/api/history/{history_id}/favorite", dependencies=[Depends(verify_same_origin)])
async def put_history_favorite(
    history_id: PositiveInt32Id,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _set_history_favorite(db, current_user, history_id, True)


@app.delete("/api/history/{history_id}/favorite", dependencies=[Depends(verify_same_origin)])
async def delete_history_favorite(
    history_id: PositiveInt32Id,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _set_history_favorite(db, current_user, history_id, False)


@app.get("/api/base-favorites")
async def get_base_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"status": "success", "data": list_base_favorite_ids(db, current_user.id)}


def _set_base_favorite(db, user, recipe_id, favorite):
    if not set_base_favorite(db, user_id=user.id, base_recipe_id=recipe_id, favorite=favorite):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return {"status": "success", "data": {"is_favorite": favorite}}


@app.put("/api/base-favorites/{recipe_id}", dependencies=[Depends(verify_same_origin)])
async def put_base_favorite(
    recipe_id: PositiveInt32Id,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _set_base_favorite(db, current_user, recipe_id, True)


@app.delete("/api/base-favorites/{recipe_id}", dependencies=[Depends(verify_same_origin)])
async def delete_base_favorite(
    recipe_id: PositiveInt32Id,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _set_base_favorite(db, current_user, recipe_id, False)


def resolve_blocks_for_request(user_prefs):
    # Resolved once per request, before the retry loop: prefs never change
    # between attempts, and no DB session is held open across LLM calls.
    if not detect_flagged_allergens(user_prefs):
        return {}
    if SessionLocal is None:
        return unavailable_blocks(user_prefs)
    try:
        db = SessionLocal()
        try:
            return resolve_allergy_blocks(db, user_prefs)
        finally:
            db.close()
    except Exception:
        logging.getLogger("allergen_kg").exception("[allergen_kg] could not open a session -- floor only")
        return unavailable_blocks(user_prefs)


def _print_safe(message):
    # Windows consoles on legacy codepages (cp874/cp1252) cannot encode the
    # KG chain arrow in violation reasons; a log line must never crash the
    # request, so degrade to backslash escapes instead of raising.
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(message.encode(encoding, errors="backslashreplace").decode(encoding))


def save_generate_history(db, user, request, final_output):
    # A recipe that already passed validation must never be lost because the
    # history write failed — swallow, roll back, log safely, return None.
    try:
        return insert_generate_history(
            db, user_id=user.id, request_recipe=request.recipe, final_output=final_output
        )
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        _print_safe(f"[History] could not save generate history: {e!r}")
        return None


# The checker (allergen_kg/match.py) scans ONLY recipe["adjusted_ingredients"]; steps and
# safety_warning are never checked, so the wording must not forbid the words there.
_LLM_FORBIDDEN_KEY = ("ห้ามมีในรายการวัตถุดิบ adjusted_ingredients "
                      "(ระบบตรวจอัตโนมัติจะปฏิเสธสูตรที่รายการวัตถุดิบมีคำเหล่านี้ "
                      "แม้อยู่ในหมายเหตุหรือคำปฏิเสธ เช่น 'ไม่มี...' ภายในบรรทัดวัตถุดิบ)")
_LLM_FORBIDDEN_SUFFIX = (" — ห้ามพิมพ์คำเหล่านี้ในบรรทัดใดๆ ของ adjusted_ingredients "
                         "ให้ตัดวัตถุดิบนั้นออกหรือใช้ทางเลือกที่ชื่อไม่มีคำเหล่านี้ "
                         "ส่วน safety_warning และขั้นตอนการทำ (instructions) "
                         "ยังกล่าวถึงเรื่องอาการแพ้ได้ตามปกติ")


def build_llm_prefs(user_prefs, resolved_blocks):
    """Prefs as shown to the generator: user_prefs plus the exact terms the checker rejects.

    The validator rejects any recipe containing a resolved block term, even inside a
    note or a negation ("ไม่มีกุ้ง"). Telling the model the terms up front avoids
    burning retries on them. Returns user_prefs itself when nothing is resolved;
    otherwise a NEW dict (user_prefs is never mutated; validation keeps using it).
    Pure: no DB access.
    """
    if not resolved_blocks or not isinstance(user_prefs, dict):
        return user_prefs
    terms = sorted({term for resolved in resolved_blocks.values() for term in resolved.terms})
    return {**user_prefs, _LLM_FORBIDDEN_KEY: ", ".join(terms) + _LLM_FORBIDDEN_SUFFIX}


async def get_personalization_for_request(
    db,
    user_id,
    *,
    recipe_name,
    ingredient_names,
    taste,
    user_prefs,
    resolved_blocks,
) -> PersonalizationContext | None:
    """Build request-scoped context without holding a transaction over remote work."""
    if os.getenv("PERSONALIZATION_ENABLED", "1") == "0":
        return None

    try:
        signal_count = count_embedded_signals(db, user_id)
    except Exception as error:
        try:
            db.rollback()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass
        logging.getLogger("personalization").warning(
            "[personalization] stage=count user_id=%s error=%s",
            user_id,
            type(error).__name__,
        )
        return None

    try:
        db.close()
    except Exception as error:
        try:
            db.rollback()
        except Exception:
            pass
        logging.getLogger("personalization").warning(
            "[personalization] stage=count_close user_id=%s error=%s",
            user_id,
            type(error).__name__,
        )
        return None
    if signal_count < 3:
        return None

    try:
        query = build_request_query(recipe_name, ingredient_names, taste)
        query_embedding = (await run_in_threadpool(embed_request_queries, [query]))[0]
    except Exception as error:
        logging.getLogger("personalization").warning(
            "[personalization] stage=query_embedding user_id=%s error=%s",
            user_id,
            type(error).__name__,
        )
        return None

    try:
        return build_personalization_context(
            db,
            user_id,
            query_embedding=query_embedding,
            user_prefs=user_prefs,
            resolved_blocks=resolved_blocks,
        )
    except Exception as error:
        try:
            db.rollback()
        except Exception:
            pass
        logging.getLogger("personalization").warning(
            "[personalization] stage=context user_id=%s error=%s",
            user_id,
            type(error).__name__,
        )
        return None
    finally:
        try:
            db.close()
        except Exception:
            pass


def build_allergy_exhaustion_message(ingredient_names, user_prefs, resolved_blocks):
    """Thai message for a retry loop that ran out on an allergy violation."""
    violating = []
    for name in dict.fromkeys(ingredient_names):  # de-duplicate, keep order
        violation = find_allergy_violation({"adjusted_ingredients": [name]}, user_prefs, resolved_blocks)
        if violation is None:
            continue
        path = violation.path
        # path[-1] is the ingredient node that directly implies the allergen. Graph
        # node names can be English (e.g. "oyster"); the user-facing cause must be
        # Thai only, so those fall back to the allergen label.
        if path and len(path) >= 2 and re.search(r"[A-Za-z]", path[-1]) is None:
            cause = f"มี{path[-1]}"
        else:
            cause = f"ตรงกับที่แพ้: {ALLERGEN_LABELS[violation.allergen_key]}"
        violating.append(f"{name} ({cause})")
    if violating:
        return (f"ไม่สามารถสร้างสูตรได้ เพราะมีวัตถุดิบที่ขัดกับอาการแพ้ของคุณ: {', '.join(violating)} "
                "กรุณาลองเอาออกแล้วสร้างใหม่")
    return ("ไม่สามารถสร้างสูตรได้ เพราะหาสูตรที่ปลอดภัยกับอาการแพ้ของคุณไม่เจอ "
            "กรุณาลองเปลี่ยนวัตถุดิบแล้วสร้างใหม่")


def run_generation_with_validation(generate_fn, ingredients, ingredients_name_only, user_prefs,
                                   base_recipe, resolved_blocks, max_retries=3, llm_prefs=None):
    # llm_prefs is what the generator sees (defaults to user_prefs); validation
    # always uses user_prefs.
    if llm_prefs is None:
        llm_prefs = user_prefs
    attempts_log = []
    feedback = None
    for attempt in range(1, max_retries + 1):
        print(f"Generation Attempt: {attempt}/{max_retries}")
        recipe = generate_fn(ingredients, llm_prefs, base_recipe, feedback=feedback)

        if isinstance(recipe, dict) and "error" in recipe:
            attempts_log.append({"attempt": attempt, "status": "error", "reason": recipe["error"]})
            return recipe, attempts_log

        result = validate_recipe(recipe, ingredients_name_only, user_prefs, resolved_blocks=resolved_blocks)
        if result["status"] == "fail":
            feedback = result["reason"]
            attempts_log.append({"attempt": attempt, "status": "fail", "reason": feedback})
            _print_safe(f"Recipe rejected: {feedback}")
        else:
            attempts_log.append({"attempt": attempt, "status": "pass", "reason": None})
            print("Recipe approved")
            return recipe, attempts_log
    return None, attempts_log


class GenerateRecipeTextRequest(BaseModel):
    recipe: Dict[str, Any]
    ingredients: List[Any]
    preferences: Dict[str, str]

# generate recipe text from base recipe and user ingredients
@app.post("/api/generate-recipe-text", dependencies=[Depends(verify_same_origin)])
async def generate_recipe_text(
    request: GenerateRecipeTextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # get_current_user's lookup began a transaction on this Session; end it now
    # so no connection sits idle-in-transaction across the LLM calls. The
    # Session is reused later by the history write (a fresh transaction).
    db.close()
    try:
        user_prefs = request.preferences
        if isinstance(user_prefs, dict) and _PERSONALIZATION_CONTEXT_KEY in user_prefs:
            user_prefs = {
                key: value
                for key, value in user_prefs.items()
                if key != _PERSONALIZATION_CONTEXT_KEY
            }
        ingredients_list_for_llm = ingredient_names(request.ingredients)
        ingredients_name_only = [name.lower() for name in ingredients_list_for_llm]
        
        base_recipe = request.recipe
        
        print(f"\n[1] Text Request | Prefs: {user_prefs}")
        print(f"[2] Text Ingredients: {ingredients_list_for_llm}")
        print(f"[3] Base Recipe: {base_recipe.get('name', 'Unknown')}")

        resolved_blocks = resolve_blocks_for_request(user_prefs)
        personalization = await get_personalization_for_request(
            db,
            current_user.id,
            recipe_name=base_recipe.get("name", ""),
            ingredient_names=ingredients_list_for_llm,
            taste=user_prefs.get("taste", ""),
            user_prefs=user_prefs,
            resolved_blocks=resolved_blocks,
        )
        llm_prefs = build_llm_prefs(user_prefs, resolved_blocks)
        if personalization is not None:
            llm_prefs = {
                **llm_prefs,
                _PERSONALIZATION_CONTEXT_KEY: personalization.prompt_block,
            }
        final_output, attempts_log = run_generation_with_validation(
            call_agentic_llm,
            ingredients_list_for_llm,
            ingredients_name_only,
            user_prefs,
            base_recipe,
            resolved_blocks,
            llm_prefs=llm_prefs,
        )

        if not final_output:
             last_reason = (attempts_log[-1].get("reason") or "") if attempts_log else ""
             if last_reason.startswith("Allergy violation:"):
                 return {"status": "error", "message": build_allergy_exhaustion_message(
                     ingredients_list_for_llm, user_prefs, resolved_blocks)}
             return {"status": "error", "message": "ไม่สามารถสร้างสูตรที่ผ่านการตรวจสอบได้ กรุณาลองใหม่อีกครั้งหรือเปลี่ยนวัตถุดิบ"}
        elif isinstance(final_output, dict) and "error" in final_output:
             return {"status": "error", "message": final_output["error"]}

        # (rev 3) final_output may be a caller-owned object in some code
        # paths -- copy before mutating so this never corrupts shared state.
        final_output = dict(final_output)

        # Nutrition Engine: runs exactly once, on the already-approved
        # recipe -- never inside the retry loop above. Its own try/except
        # is separate from this function's outer one, so an engine bug
        # falls back to the LLM's own guess instead of discarding a
        # recipe that already passed validation.
        llm_estimated_nutrition = final_output.get("nutrition")
        try:
            # Named nutrition_db so it never shadows the request-scoped `db`
            # parameter that save_generate_history uses below.
            nutrition_db = SessionLocal()
            try:
                nutrition_result = compute_recipe_nutrition(
                    db=nutrition_db,
                    adjusted_ingredients=final_output.get("adjusted_ingredients", []),
                    instructions=final_output.get("instructions", []),
                    servings=final_output.get("servings", 1),
                    llm_estimator=NutritionLLMEstimator(),
                )
            finally:
                nutrition_db.close()

            final_output["llm_estimated_nutrition"] = llm_estimated_nutrition
            final_output["computed_nutrition"] = nutrition_result.nutrition
            if nutrition_result.partially_estimated:
                # `nutrition` keeps the LLM's original guess -- do not
                # overwrite it with a partially-estimated computed value
                # (design spec: "never let a partially-estimated number pass
                # as fully grounded"). The computed value is still exposed
                # separately as `computed_nutrition`.
                final_output["nutrition_partially_estimated"] = True
                print(f"[Nutrition Engine] partially estimated: {nutrition_result.partially_estimated_reasons}")
            else:
                # Sanity bound on the COMPUTED result -- log and flag only,
                # never retried (a computation bug is not the LLM's mistake
                # to fix, see design spec). A failed bound means the value
                # is not trustworthy as grounded, so it is treated exactly
                # like the partially-estimated branch above: flag it, and
                # leave `nutrition` as the LLM's guess.
                computed_calories = nutrition_result.nutrition.get("calories", 0)
                if computed_calories < 0 or computed_calories > 3000:
                    print(f"[Nutrition Engine] sanity check failed on computed result: {nutrition_result.nutrition}")
                    final_output["nutrition_partially_estimated"] = True
                else:
                    final_output["nutrition"] = nutrition_result.nutrition
                    final_output["nutrition_partially_estimated"] = False
        except Exception as e:
            print(f"[Nutrition Engine] failed, keeping LLM's original guess: {e}")
            final_output["llm_estimated_nutrition"] = llm_estimated_nutrition
            final_output["nutrition_partially_estimated"] = True

        print("[4] Recipe generation completed")

        history_id = save_generate_history(db, current_user, request, final_output)

        personalization_metadata = {
            "applied": personalization is not None,
            "positives": personalization.positives if personalization is not None else 0,
            "negatives": personalization.negatives if personalization is not None else 0,
        }

        return {
            "status": "success",
            "data": {
                **final_output,
                "history_id": history_id,
                "personalization": personalization_metadata,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

class RegisterRequest(BaseModel):
    email: str
    password: str


# register a new user — email/password stored with a bcrypt hash
@app.post(
    "/api/auth/register",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_same_origin)],
)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Invalid email")
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    if db.query(User).filter_by(email=email).first() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=email, hashed_password=hash_password(request.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "success", "data": {"id": user.id, "email": user.email}}


class ForgotPasswordRequest(BaseModel):
    email: str


_GENERIC_FORGOT_PASSWORD_RESPONSE = {
    "status": "success",
    "message": "If that email exists, a code has been sent.",
}


@app.post("/api/auth/forgot-password", dependencies=[Depends(verify_same_origin)])
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    user = db.query(User).filter_by(email=email).first()
    if user is None:
        return _GENERIC_FORGOT_PASSWORD_RESPONSE

    try:
        # Serialize requests for one account without making duplicates wait
        # behind the SMTP-held transaction. PostgreSQL raises immediately;
        # the generic response keeps the account-existence signal unchanged.
        # ponytail: this holds one user-row lock during SMTP; use a durable
        # delivery reservation/worker only if OTP throughput grows.
        db.query(User).filter_by(id=user.id).with_for_update(nowait=True).one()
        if otp.get_recent_otp_request(db, user.id, otp.RESEND_COOLDOWN_SECONDS) is not None:
            db.rollback()
            return _GENERIC_FORGOT_PASSWORD_RESPONSE
        _row, code = otp.create_otp_for_user(db, user.id)
    except Exception as exc:
        db.rollback()
        logging.error(
            "forgot-password: OTP prepare failed for user_id=%s error_type=%s",
            user.id,
            type(exc).__name__,
        )
        return _GENERIC_FORGOT_PASSWORD_RESPONSE

    try:
        await run_in_threadpool(send_otp_email, email, code)
    except Exception as exc:
        db.rollback()
        logging.error(
            "forgot-password: OTP delivery unconfirmed for user_id=%s error_type=%s",
            user.id,
            type(exc).__name__,
        )
        return _GENERIC_FORGOT_PASSWORD_RESPONSE

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logging.error(
            "forgot-password: OTP commit failed for user_id=%s error_type=%s",
            user.id,
            type(exc).__name__,
        )
        return _GENERIC_FORGOT_PASSWORD_RESPONSE
    return _GENERIC_FORGOT_PASSWORD_RESPONSE


class VerifyOtpRequest(BaseModel):
    email: str
    code: str


def _generic_verify_otp_error() -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"status": "error", "message": "Invalid or expired code"},
    )


@app.post("/api/auth/verify-otp", dependencies=[Depends(verify_same_origin)])
async def verify_otp(request: VerifyOtpRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    user = db.query(User).filter_by(email=email).first()
    if user is None:
        return _generic_verify_otp_error()

    ticket = otp.attempt_verify_otp(db, user.id, request.code)
    if ticket is None:
        return _generic_verify_otp_error()

    return {"status": "success", "data": {"reset_ticket": ticket}}


class ResetPasswordRequest(BaseModel):
    reset_ticket: str
    new_password: str


@app.post("/api/auth/reset-password", dependencies=[Depends(verify_same_origin)])
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    # NOTE: JSONResponse with {"status": "error", ...}, not raise HTTPException —
    # same generic-error response shape convention verify_otp uses above, so
    # error bodies stay consistent across the password-reset flow.
    if len(request.new_password) < 8:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Password must be at least 8 characters"},
        )

    user_id = otp.consume_reset_ticket(db, request.reset_ticket)
    if user_id is None:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Invalid or expired reset link"},
        )

    # otp.consume_reset_ticket deliberately does not commit (it only flushes
    # its UPDATE, or rolls back and returns None on failure) — the ticket
    # consumption, password update, and refresh-token revocation below must
    # all commit together in one transaction so a failure partway through
    # never leaves a burned ticket with the old password still active, or a
    # changed password with old sessions still valid.
    user = db.get(User, user_id)
    user.hashed_password = hash_password(request.new_password)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()
    return {"status": "success"}


# login — OAuth2 password flow (form fields: username, password); username holds the email
@app.post("/api/auth/login", dependencies=[Depends(verify_same_origin)])
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    email = form_data.username.strip().lower()
    user = db.query(User).filter_by(email=email).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()
    set_auth_cookies(response, access_token, refresh_token)
    response.headers["Cache-Control"] = "no-store"
    return {"status": "success", "data": {"id": user.id, "email": user.email}}


@app.post("/api/auth/refresh", dependencies=[Depends(verify_same_origin)])
async def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_refresh = request.cookies.get("refresh_token")
    result = rotate_refresh_token(db, raw_refresh) if raw_refresh else None
    if result is None:
        # NOTE: must return a fresh JSONResponse here, not raise HTTPException.
        # FastAPI only merges the injected `response` parameter's headers into
        # the final response when the handler returns normally — when it raises,
        # Starlette's exception middleware builds a brand-new response and any
        # Set-Cookie headers already set on `response` (e.g. by clear_auth_cookies)
        # are silently discarded. Constructing+returning the response ourselves
        # is the only way the cleared cookies actually reach the client.
        error_response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or expired refresh token"},
        )
        clear_auth_cookies(error_response)
        error_response.headers["Cache-Control"] = "no-store"
        return error_response

    new_access, new_refresh = result
    set_auth_cookies(response, new_access, new_refresh)
    response.headers["Cache-Control"] = "no-store"
    return {"status": "success"}


@app.post("/api/auth/logout", dependencies=[Depends(verify_same_origin)])
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_refresh = request.cookies.get("refresh_token")
    if raw_refresh:
        try:
            revoke_refresh_token(db, raw_refresh)
        except Exception:
            logging.exception("logout: failed to revoke refresh token")
            db.rollback()
            # Same reason as /refresh's 401 path above: raising HTTPException
            # here would discard clear_auth_cookies' Set-Cookie headers because
            # Starlette builds a fresh response for raised exceptions instead of
            # merging headers already set on the injected `response` object.
            error_response = JSONResponse(
                status_code=500,
                content={"detail": "Logout failed, please try again"},
            )
            clear_auth_cookies(error_response)
            error_response.headers["Cache-Control"] = "no-store"
            return error_response
    clear_auth_cookies(response)
    response.headers["Cache-Control"] = "no-store"
    return {"status": "success"}


# current authenticated user, resolved from the access-token cookie
@app.get("/api/auth/me")
async def read_current_user(response: Response, current_user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return {"status": "success", "data": {"id": current_user.id, "email": current_user.email}}


class UserPreferenceUpdate(BaseModel):
    age: int | None = None
    cuisine_preferences: list[str] = []
    dietary_restrictions: list[str] = []
    equipment: list[str] = []
    cooking_frequency: str | None = None
    cooking_goals: list[str] = []


def _serialize_preferences(pref: UserPreference) -> dict:
    return {
        "age": pref.age,
        "cuisine_preferences": pref.cuisine_preferences,
        "dietary_restrictions": pref.dietary_restrictions,
        "equipment": pref.equipment,
        "cooking_frequency": pref.cooking_frequency,
        "cooking_goals": pref.cooking_goals,
    }


# real per-user preferences (onboarding quiz + Profile edits) — real auth
# from the start, no dev-bridge, since nothing pre-existing depends on it
@app.get("/api/user-preferences")
async def get_user_preferences(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    pref = db.get(UserPreference, current_user.id)
    return {"status": "success", "data": _serialize_preferences(pref) if pref else None}


@app.put("/api/user-preferences", dependencies=[Depends(verify_same_origin)])
async def put_user_preferences(
    request: UserPreferenceUpdate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.age is not None and not (1 <= request.age <= 120):
        raise HTTPException(status_code=400, detail="age must be between 1 and 120")

    pref = db.get(UserPreference, current_user.id)
    if pref is None:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)
    pref.age = request.age
    pref.cuisine_preferences = request.cuisine_preferences
    pref.dietary_restrictions = request.dietary_restrictions
    pref.equipment = request.equipment
    pref.cooking_frequency = request.cooking_frequency
    pref.cooking_goals = request.cooking_goals
    db.commit()
    db.refresh(pref)
    response.headers["Cache-Control"] = "no-store"
    return {"status": "success", "data": _serialize_preferences(pref)}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

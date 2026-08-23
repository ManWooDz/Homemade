# Homemade — สร้างสูตรอาหารไทยจากวัตถุดิบในตู้เย็น ที่ grounded และตรวจสอบได้

Capstone โปรเจกต์ ทีม 2 คน กำลังเตรียมสอบหัวข้อ (ปีการศึกษา 2569) รายละเอียดเชิงวิชาการเต็มดูที่ [docs/project-proposal.md](docs/project-proposal.md)

## Architecture

**Stack ปัจจุบัน (โค้ดจริงใน repo):**
- Backend: FastAPI (Python) + SQLite (`backend/main.py`) — SQL แบบ raw ผ่าน `sqlite3.connect()` ไม่มี ORM
- Frontend: React + Vite + Tailwind CSS v4 (`frontend/src/pages/*`)
- AI: Gemini API (`gemini-3.1-flash-lite-preview`) เรียกตรงใน `call_agentic_llm()`
- มี 6-stage validation pipeline อยู่แล้ว (`validate_recipe()`): ingredient check, flavor check, logic check, nutrition check (bound เดียว 0-1500 cal ไม่มี DB อ้างอิง), allergy check (keyword matching ผ่าน `ALLERGEN_MAP`), core-ingredient check
- มีไฟล์ `backend/model/yolo11n_food.pt` อยู่ในโปรเจกต์แต่**ไม่ได้ใช้งานแล้ว** (ทีมตัดสินใจไม่เอา YOLO แล้ว — อย่าเสนอกลับมา)

**Stack เป้าหมาย (กำลังจะสร้าง):**
- Backend DB: ย้าย SQLite → **PostgreSQL** (พร้อม SQLAlchemy แนะนำ เพราะตอนนี้ raw SQL string จะรกเมื่อมี user_id ผูกหลายตาราง)
- Auth: JWT ทำเอง (`passlib[bcrypt]` + `python-jose`/`PyJWT` + FastAPI `OAuth2PasswordBearer`/`OAuth2PasswordRequestForm`) — **ไม่ใช่** fastapi-users, **ไม่ใช่** Auth.js/BetterAuth (เป็น Node-only ใช้กับ FastAPI ไม่ได้)
- ตั้ง `hashed_password` เป็น nullable ไว้เผื่ออนาคตอยากเพิ่ม Google OAuth (เพิ่มได้แบบ additive ไม่ต้องรื้อ ไม่ต้องทำตอนนี้)
- External API: Open Food Facts (barcode lookup, fallback พิมพ์เองถ้าไม่เจอ — coverage ของสดตลาดไทยอ่อน)

**System Architecture diagram:** ทำใน Eraser.io (นอก repo) — ดูส่วน Current State ด้านล่างสำหรับจุดที่ต้องแก้

## Done

- Frontend หน้าใช้งานหลักครบ: AddIngredient, CreateRecipe, UserIngredients, RecipeDetail, CustomCookingPage, CookingPage (มี flow ทั้งเลือก base menu และ generate อิสระ)
- Backend 6-stage validation pipeline (ดูด้านบน) — เป็นฐานที่ core contribution ใหม่จะต่อยอด ไม่ใช่สร้างใหม่หมด
- `docs/project-proposal.md` — เอกสารข้อเสนอโครงงานฉบับเต็ม (ที่มาปัญหา, objectives, scope, architecture, features, feasibility, success criteria, Gantt ~12 เดือน [ต้องบีบเหลือ ~9 เดือนจริง — ยังไม่ได้แก้], การแบ่งงาน 2 คน)
- Competitive analysis: Paprika, Cooklang, Deglaze, Umami, Spillt, ReciMe, SuperCook, AI Chatbot ทั่วไป — สรุปว่า gap ของตลาดคือ "generative + บริบทไทย + grounded/ตรวจสอบได้พร้อมกัน" ไม่มีเจ้าไหนทำครบ

## Todo / Out of scope

**Contribution หลัก (แคบ ลึก ต้องมี evaluation — อย่าขยายเพิ่มอีก):**
1. Nutrition Engine: Thai quantity parsing → unit normalization → lookup ฐานข้อมูล INMU (สถาบันโภชนาการ ม.มหิดล — **ยังไม่ยืนยันว่าเข้าถึงข้อมูลได้จริง**, fallback USDA FoodData Central) → (ถ้าเวลาพอ) retention/yield factor ตามวิธีปรุง
2. Allergen Validation 2-layer: rule-based keyword (ต่อยอด `ALLERGEN_MAP` เดิม) → Knowledge Graph (transitive, เช่น กะปิ→กุ้ง) → LLM hidden-allergen layer — ลำดับนี้อยู่ *ภายใน* step 5 ของ 6-step check เดิม ไม่ใช่ stage แยกต่างหาก
   - **ตัดสินใจแล้ว (2026-07): ทำเป็น Knowledge Graph จริง** ไม่ใช่ flat JSONB tag — ต้องมี node/edge/traversal จริงถึงจะ claim คำนี้ได้อย่างซื่อสัตย์ (ไม่งั้นเข้า trap เดียวกับที่เคยพลาดเรื่อง "RAG" มาก่อน)
   - Schema: table `allergen_edges` (ingredient_id, implies_allergen_or_ingredient_id) + recursive CTE query — **อยู่ใน PostgreSQL ตัวเดิม ไม่ต้องสลับไป Neo4j/graph DB เฉพาะทาง** (ปรึกษาอาจารย์มาว่าต้องเปลี่ยน DB แต่จริงๆ ไม่จำเป็น — graph = data structure concept ไม่ผูกกับ storage engine, ใช้ edge-list + recursive query บน relational DB เป็น pattern มาตรฐาน)
   - **ข้อบังคับสำคัญ:** dataset ที่ curate ต้องมีเคส **2-hop ขึ้นไปจริง** (เช่น "น้ำพริกกะปิ/ลูกชิ้นกะปิ" → กะปิ → shrimp) ไม่ใช่แค่ 1-hop ทั้งหมด ถ้าทุก edge เป็น 1-hop เดียว ต่อให้ implement เป็น edge table ก็ยังเทียบเท่า flat array ในทางปฏิบัติ (ไม่มี inference จริงให้โชว์) — ต้องออกแบบ dataset ให้มี chain จริงเพื่อพิสูจน์ claim ตอนเดโม/สอบ
3. Agentic Critic-Feedback Loop: แก้ blind-retry ปัจจุบันให้ส่ง fail reason กลับเข้า prompt รอบถัดไป (โค้ดร่างอยู่ด้านล่าง Current State)

**Product envelope (ความเสี่ยงวิจัยต่ำ CRUD/API ปกติ — โชว์เดโมได้ ไม่ผูก KPI วิชาการ):**
- Barcode Scanner (Open Food Facts + fallback)
- Auth: Login/Profile, JWT
- Favorite, Rating (ดาว 1-5), Food Generate History ต่อ user
- Personalization: inject history/rating เป็น context ใน prompt ผ่าน **plain query ธรรมดา** (top-rated/recent history, ไม่ใช่ RAG) (**demonstrated only** — ไม่วัด "ดีขึ้นเมื่อใช้นาน" เพราะ cold-start)
  - ~~ตัดสินใจ 2026-07: ไม่ทำ RAG~~ **พลิกกลับ (2026-07): ทำ RAG จริง** ด้วย embedding + pgvector — ยังคง**ไม่นับเป็น complex component ตัวที่ 4** ของ contribution หลัก (nutrition/allergen-graph/critic-loop ยังคงเป็น 3 ตัวหลักที่มี evaluation) RAG นี้ยังอยู่ใต้ personalization ที่ **demonstrated only ไม่ผูก KPI** เหมือนเดิม แค่ implementation จริงเปลี่ยนจาก plain query เป็น embedding-based retrieval
  - **Embedding model ตัดสินใจแล้ว: Gemini Embedding** (`gemini-embedding-001`/Gemini Embedding 2 Preview) — **ไม่ใช้ Qwen** (text-embedding-v4) เหตุผล: (1) Gemini ยืนยันรองรับไทยชัดเจนใน official doc, Qwen แค่ "100+ languages" กว้างๆ ไม่ยืนยันไทย (2) free tier Gemini เป็น rate-limit ต่อเนื่องไม่มีวันหมดอายุ, Qwen free 1M token **หมดอายุใน 90 วัน** เสี่ยงหมดกลางโปรเจกต์ (3) provider เดียวกับ Gemini generation เดิม ไม่ต้องเปิด account/API key/SDK ใหม่ — ตัด tongyi-embedding-vision-plus/flash ทิ้ง (เป็น vision embedding ไม่เกี่ยวกับ text-only task นี้), qwen3-rerank ก็ไม่ใช้ (ผูกกับ Qwen ecosystem)
  - **ต้องทำก่อนใช้จริง:** ทดสอบ embed คู่ข้อความไทยที่ความหมายใกล้/ไกลกัน เช็คว่า similarity score แยกออกจริงไหม ก่อนเชื่อ (ยังไม่เคย verify Thai quality ของ Gemini Embedding โดยตรง แค่ confirm ว่า "รองรับ" ใน doc)
  - **Schema เพิ่ม:** `generate_history` เพิ่ม column `embedding VECTOR(768)` (ต้องเปิด `pgvector` extension ใน PostgreSQL), query ด้วย cosine similarity (`<=>` operator) เทียบ history ที่ rating สูง
  - **Legacy plain-query design (เก็บไว้อ้างอิง ไม่ใช่แผนที่ใช้แล้ว):**
    1. Tag-rating aggregate: `SELECT tag, COUNT(*), AVG(rating) FROM generate_history, unnest(diet_tags) AS tag WHERE user_id=X AND rating IS NOT NULL GROUP BY tag ORDER BY avg_rating DESC` → หา flavor/menu-type ที่ user ให้ rating สูง
    2. Ingredient×dish-category cross-tab: `SELECT ingredient, tag, COUNT(*) FROM generate_history, unnest(adjusted_ingredients) AS ingredient, unnest(diet_tags) AS tag WHERE user_id=X GROUP BY ingredient, tag HAVING COUNT(*) >= 3` → หา pattern "user มักใส่วัตถุดิบ X ในเมนูประเภท Y" — ใส่ `HAVING COUNT(*) >= 3` กัน noise จาก data น้อย (capstone timeframe มี record จำกัด ยิ่ง cross-tab ละเอียดยิ่งต้องการ data เยอะกว่าจะมีนัยสำคัญ)
    3. แปลงผล query เป็น text summary สั้นๆ ("มักชอบเมนูรสจัด ผัด/แกง, มักใส่ไข่ในเมนูผัด") → ฉีดเข้า prompt ตำแหน่งเดียวกับ "Preferences (+History)"
  - **ตัดออกจาก scope:** สัญญาณ "วัตถุดิบที่มักมีใน fridge เสมอ" — ต้องมี audit log การ add/remove วัตถุดิบข้ามเวลาซึ่งยังไม่ได้วางแผน (query fridge ปัจจุบันบอก pattern อดีตไม่ได้) เพิ่มทีหลังได้ถ้ามีเวลา ไม่ใช่ MVP
  - **คำที่ต้องใช้ตอนเขียนเล่ม/สอบ:** เรียก "rating-weighted aggregation heuristic" หรือ "rule-based taste profile summarizer" — **ห้ามเรียกว่า "AI เรียนรู้ preference"** เพราะไม่มี model train จริง เป็นแค่ SQL aggregation
- Expiry Tracking + ranking (**demonstrated only** — ไม่เคลม "ลด food waste X%")
- PostgreSQL migration + schema ใหม่ (users, ingredient_nutrition, generate_history, favorites, ratings, user_ingredients+expiry_date)

**Out of scope (ตัดสินใจแล้ว อย่าเสนอกลับมา):**
- YOLO ingredient recognition (ตัดออกแล้ว ใช้ Barcode แทน)
- Meal planning เต็มรูป/shopping list
- ฟีเจอร์โซเชียล (public feed, follow, comment — บทเรียนจาก Spillt)
- Mobile native app, OAuth ภายนอกจริงจัง (Google/Facebook login — เพิ่มทีหลังได้แบบ additive), production-scale deployment
- ทำอาหารจริงทุกสูตรเพื่อทดสอบ (ใช้ 3-layer verification: rule-based safety + retrieval similarity + expert-rated sample เล็กแทน)

## Current state

**AddIngredient image picker → online search + upload (2026-08-23) — product envelope, ไม่ใช่ contribution ที่ต้องมี evaluation:**
- เดิม `frontend/src/pages/AddIngredient.jsx` เลือกรูปจาก local library ที่ backend list ให้ (`GET /api/ingredient-images`); ตอนนี้เปลี่ยนเป็น **online image search** (Pexels) พิมพ์ค้นหา/auto-search ตามชื่อวัตถุดิบ debounce 400ms, ถ้า search fail หรือหา provider ไม่เจอมีปุ่ม **Upload or Take Photo** (`<input type="file" accept="image/*" capture="environment">`) เป็น fallback
- Backend เพิ่ม 2 endpoints ใหม่ใน `backend/main.py` (ขอ confirm แล้วก่อนแก้ตาม Hard Rule):
  - `GET /api/ingredient-images/search?q=<term>` — proxy เรียก Pexels Search API ด้วย `PEXELS_API_KEY` (server-side, ไม่ expose key ให้ frontend), คืน list URL รูป (`photo.src.medium`)
  - `POST /api/ingredient-images/upload` (multipart) — save ไฟล์ลง `backend/images/ingredients/` ด้วยชื่อสุ่ม (`uuid4().hex` + นามสกุลเดิม), คืน URL แบบเดียวกับรูป static เดิม
  - `requests` package เพิ่มใน `backend/requirements.txt` แต่ **ไม่ต้อง pip install ใหม่** เพราะติดมากับ `google-genai` dependency อยู่แล้ว (เช็คแล้วด้วย `python -c "import requests"` ผ่าน)
- `GET /api/ingredient-images` (list local library) ยังอยู่เหมือนเดิม — ตอนนี้ frontend ใช้แค่ดึง `fallback` URL (default "no image" placeholder) เท่านั้น ไม่ได้ใช้ full list แล้ว
- **ค้างอยู่:** `PEXELS_API_KEY` ยังไม่ได้ตั้งใน `backend/.env` — ผู้ใช้จะสมัคร/ใส่เองทีหลัง จนกว่าจะใส่ search endpoint จะคืน `{"status":"error","message":"PEXELS_API_KEY not configured"}` เสมอ (ทดสอบแล้วว่า error graceful ไม่ crash, frontend แสดงข้อความ error ชี้ไปปุ่ม upload แทน)
- Verify: `python -m py_compile backend/main.py` ผ่าน, `bun run build` (frontend) exit 0, ทดสอบ live: dev server (`--host 127.0.0.1 --port 5173 --strictPort`) HTTP 200, backend `uvicorn` local เรียก `/api/ingredient-images/search` เจอ error ตามคาด, เรียก `/api/ingredient-images/upload` ด้วยไฟล์ทดสอบ (`No-image-available.png`) สำเร็จ ได้ URL คืนมา และ URL นั้น serve ได้จริง (HTTP 200) — ลบไฟล์ทดสอบที่ upload ออกหลังตรวจแล้ว ไม่ทดสอบผ่าน browser UI จริง (ผู้ใช้ควรตรวจหน้า AddIngredient เองผ่าน dev server อีกที โดยเฉพาะหลังใส่ `PEXELS_API_KEY` แล้ว)
- ไฟล์ที่แก้: `backend/main.py`, `backend/requirements.txt`, `frontend/src/pages/AddIngredient.jsx`

**Profile page (frontend-only, 2026-08-18) — เข้าเงื่อนไข "product envelope" ไม่ใช่ contribution ที่ต้องมี evaluation:**
- ไฟล์ใหม่ `frontend/src/pages/Profile.jsx` ผูกกับ bottom-tab "me" ผ่าน `App.jsx` (`currentView === "profile"`); internal sub-view switching ในไฟล์เดียว (main/history/language/preferences/helps) ตาม pattern เดียวกับ `CreateRecipe.jsx`
- Username/email/avatar เป็น **hardcoded placeholder** — ยังไม่มี auth/user backend (เช็คแล้วว่า `/backend/` ไม่มี endpoint user/profile ใดๆ) ตรงตาม NO MAGIC ห้ามเดา infra
- Cooking History ดึงจาก `cookingHistory` state ใหม่ใน `App.jsx` — push เข้า array ทุกครั้งที่ `generate-recipe-text` สำเร็จ (ทั้งสอง flow: create-recipe และ custom-cooking) เก็บ **in-session เท่านั้น** รีเฟรชหน้าแล้วหาย เพราะยังไม่มี persistence/backend
- Language menu: เลือกได้ (ไทย/English) แต่เป็น **visual only ไม่มี i18n wiring จริง** (ยังไม่มี locale infra ในโปรเจกต์)
- Preferences menu: ใช้ pill-select pattern เดิมจาก `CreateRecipe.jsx` (รสชาติ/อาการแพ้อาหาร/อุปกรณ์ที่มี) เก็บเป็น local state ใน `Profile.jsx` เท่านั้น **ยังไม่ได้ผูกเป็นค่า default ให้ `CreateRecipe.jsx`** จริง (ไม่ได้อยู่ในขอบเขตที่ขอ ถ้าจะทำเป็นงานถัดไป)
- Logout button: แดง วางไว้ตาม UI spec แต่ยังเป็น **no-op** (`console.log` เฉยๆ) เพราะยังไม่มี auth/session backend ให้ logout จริง
- Verify: `npx eslint` ผ่าน (0 error/warning บนไฟล์ที่แก้), `npx vite build` exit 0 — **ไม่ได้ทำ visual browser verification** (playwright chromium cache version ไม่ตรงกับที่ npx ต้องการ ต้องโหลดใหม่ ผู้ใช้เลือก skip ไม่ดาวน์โหลด) ผู้ใช้ต้องตรวจ UI จริงเองผ่าน dev server
- ไฟล์ที่แก้: `frontend/src/App.jsx` (เพิ่ม `cookingHistory` state, route `"profile"`, tab handler `"me"`), ไฟล์ใหม่ `frontend/src/pages/Profile.jsx` — ไม่แตะ `/backend/`, ไม่ติดตั้ง package ใหม่

**Local development launcher (implemented and locally verified — 2026-07-14):**
- เป้าหมาย: ดับเบิลคลิก Windows Desktop shortcut ครั้งเดียวเพื่อเปิด FastAPI backend, Vite frontend และ `http://127.0.0.1:5173` ใน default browser โดยไม่ต้องเปิด VS Code/activate venv เอง
- launcher จะอยู่ที่ root ชื่อ `start-homemade.ps1` และต้องถูก `.gitignore` แบบเจาะจงเพื่อไม่ให้ push ขึ้น GitHub; Desktop shortcut อยู่นอก repo
- ใช้ `backend/venv/Scripts/python.exe -m uvicorn main:app --reload` และ `bun run dev -- --host 127.0.0.1 --port 5173 --strictPort`; ไม่ติดตั้ง package และไม่แก้ `/backend/`
- ต้องรอ HTTP response จากทั้ง FastAPI (`/docs`) และ frontend ก่อนเปิด browser, แสดง log แยกสอง terminal และตรวจ syntax/HTTP/shortcut/`git check-ignore` ก่อนถือว่าเสร็จ
- Design: [`docs/superpowers/specs/2026-07-14-local-dev-launcher-design.md`](docs/superpowers/specs/2026-07-14-local-dev-launcher-design.md)
- PowerShell AST parse: 0 errors
- git check-ignore: `/start-homemade.ps1` matched
- FastAPI `/docs`: HTTP 200
- Vite `/`: HTTP 200
- Desktop shortcut target/arguments/working directory: verified
- Final shortcut smoke test: browser opened frontend; dev terminals left running for user

**เสร็จแล้ว:** ข้อ 1 — `backend/main.py` แก้เป็น critic-feedback loop จริงแล้ว:
- `call_agentic_llm()` รับ `feedback=None` param เพิ่ม, ถ้ามีค่าจะฝังเป็น `feedback_section` ลงใน prompt บอก Gemini ว่ารอบก่อนพังเพราะอะไร ต้องแก้อะไรโดยเฉพาะ
- retry loop ใน `generate_recipe_text()` เก็บ `result["reason"]` จาก validation ที่ fail ไปเป็น `feedback` ป้อนรอบถัดไป (แทนที่จะ retry มั่วด้วย input เดิมทุกรอบ)
- verify แล้วด้วย `python -m py_compile main.py` → syntax OK (ยังไม่ได้ integration test จริงกับ Gemini API — ต้องรันเซิร์ฟเวอร์ทดสอบก่อนถือว่า verify ครบ)
- commit `0949f304` + push ขึ้น `origin/main` แล้ว (2026-07) — commit เฉพาะ `backend/main.py` เท่านั้น
- README.md อัปเดตเพิ่มบูลเล็ต "Adaptive Retry" ให้ตรงกับพฤติกรรมใหม่ → commit `a7371706` + push แล้วเช่นกัน
- `.gitignore` และ `backend/database/recipes.db` ยังค้าง modified อยู่ (ไม่เกี่ยวกับ fix นี้ ยังไม่ commit — ถามผู้ใช้ค้างไว้ว่าจะจัดการยังไง)

**Quantity/presence grounding slice (2026-07-14) — implement แล้วและตรวจสอบในเครื่องแล้ว:**
- My Fridge เป็น **presence-only**: active UI/API create/list ไม่รับ ไม่แสดง และไม่คืน `quantity`; payload สำหรับ generate ส่งวัตถุดิบเป็น `{id?, name}` และ backend ใช้เฉพาะชื่อ แม้ยังยอมรับ legacy string/object metadata เพื่อ compatibility (`quantity` ที่ติดมากับ legacy object จะถูก ignore)
- `servings` คือจำนวนที่เสิร์ฟ; ปริมาณใน `adjusted_ingredients` เป็นปริมาณรวมสำหรับสูตรทั้งสูตรที่ครอบคลุมจำนวนที่เสิร์ฟนั้น ส่วน `nutrition` (`calories`, `protein_g`, `carbs_g`, `fat_g`) เป็นค่าต่อ 1 ที่เสิร์ฟตาม `basis: "per_serving"` ไม่ใช่ stock คงเหลือใน My Fridge
- ไม่มี shortage/“ต้องซื้อเพิ่ม” claim หรือข้อสรุปว่า stock “เพียงพอ”, ไม่มีการเปรียบเทียบปริมาณคงเหลือ และไม่มี stock deduction หลังทำอาหาร เพราะระบบไม่ได้เก็บปริมาณที่ใช้จริง; validation stage 3 ปฏิเสธข้อสรุปเรื่อง stock ทั้งด้านไม่พอ/ต้องซื้อและด้านเพียงพอที่หลุดมาใน `instructions` หรือ `safety_warning` แล้วส่งเหตุผลกลับ critic-feedback retry
- ก่อนเข้า 6 validation stages มี contract preflight ตรวจ top-level object, `recipe_name`, `servings`, non-empty `adjusted_ingredients`/`instructions`, `diet_tags` (ต้องเป็น list ของ nonblank strings แต่ empty list ได้), `safety_warning` (nonblank string), `nutrition.basis` และ nutrient ทั้ง 4 ค่า; nutrient ต้องเป็น finite number ที่ไม่ใช่ boolean และไม่ติดลบ โดยกฎ calories เดิม `> 0` และ `<= 1500` ยังอยู่ใน stage 4 (preflight นี้ไม่ใช่ stage ที่ 7)
- Cooking Page แสดงคำเตือนทั่วไปตามข้อความ exact: **“ตรวจสอบวัตถุดิบและปริมาณจริงก่อนเริ่มทำอาหาร”**
- Item-specific notice เช่น “ไม่พบในรายการ My Fridge — กรุณาตรวจสอบว่ามี” ยัง defer ไป slice หลัง canonical ingredient resolver พร้อมแล้วเท่านั้น; ห้ามเทียบด้วย raw Thai/English string
- SQLite column `user_ingredients.quantity` เป็น legacy/deprecated และคงไว้เพื่อ compatibility เท่านั้น: implementation ไม่ rewrite ค่าเดิมและ insert แถวใหม่ด้วย `quantity = NULL`
- หลักฐาน local ล่าสุดหลัง final-review second pass: frontend contract tests 9/9 PASS, Vite build exit 0, lint คง baselineเดิม 3 errors/0 warnings (ผล frontend จาก first pass เพราะ second pass ไม่แก้ frontend); backend pure + mocked FastAPI handler tests 25/25 PASS และ `main.py`/`recipe_contracts.py` compile ผ่าน การทดสอบ FastAPI handler patch `call_agentic_llm` จึงไม่เรียก live Gemini, network หรือ server
- การทดสอบใช้ in-memory DB และ final verification ไม่เปลี่ยน `backend/database/recipes.db` (SHA256 ก่อน/หลัง final verification เท่ากัน: `7E647EE9AAA524941B20D792CDCBBE7786A1BF457DA66EDD23C01B0AEA941136`; แถว read-only ยังคงเป็น ids 19, 21, 22, 23, 24 พร้อมค่า quantity เดิม) อย่างไรก็ดี DB modified อยู่ก่อน final verification และไม่มี row/hash snapshot ก่อน Tasks 1–6 เริ่ม จึง **ไม่อ้าง** ว่า hash นี้พิสูจน์ความไม่เปลี่ยนแปลงตลอด implementation ทั้งหมด
- Design (local/ignored, ไม่ stage/commit): [`docs/superpowers/specs/2026-07-14-presence-only-fridge-design.md`](docs/superpowers/specs/2026-07-14-presence-only-fridge-design.md)
- Implementation plan (local/ignored, ไม่ stage/commit): [`docs/superpowers/plans/2026-07-14-presence-only-fridge.md`](docs/superpowers/plans/2026-07-14-presence-only-fridge.md) — item-specific badge และ quantity parseability validation ยังคง defer ตามขอบเขตด้านบน

**System Architecture diagram (Eraser.io) — งานนี้คือแก้ "ภาพ" ใน Eraser เท่านั้น ไม่ใช่แก้โค้ด (บทเรียนจากจุดที่ 1: ต้องเจาะจงเองว่าหมายถึง diagram หรือโค้ด — อย่าเดา):**

1. ~~"Retry (Max 3 times)" → Feedback loop~~ ✅ diagram แก้แล้ว **และ** โค้ดแก้แล้ว (`main.py`) — จุดนี้เสร็จสมบูรณ์ทั้งสองฝั่ง
2. ~~Allergen 2-layer แยกเป็น box "Allergen Validation (2-layer)" นอก 6-Step Check list~~ ✅ **diagram แก้แล้ว** (2026-07) — **⚠️ โค้ดยังไม่แก้** `check_allergy()` ใน `main.py` ยังเป็น rule-based ชั้นเดียวเหมือนเดิม (ยังไม่มี Knowledge Graph หรือ LLM hidden-allergen layer จริง) ถ้าจะ implement ต้องขอ confirm แยกเป็นงานใหม่ (เข้าเงื่อนไข Hard Rule ห้ามแก้ backend โดยไม่ขอก่อน)
3. ~~เส้น "Preferences" เข้า Agentic Prompt Engine~~ ✅ **diagram แก้แล้ว** (2026-07) — เปลี่ยน label เป็น `"Base Recipe + Ingredients + Preferences (+ History)"` แยก History ออกจาก Preferences ชัดเจน — **⚠️ ยังไม่ได้ implement personalization module จริง** (โค้ดยังไม่มีการดึง history มาฝังใน prompt เลย เป็นแค่ diagram ที่วาดล่วงหน้าไว้)
4. ~~เพิ่ม "Users DB"~~ ✅ **diagram แก้แล้ว** (2026-07) — เพิ่ม box "User DB" ใน Data Layer พร้อมลูกศร `FastAPI --"Query User Information"--> User DB` — **⚠️ ยังไม่ได้เริ่ม auth module จริง** (ยังไม่มีตาราง users, ยังไม่มี JWT/login endpoint ในโค้ด)

**สรุป:** รีวิว System Architecture diagram ครบทั้ง 4 จุดแล้ว (ฝั่ง diagram) — สิ่งที่ diagram แสดงตอนนี้คือ**เป้าหมายที่จะสร้าง** ไม่ใช่สถานะโค้ดปัจจุบัน ยังมีช่องว่างระหว่าง diagram กับโค้ดจริงอยู่ 3 โมดูลใหญ่ที่ยังไม่เริ่ม: Allergen Knowledge Graph + LLM layer, Personalization module, Auth/Users module (ทั้งหมดอยู่ใน `/backend/` — ต้องขอ confirm แยกเป็นรายโมดูลก่อนเริ่มแก้โค้ดตาม Hard Rule)

**ค้างอยู่ (ยังไม่ทำ):** บีบ Gantt chart ใน `docs/project-proposal.md` จาก ~12 เดือนเหลือ ~9 เดือนจริง (รู้ว่า scope พอ/เต็มสำหรับ 9 เดือนแล้ว ไม่ต้องเพิ่มอะไรอีก — ทีมเคยสร้าง prototype เดิมเสร็จใน 1-2 สัปดาห์ แต่ความเร็วนั้น**ไม่ transfer**ไปงาน evaluation/research ที่เหลือ เพราะ bottleneck ต่างกัน)

## Data Contracts

**`POST /api/generate-recipe-text`** (active contract):
```
Request:  { recipe: {...base_recipe}, ingredients: [{id?, name}], preferences: { allergy, taste, equipment, extra } }
Response: { status: "success"|"error", data: {recipe_name, servings, adjusted_ingredients[], diet_tags[], nutrition{basis:"per_serving",calories,protein_g,carbs_g,fat_g}, instructions[], safety_warning} }
```
Backend ยังรับ legacy ingredient strings/objects ที่มี metadata เพื่อ compatibility แต่ normalize เป็นชื่อเท่านั้นและ ignore `quantity`; FastAPI handler boundary ตรวจด้วย integration test ที่ mock `call_agentic_llm` แล้ว ไม่ใช่การทดสอบกับ live Gemini/network/server

**`GET /api/user-ingredients`** (active presence-only contract):
```
Request:  none
Response: { status: "success"|"error", data: [{id, name, category, image, selected}] }
```
เมื่อสำเร็จ `data` ไม่คืน legacy `quantity`; เมื่อ error จะคืน `message` แทน `data`

**`POST /api/user-ingredients`** (active presence-only contract):
```
Request:  { name, category, image }
Response: { status, data: {id, name, category, image, selected} }
```
⚠️ ยังไม่มี `user_id` — ต้องเพิ่มตอน migrate ไป PostgreSQL พร้อม auth

**`GET /api/ingredient-images/search`** (active contract, 2026-08-23):
```
Request:  query param q: string
Response: { status: "success"|"error", data?: {images: string[]}, message?: string }
```
`status: "error"` เมื่อ `PEXELS_API_KEY` ไม่ได้ตั้งใน `.env` หรือเรียก Pexels API ไม่สำเร็จ — frontend ต้อง fallback ไปปุ่ม upload

**`POST /api/ingredient-images/upload`** (active contract, 2026-08-23):
```
Request:  multipart/form-data, field "file" (.png/.jpg/.jpeg/.webp เท่านั้น)
Response: { status: "success"|"error", data?: {image: string}, message?: string }
```
ไฟล์ถูก save ลง `backend/images/ingredients/` ด้วยชื่อสุ่ม (`uuid4`), ยังไม่มี size limit หรือ virus/content scan — เหมาะกับ local dev เท่านั้น ต้องทำเพิ่มก่อน production

**ยังไม่ได้ออกแบบ (ต้องทำก่อนเริ่ม auth):** `/api/auth/register`, `/api/auth/login` (OAuth2PasswordRequestForm → JWT), `/api/barcode-lookup`, `/api/favorites`, `/api/ratings`, `/api/history`
## Research note (2026-07-15)

- Official CPI reference checked: TPSO/Ministry of Commerce annual CPI release for December 2568 and year 2568.
- Food and non-alcoholic beverages CPI: 2568 compared with 2567 increased 1.05% on an annual-average basis (AoA; January–December average), not a December-only YoY figure.
- Source: https://uploads.tpso.go.th/economic/pdf/Cpig122568_tg.pdf

## Presentation note (2026-07-15)

- The current Eraser system architecture is too detailed for a presentation slide because it mixes the primary user flow, implementation internals, data stores, external services, and future research components.
- Recommended slide abstraction: show one left-to-right flow: User/Fridge Input -> FastAPI Orchestrator -> AI Recipe Generation -> Validation + Critic Retry -> Validated Recipe/UI.
- Keep Open Food Facts, Gemini, and the database as small supporting components around the orchestrator. Collapse individual databases into one Data Store group and show the three research contributions as short badges: Nutrition Engine, Allergen Graph, and Critic-Feedback Loop.
- Do not show every validation sub-check or every database arrow on the main slide. Treat the diagram as a target/research architecture and label unimplemented modules as future work where needed.
- Slide mockup created in the thread visualization workspace: `homemade-architecture-slide.html`; use it as a visual reference for the PowerPoint redraw.
- Speaking script drafted for presentation pages 7–14 (4–5 minutes), centered on the system architecture. The script distinguishes the current prototype (React/Vite/Tailwind, FastAPI + SQLite, Gemini, existing validation and critic-feedback loop) from target/future modules (PostgreSQL, nutrition engine, allergen graph/LLM layer, auth and personalization). Exact page titles were not available in the workspace, so the page mapping is an assumed narrative order based on the architecture proposal.
- The source presentation PDF was reviewed directly on 2026-07-15. The page mapping is now verified against pages 7–14, and the finalized Thai speaking script is saved at `docs/presentation-script-pages-07-14.md` with about two minutes allocated to the system architecture slide.

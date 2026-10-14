# Homemade — AI Recipe Generator

ระบบสร้างและดัดแปลงสูตรอาหารจากวัตถุดิบในตู้เย็น สำหรับโครงงาน capstone โดยเน้นบริบทอาหารไทย การตรวจการแพ้อาหาร และข้อมูลโภชนาการที่ตรวจสอบที่มาได้

อัปเดตจากโค้ดและสถานะโปรเจกต์วันที่ **14 ตุลาคม 2026** รายละเอียดในหน้านี้แยกความสามารถที่อยู่บน `main` แล้วออกจากงานที่ยังไม่ได้ commit ในเครื่อง

## ความสามารถปัจจุบัน

ความสามารถต่อไปนี้มีโค้ดบน `main` ที่เผยแพร่แล้ว:

- **ตู้เย็น:** เพิ่ม ดู และลบวัตถุดิบ ระบุปริมาณ/หน่วยและวันหมดอายุได้ พร้อมเรียงและแสดงสถานะใกล้หมดอายุ การส่งให้ AI ใช้รายการชนิดวัตถุดิบ ไม่ใช่หลักฐานว่ามีปริมาณพอหรือระบบหักสต็อกอัตโนมัติ
- **บาร์โค้ด:** อ่านผ่านกล้องหรือกรอกเลข 8–14 หลัก ค้น Open Food Facts แล้วเติมข้อมูลในฟอร์มที่แก้ไขได้ ผู้ใช้ต้องกดบันทึกเอง และเพิ่มด้วยมือได้เมื่อค้นไม่พบ
- **สูตรอาหาร:** เลือกเมนูตั้งต้นหรือสร้างสูตรใหม่ด้วย Gemini พร้อมจำนวนที่เสิร์ฟ วัตถุดิบและขั้นตอน เมนูตั้งต้นแสดงช่วงเวลารวมโดยประมาณตามขั้นตอนของสูตร
- **ตรวจสูตรและลองแก้:** ตรวจรูปแบบผลลัพธ์ก่อนเข้า validation 6 ขั้น ส่งเหตุผลแรกที่ไม่ผ่านกลับไปให้ AI โดยสร้างได้สูงสุด **3 ครั้งรวมครั้งแรก**
- **การแพ้อาหาร:** ใช้กฎพื้นฐานร่วมกับ Knowledge Graph ใน PostgreSQL รองรับนโยบายสารก่อภูมิแพ้ 10 กลุ่ม แยกการพบโดยตรง/ส่วนประกอบที่เกี่ยวข้อง ขอคำชี้แจงเมื่อข้อมูลกำกวม และปฏิเสธคำขอที่ระบุการแพ้เมื่อกราฟที่ต้องใช้ไม่พร้อม
- **Nutrition Engine:** แยกผลคำนวณจากวัตถุดิบ/ปริมาณและข้อมูล INMU/USDA ออกจากค่าประมาณของ AI พร้อมสถานะความครบถ้วนของข้อมูล
- **บัญชีและโปรไฟล์:** สมัคร/เข้าสู่ระบบด้วย JWT ใน HttpOnly cookies, refresh/logout, รีเซ็ตรหัสผ่านด้วย email OTP, บันทึก preferences ชื่อ รูปโปรไฟล์ที่ครอปได้ และภาษาไทย/อังกฤษ
- **ประวัติและความชอบ:** เก็บสูตรที่สร้างสำเร็จ รายการโปรดของเมนูตั้งต้นและสูตรที่สร้าง คะแนน/แท็ก/ข้อความ feedback และดึงประวัติที่มีคะแนนมาเป็นบริบทของคำขอใหม่ผ่าน embeddings + pgvector เป็น personalization ใน prompt ไม่ใช่การฝึกโมเดลรายผู้ใช้

### งานล่าสุดที่ยังอยู่ใน working tree

ณ วันที่อัปเดต README งานต่อไปนี้มีโค้ดในเครื่องแต่ยังไม่ได้ commit/push จึง **ยังไม่รวมใน fresh clone ของ remote `main`**:

- แก้ไขวัตถุดิบในตู้เย็น: ชื่อ หมวดหมู่ ปริมาณ หน่วย และวันหมดอายุ
- หน้ารายละเอียดโภชนาการที่แยกผลคำนวณ/ค่าประมาณ/ข้อมูลไม่ครบ และคำนวณโภชนาการเมนูตั้งต้นใหม่จากปริมาณในสูตร
- ปรับข้อความภาษาไทย ฟอนต์ Noto Sans Thai ที่ให้บริการจากไฟล์ในโปรเจกต์ และแก้หน้า Favorites
- utility และ tests สำหรับการแก้ค่า total carbohydrate ของ N3 แบบ project-derived; หลักฐานและการแก้ข้อมูล dev DB เป็นคนละส่วนกับการเผยแพร่ source

การ clone และ seed ใหม่ไม่ได้ทำซ้ำข้อมูล nutrition ที่ผ่านการทบทวนและแก้ใน dev DB ทั้งหมด ดู [แนวทางดูแล nutrition และหลักฐานส่วนตัว](NUTRITION_MAINTENANCE.md)

## ขอบเขต validation และข้อจำกัด

หลังตรวจโครงสร้าง JSON ลำดับจริงใน `backend/main.py` คือ:

| ลำดับ | Check | ขอบเขตปัจจุบัน |
| --- | --- | --- |
| 1 | Ingredient | ตรวจวัตถุดิบกับรายการที่ผู้ใช้มีและเครื่องปรุงที่อนุญาต ยังมีข้อจำกัดด้านภาษาไทย/ชื่อผสม |
| 2 | Allergy | ตรวจรายการวัตถุดิบของสูตรด้วย matcher ร่วมกับ floor + KG |
| 3 | Flavor | กฎคู่รสชาติที่กำหนดไว้บางคู่ |
| 4 | Logic | กฎขั้นตอนบางกรณีและข้อความสรุปสต็อกที่ห้ามใช้ |
| 5 | Nutrition sanity | เงื่อนไขตัวเลขเบื้องต้น ร่วมกับการตรวจรูปแบบผลลัพธ์ |
| 6 | Core ingredient | กฎวัตถุดิบหลักบางกรณี |

ระบบหยุดที่เหตุผลแรกที่ไม่ผ่านในแต่ละครั้ง **Nutrition Engine ทำงานหลังสูตรผ่าน validation และอยู่นอก retry loop** ไม่ใช่ check ลำดับที่ 5

กฎเหล่านี้ยังไม่ใช่การยืนยันความปลอดภัยในการปรุง รสชาติ ความถูกต้องทางคลินิก หรือการตรวจสารก่อภูมิแพ้ทุกข้อความในขั้นตอนทำอาหาร ข้อมูลชื่อวัตถุดิบ แหล่งโภชนาการ ปริมาณต่อหน่วย และ proxy ยังมีช่องว่าง; ค่าที่คำนวณได้ไม่ได้แปลว่ามีหลักฐานแหล่งข้อมูลครบ และยังไม่มีการปรับการสูญเสียสารอาหารจากการปรุง/การดูดซับน้ำมัน

ยังไม่มีระบบส่งแจ้งเตือนอัตโนมัติหรือหน้า admin จัดการ catalog ส่วน YOLO ไม่ได้ใช้ใน flow ปัจจุบัน แม้ยังมีไฟล์และ dependency เดิมอยู่ งาน Local LLM/finetune เป็นส่วนทดลองแยกจาก API สร้างสูตรที่ใช้งานอยู่

## Tech stack

| ส่วน | เทคโนโลยีในโปรเจกต์ |
| --- | --- |
| Frontend | React 19, Vite 7, Tailwind CSS 4, React Router 7, Framer Motion, Lucide/React Icons |
| กล้องและรูปโปรไฟล์ | `@yudiel/react-qr-scanner`, `react-easy-crop` |
| Backend | FastAPI, SQLAlchemy 2, Alembic, psycopg |
| Database | PostgreSQL 16 + pgvector; Docker Compose รันเฉพาะฐานข้อมูล |
| Recipe generation | Google Gen AI SDK (`google-genai`), model ใน source: `gemini-3.1-flash-lite-preview` |
| History embeddings | `gemini-embedding-001`, 768 dimensions |
| Authentication | bcrypt + PyJWT, HttpOnly cookies, OTP/reset ticket |
| ข้อมูลภายนอก | Open Food Facts, INMU/USDA; Pexels สำหรับค้นรูปเมื่อกำหนด key |

SQLite ใช้กับ test fixtures และมีสคริปต์เก่าที่ deprecated; runtime หลักย้ายเป็น PostgreSQL แล้ว ชื่อ model ข้างต้นคือค่าที่โค้ดกำหนด ไม่ใช่การยืนยันว่า provider พร้อมให้บริการ ณ เวลารัน

## ตั้งค่า local development

ตัวอย่างใช้ **PowerShell บน Windows** ต้องมี Python พร้อม `venv`, Node.js ที่ Vite 7 รองรับ (`20.19+` ในสาย 20 หรือ `22.12+` ขึ้นไป), npm และ Docker Desktop ที่กำลังทำงาน

คำสั่งติดตั้งด้านล่างเป็นคู่มือสำหรับผู้พัฒนา ไม่ใช่สิ่งที่รันอัตโนมัติเมื่ออัปเดต README

### 1. Backend environment

จาก root โปรเจกต์:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

สร้าง `backend/.env` โดยใช้ secret ใหม่แยกกันสำหรับ JWT และ OTP สร้างแต่ละค่าด้วย `python -c "import secrets; print(secrets.token_hex(32))"`:

```dotenv
DATABASE_URL=postgresql+psycopg://homemade:homemade_dev_only@localhost:5432/homemade
GEMINI_API_KEY=replace_with_your_gemini_api_key
JWT_SECRET_KEY=replace_with_a_random_secret_at_least_32_bytes
OTP_HMAC_SECRET=replace_with_another_random_secret_at_least_32_bytes
EMAIL_BACKEND=console
COOKIE_SECURE=false
PERSONALIZATION_ENABLED=1
```

`homemade_dev_only` เป็นรหัสผ่านฐานข้อมูลตัวอย่างใน Compose สำหรับ local development เท่านั้น ห้าม commit `.env` หรือใช้ secret ตัวอย่างเป็นค่าจริง `EMAIL_BACKEND` ต้องกำหนดชัดเจน; `console` เขียน email/OTP ลง log และใช้เฉพาะ dev หากใช้ HTTPS ให้ตั้ง cookie policy ให้เหมาะกับ deployment

หากต้องส่ง OTP จริง ให้เปลี่ยนเป็น `EMAIL_BACKEND=smtp` และเพิ่ม:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_sender_account
SMTP_PASSWORD=your_app_password
SMTP_FROM=HomeMade OTP <your_sender_account>
```

backend ตรวจ config อีเมลตอน startup และ SMTP ใช้ STARTTLS สำหรับ Gmail ใช้ App Password; มี wizard `scripts/setup-gmail-smtp.sh` ให้รันผ่าน Git Bash จาก root โดยไม่ส่งอีเมลทดสอบ

ตัวเลือกเพิ่มเติม:

- `PEXELS_API_KEY`: สำหรับค้นรูปจาก Pexels
- `USDA_API_KEY`: สำหรับงาน import USDA ที่ผู้ดูแลเลือกทำแยก ไม่จำเป็นต่อการเปิด API ด้วยฐานข้อมูลที่เตรียมไว้แล้ว
- `PERSONALIZATION_ENABLED=0`: ปิด retrieval, embedding และงาน vector ที่เกี่ยวข้อง
- `LOCAL_LLM_BASE_URL` / `LOCAL_LLM_MODEL`: สำหรับ `LocalLLMGenerator` ในงานทดลอง ไม่ได้สลับ model ของ API ปัจจุบันโดยอัตโนมัติ

### 2. Database และ migrations

เปิดอีก terminal ที่ **root โปรเจกต์**:

```powershell
docker compose up -d db
```

ใน terminal backend ที่ activate venv และตั้ง `.env` แล้ว:

```powershell
alembic current
alembic upgrade head
```

ตรวจ migration ที่เปลี่ยนและสำรองข้อมูลก่อนใช้กับฐานข้อมูลที่มีข้อมูลจริง ต้อง apply migration ใหม่เมื่ออัปเดต source; ไม่ใช่ทำเฉพาะครั้งแรก `upgrade head` เดินจาก revision ปัจจุบันไป revision ล่าสุดตาม [คู่มือ Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

**เฉพาะฐานข้อมูล dev ใหม่ที่ยังไม่มีข้อมูล** สามารถเติมเมนูตัวอย่างและกราฟสารก่อภูมิแพ้จาก `backend/`:

```powershell
python database/seed_postgres.py
python -m database.seed_allergen_graph
```

schema/migration ไม่ได้เตรียมข้อมูล nutrition ให้ครบ สคริปต์เมนูตัวอย่างอาจใช้ค่า nutrition ที่กรอกไว้เมื่อคำนวณไม่ได้ และสามารถอัปเดตข้อมูลเมนูเดิมได้ จึงห้ามใช้ reseed เพื่อซ่อมฐานข้อมูลเดิมโดยไม่ทบทวน diff ข้อมูลก่อน งานนำเข้า INMU/USDA, aliases, portions, reviewed corrections และ embedding backfill ต้องเตรียมและตรวจแยกตาม [NUTRITION_MAINTENANCE.md](NUTRITION_MAINTENANCE.md) ไม่ใช่ bootstrap อัตโนมัติ

กราฟที่ยังไม่พร้อมอาจทำให้คำขอสร้างสูตรที่ระบุการแพ้ถูกปฏิเสธตามนโยบายปัจจุบัน ข้อมูลเก็บใน named volume `pgdata` ของ Compose; อย่าลบ volume เพื่อแก้ปัญหาการรัน

### 3. รัน API และ frontend

จาก `backend/` ที่ activate venv แล้ว:

```powershell
uvicorn main:app --reload
```

API: [http://127.0.0.1:8000](http://127.0.0.1:8000) · Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

ต้องรัน API จาก `backend/` เนื่องจาก static images ใช้ path ที่สัมพันธ์กับ working directory

อีก terminal จาก root:

```powershell
cd frontend
npm ci
npm run dev
```

เปิด [http://localhost:5173](http://localhost:5173) ตาม URL ที่ Vite แสดง `frontend/vite.config.js` ส่ง `/api` ไป `http://127.0.0.1:8000` ผ่าน [Vite proxy](https://vite.dev/config/server-options.html#server-proxy) หาก port 5173 ถูกใช้อยู่ ให้จัดการ port ให้ตรงกับ origin ที่ backend อนุญาต

`docker compose up` ไม่ได้เปิด API/frontend ให้ และ `npm run build` สร้าง frontend assets เท่านั้น การ deploy ต้องจัดการการเสิร์ฟ assets, API routing, HTTPS/cookies และ secrets เพิ่มเติม

## ตรวจสอบก่อนส่งงาน

Frontend จาก `frontend/`:

```powershell
node --test test/*.test.js
npm run build
npm run lint
```

Backend จาก `backend/` โดยใช้ environment ที่ติดตั้ง dependencies และตั้งค่าไว้แล้ว:

```powershell
python tests/run_offline.py
# หรือเลือกเฉพาะกลุ่ม
python tests/run_offline.py 'test_nutrition_*.py'
```

offline runner ใช้ fixtures โดยปิด network/provider และ persistent DB จึงไม่ใช่ผลทดสอบ PostgreSQL, Gemini, SMTP หรือกล้องจริง การตรวจหลักฐาน nutrition ส่วนตัวแยกจาก default suite และอาจต้องใช้ bundle ที่ไม่ได้เผยแพร่

มีประวัติ frontend suite ล้มใน assertions ของ CookingPage/quantity contract และ lint บางจุด รวมถึง bundle-size warning; อ่านผลรันปัจจุบันก่อนสรุปว่าผ่านทั้งหมด การอัปเดต README นี้ตรวจความตรงกับ source และเอกสาร ไม่ได้รัน application test suites ใหม่

## โครงสร้างที่ใช้จริง

```text
homemade/
├── backend/
│   ├── main.py                 # API, generation orchestration และ validation
│   ├── database/               # connection, ORM models, seeds และ backfill
│   ├── alembic/                # PostgreSQL schema migrations
│   ├── allergen_kg/            # floor, graph resolution และ matcher
│   ├── nutrition/              # parser, lookup, calculation และ maintenance
│   ├── personalization/        # retrieval และ prompt context
│   ├── generators/             # generator adapters สำหรับงานทดลอง
│   ├── eval/                   # evaluation tools และ fixtures
│   ├── finetune/               # งานทดลองเตรียมข้อมูล/โมเดล
│   ├── images/                 # static ingredient/menu images
│   └── tests/                  # unittest และ offline runner
├── frontend/
│   ├── src/components/         # shared UI
│   ├── src/pages/              # application screens
│   ├── src/context/            # authentication และ locale
│   ├── src/utils/              # validation, payloads และ translations
│   ├── test/                   # Node test runner
│   └── vite.config.js          # React/Tailwind plugins และ API proxy
├── docker-compose.yml          # PostgreSQL 16 + pgvector
├── NUTRITION_MAINTENANCE.md     # ขอบเขต tests/imports/reviewed evidence
├── GLOSSARY.md                 # คำศัพท์และความหมายในโปรเจกต์
└── spec.md                     # สถานะและการตัดสินใจของโครงการ
```

## เอกสารและการทำงานร่วมกัน

- [spec.md](spec.md): สถานะล่าสุด การตัดสินใจ งานต่อ และ data contracts; อ่านรายการใหม่ก่อนบันทึกประวัติเก่า
- [GLOSSARY.md](GLOSSARY.md): ความหมายของคำที่ใช้ร่วมกัน
- [MEMORY.md](MEMORY.md): ข้อผิดพลาดที่ต้องไม่ทำซ้ำ
- [AGENTS.md](AGENTS.md): ข้อกำหนดการแก้ไขโปรเจกต์ รวมถึงการยืนยันแผนก่อนแก้ backend และขออนุญาตก่อนติดตั้ง package
- `docs/` และ `tmp/` เป็น local-only ตาม `.gitignore` จึงอาจไม่มีใน fresh clone รวมถึงหลักฐาน/แผนงานที่ spec อ้างถึง ข้อเสนอใน `docs/project-proposal.md` เป็นร่างเก่า ไม่ใช่ข้อกำหนดล่าสุดทั้งหมด

ขอบเขต contribution ที่ต้องประเมินทางวิชาการคือ nutrition engine, allergen validation และ critic-feedback loop ส่วน UI/auth/barcode และความสะดวกในการใช้งานเป็น product envelope การมี code path หรือผ่าน regression tests ยังไม่ใช่หลักฐานความแม่นยำหรือผลการทดลองกับผู้ใช้

# 🍳 Homemade AI Recipe

แอปพลิเคชันแนะนำสูตรอาหารอัจฉริยะที่ช่วยจัดการวัตถุดิบในบ้านและคิดค้นเมนูอาหารสุดพิเศษที่ตอบโจทย์ความต้องการและสุขภาพของคุณโดยเฉพาะ!

## 🌟 จุดเด่นของโปรเจกต์ (Core Features)
*   **🛒 My Fridge:** ระบบจัดการวัตถุดิบในตู้เย็น (เพิ่ม/ลบ/เลือก) เพื่อนำมาคำนวณสูตรอาหาร
*   **🤖 Smart AI Chef:** ใช้ AI (Gemini 3.1 Flash) วิเคราะห์วัตถุดิบที่คุณมีและสร้างสรรค์เมนูใหม่ที่ทำได้จริง
*   **🛡️ 6-Stage Validation:** ระบบตรวจสอบสูตรอาหารอัจฉริยะ 6 ขั้นตอนเพื่อให้มั่นใจว่าสูตรที่ AI สร้างมานั้น:
    1.  **Safety First:** ปลอดภัย (เนื้อสัตว์ต้องสุก, ไม่มีขั้นตอนอันตราย)
    2.  **Ingredient Logic:** ใช้วัตถุดิบที่มีจริงตามที่ระบุ
    3.  **Cooking Logic:** ขั้นตอนการทำถูกต้องตามหลักพื้นฐาน
    4.  **Nutrition Check:** ข้อมูลโภชนาการสมเหตุสมผล
    5.  **Flavor Pairing:** รสชาติเข้ากันได้ดี
    6.  **Allergy Safety:** ปลอดภัยตามเงื่อนไขการแพ้อาหารของผู้ใช้
*   **🔄 Adaptive Retry:** หากสูตรไม่ผ่านการตรวจสอบ ระบบจะส่งเหตุผลที่ไม่ผ่านกลับไปให้ AI แก้ไขเฉพาะจุดในรอบถัดไป (สูงสุด 3 รอบ) แทนการสุ่มสร้างสูตรใหม่ทั้งหมด
*   **📊 Nutrition Info:** ข้อมูลแคลอรี และสารอาหารครบถ้วน (Protein, Carbs, Fat)

## 🚀 Tech Stack
*   **Frontend:** React + Vite, Tailwind CSS v4, Lucide React(icons)
*   **Backend:** FastAPI (Python)
*   **Database:** PostgreSQL (+ pgvector) via SQLAlchemy + Alembic
*   **AI Models:** Gemini 3.1 Flash (Google Generative AI)

---

## 🛠️ วิธีการติดตั้งและรันโปรเจกต์ (Getting Started)

### 1️⃣ การตั้งค่า Backend (FastAPI + Database)
เปิด Terminal ในโฟลเดอร์ `backend`:

1.  **สร้างและเปิดใช้งาน Virtual Environment**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # สำหรับ Windows
    ```
2.  **ติดตั้ง Libraries**
    ```bash
    pip install -r requirements.txt
    ```
3.  **ตั้งค่า Environment Variable**
    สร้างไฟล์ `.env` ไว้ในโฟลเดอร์ `backend/` แล้วใส่ API Key + DB config:
    ```env
    GEMINI_API_KEY=ใส่_API_KEY_ของคุณที่นี่
    DATABASE_URL=postgresql+psycopg://homemade:homemade_dev_only@localhost:5432/homemade
    JWT_SECRET_KEY=ใส่_random_secret_ของคุณที่นี่ (เช่น python -c "import secrets; print(secrets.token_hex(32))")
    ```
4.  **เริ่มต้นฐานข้อมูล (Database Initialization)**
    ต้องมี Docker รันอยู่ก่อน แล้วสั่ง (รันจาก root โปรเจกต์):
    ```bash
    docker compose up -d
    ```
    จากนั้นสร้างตาราง + seed ข้อมูลตัวอย่าง (รันจาก `backend/`):
    ```bash
    alembic upgrade head
    python database/seed_postgres.py
    ```
    > ⚠️ **ทำแค่ครั้งแรกเท่านั้น** (ตอน clone ใหม่ / container เป็น volume เปล่า) ข้อมูลจะถูกเก็บถาวรใน Docker volume (`pgdata`) แล้ว รันครั้งต่อไปแค่ `docker compose up -d` พอ **ไม่ต้อง** รัน `alembic upgrade head` / `seed_postgres.py` ซ้ำ (ยกเว้นมี migration ใหม่ที่ยังไม่ apply หรือลบ volume ทิ้งด้วย `docker compose down -v`)
5.  **รันเซิร์ฟเวอร์**
    ```bash
    uvicorn main:app --reload
    ```
    *(เซิร์ฟเวอร์จะรันอยู่ที่: http://127.0.0.1:8000)*

---

### 2️⃣ การตั้งค่า Frontend (React + Vite)
เปิด Terminal ในโฟลเดอร์ `frontend`:

1.  **ติดตั้ง Dependencies**
    ```bash
    npm install  # หรือใช้ bun install
    ```
2.  **รันหน้าเว็บ**
    ```bash
    npm run dev  # หรือใช้ bun dev
    ```
    *(หน้าเว็บจะรันอยู่ที่: http://localhost:5173)*

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)
```text
homemade/
├── backend/               # ระบบ API และ Database
│   ├── database/          # SQLAlchemy models, Alembic migrations, seed script (SQLite ไฟล์เดิมยังอยู่แต่ deprecated ไม่ได้ใช้แล้ว)
│   ├── model/             # (Internal) บริการเสริมอื่นๆ
│   ├── images/            # เก็บรูปภาพวัตถุดิบและเมนู
│   ├── main.py            # ไฟล์หลักของ FastAPI
│   └── .env               # (ต้องสร้างเอง) เก็บ API Key
└── frontend/              # ระบบ UI (React)
    ├── src/
    │   ├── pages/         # หน้าจอต่างๆ (Home, Fridge, Cooking, ฯลฯ)
    │   ├── components/    # Common Components
    │   └── App.jsx        # ตัวจัดการ Routing
    └── tailwind.config.js # การตั้งค่า Design System
```

## 🤝 ข้อกำหนดสำหรับทีมพัฒนา
*   **Mobile-First Design:** ทุกการแก้ไข UI ต้องรองรับการแสดงผลบนมือถือ (Max-width 430px)
*   **Security:** ห้าม Commit ไฟล์ `.env` ขึ้น Git เด็ดขาด
*   **Validation:** หากมีการแก้ไข Logic การสร้างสูตรอาหาร ต้องทดสอบผ่าน Validation Pipeline ใน `main.py` เสมอ

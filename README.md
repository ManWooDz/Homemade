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
*   **📊 Nutrition Info:** ข้อมูลแคลอรี และสารอาหารครบถ้วน (Protein, Carbs, Fat)

## 🚀 Tech Stack
*   **Frontend:** React + Vite, Tailwind CSS v4, Lucide React(icons)
*   **Backend:** FastAPI (Python)
*   **Database:** SQLite
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
    สร้างไฟล์ `.env` ไว้ในโฟลเดอร์ `backend/` แล้วใส่ API Key:
    ```env
    GEMINI_API_KEY=ใส่_API_KEY_ของคุณที่นี่
    ```
4.  **เริ่มต้นฐานข้อมูล (Database Initialization)**
    คุณจำเป็นต้องรันสคริปต์เพื่อสร้างฐานข้อมูลและข้อมูลตัวอย่างก่อน:
    ```bash
    python database/setup_db.py
    python database/setup_ingredients.py
    ```
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
│   ├── database/          # ไฟล์ SQLite และสคริปต์ Setup
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

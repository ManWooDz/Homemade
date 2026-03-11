# 🍳 Homemade AI Recipe

แอปพลิเคชันแนะนำสูตรอาหารอัจฉริยะ เพียงแค่ถ่ายรูปวัตถุดิบในตู้เย็น ระบบจะใช้ AI วิเคราะห์วัตถุดิบและคิดค้นเมนูอาหารสุดพิเศษพร้อมวิธีทำและข้อมูลโภชนาการให้คุณทันที!

## 🚀 Tech Stack
* **Frontend:** React + Vite, Tailwind CSS v4, Lucide React
* **Backend:** FastAPI, Python
* **AI Models:** YOLO11 (Object Detection), Gemini 2.0 Flash (Agentic LLM)

---

## 🛠️ วิธีการติดตั้งและรันโปรเจกต์ (Getting Started)

เนื่องจากโปรเจกต์นี้แยกการทำงานเป็น 2 ส่วน (Frontend และ Backend) คุณจำเป็นต้องเปิด Terminal 2 หน้าต่างเพื่อรันทั้งสองฝั่งพร้อมกันครับ

### 1️⃣ การตั้งค่า Backend (FastAPI + AI)
เปิด Terminal หน้าต่างที่ 1 แล้วทำตามขั้นตอนต่อไปนี้:

1. เข้าไปที่โฟลเดอร์ backend
   > cd backend

2. สร้างและเปิดใช้งาน Virtual Environment
   > python -m venv venv  
   > .\venv\Scripts\activate

3. ติดตั้งไลบรารีที่จำเป็น
   > pip install -r requirements.txt

4. สร้างไฟล์ .env ไว้ในโฟลเดอร์ backend/ และใส่ API Key ของ Gemini
   > GEMINI_API_KEY=ใส่_API_KEY_ของคุณที่นี่

5. รันเซิร์ฟเวอร์
   > uvicorn main:app --reload  
   > (เซิร์ฟเวอร์จะรันอยู่ที่: http://127.0.0.1:8000)

---

### 2️⃣ การตั้งค่า Frontend (React + Vite)
เปิด Terminal หน้าต่างที่ 2 แล้วทำตามขั้นตอนต่อไปนี้:

1. เข้าไปที่โฟลเดอร์ frontend
   > cd frontend

2. ติดตั้ง Dependencies
   > bun install  
   > (หรือใช้ npm install)

3. รันหน้าเว็บแอปพลิเคชัน
   > bun dev  
   > (หรือใช้ npm run dev)  
   > (หน้าเว็บจะรันอยู่ที่: http://localhost:5173)

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)
> homemade/  
> ├── backend/&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# ระบบ API และ AI Models  
> │&emsp;&emsp;├── main.py&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# ไฟล์หลักของ FastAPI  
> │&emsp;&emsp;├── requirements.txt&emsp;&emsp;&emsp;# รายชื่อไลบรารี Python  
> │&emsp;&emsp;└── .env&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# (ต้องสร้างเอง) เก็บ API Key  
> │  
> └── frontend/           # ระบบหน้าบ้าน  
>&emsp;&emsp;&emsp;├── src/  
>&emsp;&emsp;&emsp;│&emsp;&emsp;├── pages/&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# หน้าจอต่างๆ ของแอป (Home, Cooking, ฯลฯ)  
>&emsp;&emsp;&emsp;│&emsp;&emsp;├── App.jsx&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# ตัวจัดการ Routing ควบคุมหน้าจอ  
>&emsp;&emsp;&emsp;│&emsp;&emsp;└── index.css&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# ตั้งค่า Tailwind CSS v4  
>&emsp;&emsp;&emsp;└── package.json&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# รายชื่อไลบรารี Node.js  

## 🤝 สำหรับผู้ร่วมพัฒนา (Contributors)
* ห้ามนำไฟล์ .env หรือ API Key ขึ้น GitHub เด็ดขาด
* หากมีการเพิ่มไลบรารีฝั่ง Python อย่าลืมอัปเดตไฟล์ requirements.txt (ใช้คำสั่ง pip freeze > requirements.txt)
* หากแก้ไข UI ให้ยึดดีไซน์แบบ Mobile-first (จำกัดความกว้างที่ max-w-[430px])

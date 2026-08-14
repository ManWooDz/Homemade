# MEMORY — สิ่งที่พลาดมาแล้ว ห้ามพลาดซ้ำ

รูปแบบ: what (เกิดอะไรขึ้น) / root cause (ทำไมถึงพลาด) / correct (สิ่งที่ต้องทำแทน)

---

**Terminology overclaiming (2026-07):**
- what: label diagram/ตัวชี้วัดด้วยคำเทคนิคที่ฟังดูดี (เช่น เรียก simple `SELECT * FROM base_recipes` ว่า "RAG Query")
- root cause: อยากให้ระบบดูมี technical depth มากกว่าที่โค้ดทำจริง
- correct: ชื่อ/label ต้องตรงกับสิ่งที่โค้ดทำจริงเสมอ ถ้าเป็นแค่ DB lookup ธรรมดา อย่าเรียกด้วยศัพท์ ML/AI เฉพาะทาง (RAG, embedding, etc.) — กรรมการ/ผู้เชี่ยวชาญจับได้ทันทีถ้าถามลึกแล้วคำตอบไม่ตรง

**Circularity trap ในการวัดผล (2026-07):**
- what: เกือบตั้ง "Nutrition MAE เทียบ ground truth" เป็น headline metric
- root cause: ถ้า ground truth มาจาก DB เดียวกับที่ engine ใช้คำนวณ error จะ ~0 โดยธรรมชาติ (แค่เลขคณิตถูก ไม่ได้พิสูจน์อะไร)
- correct: metric ที่วัด contribution จริงต้องเป็น "ความแม่นยำการ parse/จับคู่ชื่อวัตถุดิบไทย → DB" เทียบ human-annotated ground truth ไม่ใช่เทียบ DB ที่ engine อ้างอิงเอง ส่วน "LLM เดาคลาดจาก DB กี่ %" ให้ใช้เป็น "แรงจูงใจของปัญหา" ไม่ใช่ metric ของ contribution

**Overclaiming metric ที่วัดไม่ได้จริงในกรอบเวลาโครงงาน (2026-07):**
- what: เกือบตั้ง KPI ตายตัวให้ Personalization ("Rating Improvement") และ Expiry Tracking ("ลด food waste X%")
- root cause: ฟีเจอร์ทั้งสองต้องใช้ longitudinal data (ใช้นานแล้วดีขึ้นจริงไหม) ซึ่งแอปใหม่ไม่มีข้อมูลสะสมพอ (cold start) และวัดในกรอบเวลา capstone ไม่ทัน
- correct: จัดเป็น "demonstrated, not measured" — โชว์ในเดโมว่าทำงานได้จริง แต่ไม่ผูก KPI ตัวเลขที่ต้องพิสูจน์ ตั้ง KPI ที่พิสูจน์ไม่ได้จริงเสียหายกว่าไม่ตั้งเลย

**Stack mismatch เวลาแนะนำ library (2026-07):**
- what: ผู้ใช้ถามว่าควรใช้ Auth.js/BetterAuth ไหม
- root cause: สองตัวนี้เป็น Node.js-only library ต้องรันบน Node runtime แต่ backend จริงคือ FastAPI (Python)
- correct: ก่อนแนะนำ library ต้องเช็คก่อนว่ามัน compatible กับ runtime/ภาษาของ backend จริง ไม่ใช่แนะนำเพราะ "เป็นที่นิยม" เฉยๆ — สำหรับ FastAPI ใช้ passlib+python-jose+OAuth2PasswordBearer (เขียนเอง) หรือ fastapi-users เท่านั้น

**Blind-retry ไม่ใช่ critic-feedback loop (2026-07):**
- what: โค้ดเดิมใน main.py (`generate_recipe_text`) มี retry loop สูงสุด 3 รอบ แต่เรียก `call_agentic_llm()` ด้วย argument ชุดเดิมทุกรอบ ไม่ส่งเหตุผลที่ fail กลับไป
- root cause: retry ถูกเข้าใจผิดว่าเท่ากับ "agentic self-correction" ทั้งที่มันคือการสุ่มใหม่เฉยๆ
- correct: critic-feedback loop ต้องส่ง `result["reason"]` จาก validation ที่ fail กลับเข้า prompt ของรอบถัดไปเสมอ (ดู spec.md → Current State สำหรับโค้ดที่ต้องแก้)

**YOLO ถูกตัดออกจาก scope แล้ว (2026-07):**
- what: มีไฟล์ `backend/model/yolo11n_food.pt` อยู่ในโปรเจกต์ และเคยถูกเสนอให้ใช้แทน barcode scanner
- root cause: ทีมตัดสินใจไม่ใช้ YOLO แล้ว (แจ้งชัดเจนแล้วว่า "ไม่คิดจะใช้แล้ว")
- correct: **ห้ามเสนอ YOLO กลับมาอีก** ใช้ Barcode Scanner (Open Food Facts API + fallback พิมพ์เอง) แทนสำหรับการเพิ่มวัตถุดิบแบบเร็ว ไฟล์ .pt ที่มีอยู่ถือเป็น dead code ที่ยังไม่ได้ลบ ไม่ใช่ของที่จะใช้งาน

**Launcher host/readiness mismatch (2026-07):**
- what: Vite default-bound on `::1:5173` while the launcher polled `127.0.0.1:5173`, causing readiness timeout even though Vite was running.
- root cause: the command relied on Vite's implicit host while the readiness URL explicitly required IPv4.
- correct: run `bun run dev -- --host 127.0.0.1 --port 5173 --strictPort`, then verify the listener address and HTTP readiness URL match before declaring startup successful.
**Local file preview blocked by in-app browser policy (2026-07-15):**
- what: Tried to preview a generated local HTML visual through the in-app browser using a `file://` URL.
- root cause: Browser URL policy blocks local file navigation.
- correct: Use the inline visualization artifact or a directly rendered local image; do not attempt browser-policy workarounds or alternate indirect navigation.

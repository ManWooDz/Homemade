---
target: BarcodeScanPage.jsx
total_score: 24
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:C:\\prosper666\\Generative_AI\\homemade\\frontend\\src\\pages\\BarcodeScanPage.jsx"
target_fingerprint: "sha256:98921097af7570f14758c0ff1a202f313f259b93ae5a778065e420142519de05"
target_path: "C:\\prosper666\\Generative_AI\\homemade\\frontend\\src\\pages\\BarcodeScanPage.jsx"
timestamp: 2026-10-12T20-25-01Z
slug: frontend-src-pages-barcodescanpage-jsx
---
<!-- Critique archive. Only the separate intermediate report-body.md is deprecated for manual removal. -->
Method: dual-agent (A: /root/design_review · B: /root/detector_evidence)

**หน้า BarcodeScanPage ใช้โครงเดิมต่อได้ แต่ควรแก้การกู้คืนและ accessibility ก่อนแต่งหน้าตา — 24/40 (Acceptable)** คะแนนเป็นการประเมิน UX เชิงคุณภาพ ไม่ใช่ KPI ของ capstone

โลโก้ สีส้ม และกรอบมือถือสอดคล้องกับ HomeMade ส่วนเนื้อหายังให้ความรู้สึกเป็นเครื่องมือค้นหาบาร์โค้ดทั่วไป มากกว่าขั้นตอนเพิ่มวัตถุดิบเข้าตู้เย็น ไม่จำเป็นต้อง redesign ทั้งหน้า

| เกณฑ์ Nielsen | /4 | เหตุผลหลัก |
|---|---:|---|
| สถานะระบบ | 2 | มี spinner แต่ไม่ประกาศสถานะให้ screen reader |
| ภาษาตรงกับผู้ใช้ | 2 | หัวข้อและปุ่มหลักเป็นอังกฤษกลาง flow ไทย |
| ควบคุมและออกจาก flow | 3 | มี back/retry/manual แต่ retry ทำเลขหาย |
| ความสม่ำเสมอ | 3 | โครงและสีเข้าชุด ภาษาและขนาดปุ่มยังไม่สม่ำเสมอ |
| ป้องกันข้อผิดพลาด | 2 | ปิดปุ่มเมื่อว่าง แต่เลขสั้นเกินไปยังส่งได้ |
| ไม่ต้องจำข้อมูลเอง | 2 | เลขหายระหว่างค้นหาและหลังผิดพลาด |
| ความรวดเร็วและทางเลือก | 3 | กล้องและช่องพิมพ์เหมาะกับงานทีละรายการ |
| ความเรียบง่าย | 3 | หน้าไม่รก แต่กรอบกล้องเสียยังเด่นที่สุด |
| กู้คืนจากข้อผิดพลาด | 2 | มีทางออก แต่ไม่รักษาข้อมูลที่พิมพ์ |
| คำแนะนำ | 2 | มีวิธีถือกล้อง ขาดคำแนะนำเรื่องเลขและการเพิ่มเอง |
| **รวม** | **24/40** | **Acceptable** |

**สิ่งที่ทำได้ดี**

- ลำดับหัวข้อ → กล้อง → พิมพ์เลขเข้าใจง่าย ทั้งจอ 390px และจอกว้างที่คงกรอบ 430px
- เมื่อค้นหาไม่พบ มีทั้งลองใหม่และเพิ่มเอง ไม่จบที่ข้อความผิดพลาด
- เมื่อพบสินค้า flow จริงส่งข้อมูลไปฟอร์ม AddIngredient ให้ตรวจแก้ก่อนบันทึก

**ห้าจุดที่ควรแก้ ตามลำดับ**

1. **[P1] ลองใหม่แล้วต้องพิมพ์เลขทั้งหมดอีกครั้ง** — [BarcodeScanPage.jsx](C:/prosper666/Generative_AI/homemade/frontend/src/pages/BarcodeScanPage.jsx:67) ถอด scanner ออกเมื่อค้นหา และ [BarcodeScanner.jsx](C:/prosper666/Generative_AI/homemade/frontend/src/components/BarcodeScanner.jsx:50) เก็บเลขไว้ภายในตัวเอง เบราว์เซอร์ยืนยันว่า error → ลองใหม่ → ช่องว่าง ควรเก็บเลขไว้ที่หน้า แสดงเลขที่กำลังค้นหา และให้แก้/ค้นหาเลขเดิมได้ ใช้ **impeccable harden**

2. **[P1] การเข้าถึงยังขาดทั้งชื่อและการแจ้งสถานะ** — [ปุ่มย้อนกลับ](C:/prosper666/Generative_AI/homemade/frontend/src/pages/BarcodeScanPage.jsx:49) ไม่มี accessible name; [ช่องเลข](C:/prosper666/Generative_AI/homemade/frontend/src/components/BarcodeScanner.jsx:117) ไม่มี label ผูกกับ input; loading/error ไม่มี live announcement และ focus กลับ BODY หลังส่ง ควรเพิ่ม label/name, ประกาศสถานะและคืน focus ให้เหมาะสม พร้อมปรับ contrast ของข้อความเล็ก: helper เทา/ขาว 2.60:1, error แดง/ขาว 3.82:1, ขาว/ส้ม 3.39:1 คงสีแบรนด์ไว้ได้โดยปรับเฉพาะคู่สีข้อความ/ปุ่ม ใช้ **impeccable harden**

3. **[P2] กรอก 1 หลักก็เริ่มค้นหาได้** — [handleManualSubmit](C:/prosper666/Generative_AI/homemade/frontend/src/components/BarcodeScanner.jsx:81) ตรวจแค่ว่าไม่ว่าง เบราว์เซอร์ยืนยันว่าเลข 1 เข้าสถานะค้นหา ทั้งที่ contract รับ 8–14 หลัก ควรแจ้งข้อกำหนดข้างช่องและตรวจให้ผ่านก่อนส่ง โดยรักษาค่าที่พิมพ์ไว้ ใช้ **impeccable harden**

4. **[P2] เมื่อกล้องเปิดไม่ได้ กรอบดำยังเป็นองค์ประกอบใหญ่ที่สุด** — [กรอบกล้อง](C:/prosper666/Generative_AI/homemade/frontend/src/components/BarcodeScanner.jsx:90) ยังอยู่ ขณะที่ทางเลือกเพิ่มวัตถุดิบเองปรากฏเฉพาะหลัง lookup error ควรลดพื้นที่กล้องในสถานะนี้ ทำช่องพิมพ์ให้เป็นจุดนำ และเปิดทาง “เพิ่มวัตถุดิบเอง” ผ่าน callback ที่มีอยู่ทันที ไม่ควรบังคับของสดหรือสินค้าที่ไม่มีเลขให้ค้นหาล้มเหลวก่อน ใช้ **impeccable clarify**

5. **[P2] หัวข้อและปุ่มหลักสลับภาษา** — “Scan Barcode” และ “Look up” กลางข้อความไทยทำให้ต้องแปลเอง เปลี่ยนเป็น “สแกนบาร์โค้ด” และ “ค้นหาสินค้า”; ใช้ label “เลขบาร์โค้ด” และบอกการพิมพ์เป็นทางเลือกปกติ ไม่ใช่เฉพาะเมื่อกล้องเสีย ใช้ **impeccable clarify**

**ภาระความคิดและความรู้สึก**

ทางเลือกหลักมีเพียงสแกนหรือพิมพ์ จึงไม่ซับซ้อน ปัญหาคือการบังคับให้จำ/พิมพ์เลขใหม่ เมื่อรอนานแล้วไม่พบ ผู้ใช้จบ flow ด้วยงานเพิ่มแทนความคืบหน้า เมนูล่างห้ารายการและปุ่มทำอาหารดึงสายตาอยู่บ้าง แต่เป็นโครงร่วมที่ไม่ควรรื้อจาก critique หน้านี้อย่างเดียว

**มองผ่านผู้ใช้สามแบบ**

- ผู้ใช้ครั้งแรก: “Look up” และการซ่อนเพิ่มเองทำให้ขั้นถัดไปไม่ชัด
- ผู้ใช้ screen reader: back/input ไม่มีชื่อที่อธิบายงาน และการเปลี่ยนสถานะไม่ถูกประกาศ
- ผู้ใช้มือถือมือเดียว: ต้องพิมพ์เลขยาวซ้ำ ช่อง/ปุ่มค้นหาสูง 38px ต่ำกว่าแนวทาง 44px ของโปรเจกต์

**ข้อสังเกตย่อย**: ปุ่มกลับขนาด 40×40px; ควรปรับให้สอดคล้องกับขนาดสัมผัสของโปรเจกต์ ขนาด 38px ไม่ใช่หลักฐานว่าผิดเกณฑ์ WCAG 24px อัตโนมัติ อีกจุดจาก source คือ response สำเร็จหลังผู้ใช้เปลี่ยนหน้าอาจเรียก callback พากลับเข้า AddIngredient; ยังไม่ได้ reproduce จึงเป็นรายการตรวจต่อ ไม่ใช่บั๊กที่ยืนยันแล้ว

**หลักฐาน**: A และ B ประเมินแยกกัน ตรวจ actual components ผ่าน preview ที่ mock auth/lookup และปฏิเสธกล้อง จอ 390×844 และ desktop; A ตรวจ loading/not-found/retry/เลขสั้น, B ตรวจเพิ่ม network/success callback และ DOM/AX/ขนาด/contrast Detector สแกนทั้งสองไฟล์ผ่านและได้ **0 findings** ซึ่งไม่ครอบคลุมปัญหาพฤติกรรมและการเข้าถึงที่ตรวจพบในเบราว์เซอร์ ไม่มี false positive ให้ตัด ไม่มี overlay เพราะ API evaluate เป็น read-only

**คำถามเพื่อเลือกงานต่อ**: จะเน้นเก็บเลขและ retry, accessibility หรือภาษาไทยและสถานะกล้องก่อน? ขอบเขตต่อไปเป็นสอง P1, ทั้งห้าข้อ หรือเฉพาะข้อความ?

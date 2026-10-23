# ยืนยันอีเมลตอนสมัครสมาชิก

สถานะวันที่ 22 ตุลาคม 2026: เพิ่มโค้ดและรัน migration บนฐานข้อมูล development `homemade` ใน `homemade-db-1` แล้ว จาก revision `b9c0d1e2f3a4` เป็น `c0d1e2f3a4b5` ไม่มีการส่งอีเมลจริงหรือสร้างบัญชีทดสอบในฐานข้อมูลนี้ระหว่างตรวจงาน

## Flow ที่เปลี่ยน

สมัครสมาชิก → กรอก OTP → สร้างบัญชีและ session → Onboarding → Home

เดิม Register สร้างแถวใน `users` ทันทีแล้ว frontend เรียก Login ต่อ ตอนนี้ Register เก็บคำขอสมัครชั่วคราวและส่งรหัสก่อน เมื่อยืนยันถูกต้องจึงสร้าง `users` และ `refresh_tokens` ใน transaction เดียวกับการใช้รหัสและออก cookie หลัง commit สำเร็จ บัญชีที่ยังไม่ผ่าน OTP จึง Login ไม่ได้

หน้า `/register/otp` ใช้ `OtpVerify.jsx` ตัวเดียวกับหน้าลืมรหัสผ่าน แต่แยกข้อความ อีเมลที่รอยืนยัน API และหน้าปลายทาง เก็บเฉพาะ email/registration token ใน sessionStorage เพื่อกลับมากรอกต่อเมื่อ reload โดยไม่เก็บ password หรือ OTP

## เพิ่มอะไรใน DB

ตารางนี้เก็บ **คำขอสมัครที่ยังรอยืนยันอีเมล** เพื่อให้ระบบมีข้อมูลสำหรับตรวจ OTP ก่อนสร้างบัญชีจริงใน `users` ข้อมูลที่ต้องจำระหว่างสองขั้นตอน ได้แก่ อีเมล password hash รหัสอ้างอิงคำขอ OTP hash และข้อจำกัดการส่ง/กรอกผิด การเก็บใน DB ช่วยให้ข้อมูลเหล่านี้ยังอยู่เมื่อ reload หน้าเว็บหรือ restart backend และให้แต่ละคำขอใช้สถานะจำกัดร่วมกัน

การแยกตารางนี้ทำให้ Login และ endpoint ที่อาศัย `users` ไม่ต้องรองรับบัญชีที่ยังไม่ยืนยันใน flow ใหม่ ส่วน `password_reset_otps` มี `user_id` อ้างถึงบัญชีที่มีอยู่แล้วและมี reset ticket สำหรับเปลี่ยนรหัสผ่าน จึงแยกคำขอสมัครออกมาเพื่อคงความหมายและสิทธิ์ของสอง flow ให้ชัดเจน

ไม่มี FK จากคำขอสมัครไป `users` เพราะระหว่างรอยืนยันยังไม่มี user ให้เชื่อม การยืนยันสำเร็จจึงค่อยสร้าง user ไม่ได้แปลงแถวนี้ให้เป็น user โดยตรง รูปแบบนี้เป็นทางเลือกที่โค้ดปัจจุบันใช้ ไม่ใช่ข้อบังคับว่าทุกระบบ OTP ต้องมีตารางนี้เสมอ

เพิ่ม **1 ตาราง: `pending_registrations`** มี **12 คอลัมน์**:

| คอลัมน์ | ชนิด | หน้าที่ |
|---|---|---|
| `id` | INTEGER, primary key | เลขประจำคำขอ พร้อม sequence ที่ PostgreSQL สร้างให้ |
| `email` | VARCHAR(254), unique | อีเมลที่รอสมัคร; trim และแปลงตัวพิมพ์เล็กตามนโยบายเดิม หนึ่งอีเมลมีหนึ่งแถว |
| `hashed_password` | VARCHAR, nullable | รหัสผ่านที่ผ่าน bcrypt แล้ว ไม่เก็บค่าจริง |
| `registration_token_hash` | VARCHAR(64), unique | SHA-256 ของ token แบบสุ่มที่ใช้ระบุคำขอ ไม่เก็บ token จริงใน DB |
| `code_hash` | VARCHAR(64), nullable | HMAC-SHA256 ของ OTP ที่ผูกกับ token และวัตถุประสงค์สมัครสมาชิก |
| `attempts` | INTEGER, default 0 | จำนวนครั้งที่กรอกผิด สะสมต่ออีเมลในรอบจำกัด |
| `send_count` | INTEGER, default 0 | จำนวนอีเมลที่ส่งสำเร็จในรอบจำกัด |
| `window_started_at` | TIMESTAMP WITH TIME ZONE | จุดเริ่มรอบจำกัด 1 ชั่วโมง |
| `last_sent_at` | TIMESTAMP WITH TIME ZONE | เวลาส่งล่าสุด สำหรับ cooldown 60 วินาที |
| `expires_at` | TIMESTAMP WITH TIME ZONE | เวลาหมดอายุของ OTP |
| `consumed_at` | TIMESTAMP WITH TIME ZONE, nullable | เวลาที่ใช้คำขอนี้สร้างบัญชีสำเร็จ ป้องกันใช้ซ้ำ |
| `created_at` | TIMESTAMP WITH TIME ZONE, default now() | เวลาสร้างแถวครั้งแรก |

Unique constraints ของ `email` และ `registration_token_hash` มี unique indexes ตามกลไก PostgreSQL ไม่มี foreign key ไป `users` เพราะช่วงรอยืนยันยังไม่มีบัญชี เมื่อสำเร็จจะล้าง `hashed_password` และ `code_hash` ในแถวชั่วคราวเป็น NULL และเก็บ `consumed_at` ไว้

**ไม่ได้เพิ่มคอลัมน์ใน `users`, `refresh_tokens` หรือ `password_reset_otps`** และไม่ได้เปลี่ยนข้อมูลบัญชีเดิม หลัง migration ตรวจ schema เดิมและ fingerprint ของข้อมูลทั้งสามตารางกับ backup ก่อนเปลี่ยนแล้วตรงกัน ตารางใหม่ยังมี 0 แถวตอนตรวจ บัญชีเดิมใช้งานต่อได้ แต่ไม่ได้ถูกระบุย้อนหลังว่าเคยยืนยันอีเมล

แถวที่หมดอายุยังไม่ถูกลบอัตโนมัติ การสมัครใหม่หลังพ้นรอบจำกัดจะใช้แถวของอีเมลเดิมและแทนที่คำขอเก่า จึงต้องกำหนดนโยบาย retention/การล้างแถวที่เลิกใช้แยกต่างหากหากจะนำขึ้น production

## กติกาและการป้องกัน

- OTP 6 หลัก ใช้ครั้งเดียว อายุสูงสุด 10 นาที และคำขอมีขอบเขตรอบ 1 ชั่วโมง ส่งซ้ำต้องรอ 60 วินาที จำกัดส่งสำเร็จ 5 ครั้งและกรอกผิด 5 ครั้งต่ออีเมลต่อรอบ ส่งซ้ำหรือเริ่มสมัครใหม่ในรอบเดิมไม่ล้างจำนวนที่ผิด
- เริ่มสมัครใหม่จะเปลี่ยน token และ OTP พร้อมผูกกับ password hash ชุดใหม่ token เก่าจึงใช้กับข้อมูลใหม่ไม่ได้ หากส่งอีเมลไม่สำเร็จ transaction จะ rollback และคำขอเดิมยังใช้ต่อได้
- ใช้ PostgreSQL transaction advisory lock แบบ try-lock แยกตามอีเมล เพื่อให้คำขอซ้อนไม่รอ SMTP อย่างไม่มีกำหนด การยืนยันยังมี conditional UPDATE ป้องกันใช้รหัสซ้ำ และ unique email ป้องกันสร้างบัญชีซ้อน
- OTP สมัครสมาชิกแยกจาก password-reset OTP และไม่สามารถออก reset ticket ได้ ทั้งสอง flow ใช้ SMTP configuration เดิม ข้อความในอีเมลระบุวัตถุประสงค์ต่างกัน
- ใช้ same-origin guard เดิม ไม่เพิ่ม package, worker หรือบริการใหม่ในระบบจริง เมื่อ SMTP ใช้งานไม่ได้ ผู้สมัครใหม่ต้องลองส่งอีกครั้งก่อนเข้าใช้งาน

## API contract

ทุก POST ต้องผ่าน `verify_same_origin` ใช้ JSON และไม่ส่ง OTP กลับให้ frontend

| Endpoint | Request | ผลสำเร็จ |
|---|---|---|
| `POST /api/auth/register` | `{email, password}` | **202** `{status: "success", data: {registration_token, email}}`; ไม่มีบัญชี/session ใหม่และมี `Cache-Control: no-store` |
| `POST /api/auth/verify-registration` | `{registration_token, code}` | **200** `{status: "success", data: <user payload เดิม>}` พร้อม access/refresh cookies และ `Cache-Control: no-store` |
| `POST /api/auth/resend-registration` | `{registration_token}` | **200** `{status: "success"}` |

ข้อผิดพลาดใช้ `{detail: ...}`: 400 สำหรับอีเมล/รหัสผ่านไม่ผ่านเงื่อนไข อีเมลมีบัญชีแล้ว หรือ OTP ไม่ถูกต้อง/หมดอายุ; 403 สำหรับ origin ไม่ผ่าน; 422 สำหรับชนิด/รูปแบบ request ไม่ผ่าน schema; 429 สำหรับ cooldown/limit/คำขออีเมลเดียวกันกำลังทำงาน; 503 สำหรับความผิดพลาดส่งอีเมลหรือบันทึกข้อมูล โดยไม่เปิดเผยรายละเอียดภายใน

`registration_token` ยาว 40–100 ตัวอักษร; `code` ต้องเป็นเลข ASCII 6 หลัก; email ไม่เกิน 254 ตัวอักษร; password อย่างน้อย 8 ตัวอักษรและไม่เกิน 72 UTF-8 bytes ตามขอบเขต bcrypt เดิม ไม่มีการเปลี่ยน contract ของ Login/Reset Password

## หลักฐานและขอบเขตการตรวจ

- Backend regression ที่เกี่ยวข้อง 159/159 ผ่าน พร้อม offline network guard; PostgreSQL จริงใน container ทดสอบแยก 18/18 ผ่าน รวม migration และ race ของ Register/Verify
- Frontend auth/OTP/onboarding ที่เกี่ยวข้อง 25/25 ผ่าน; ตรวจหน้าจอสมัคร → รหัสผิด → ส่งซ้ำ → ยืนยัน → Onboarding และลืมรหัสผ่าน → OTP → ตั้งรหัสผ่านใหม่ ด้วย synthetic browser fixture
- Frontend ทั้งชุดผ่าน 174/178 ข้อ อีก 4 ข้อเป็น baseline เดิมเกี่ยวกับข้อความหน้า Cooking และ quantity ของวัตถุดิบ; scoped ESLint, production build และ Impeccable detector ผ่าน โดย build ยังมีคำเตือนขนาด bundle เดิม
- ตรวจ mobile 430×720 และ desktop 1280×800; ไม่พบ horizontal overflow ในหน้าที่ตรวจ มี screenshot/receipts ใน `tmp/registration-20261022/`
- เปิด preview ใหม่หลังแก้โค้ดแล้ว ตรวจทั้งสมัครและลืมรหัสผ่านได้ผลถูกต้องและ console errors เป็นรายการว่าง แยกจาก error ระหว่าง HMR ในแท็บเก่าที่เก็บไว้เป็นหลักฐาน
- ไม่ได้ทดสอบส่ง SMTP จริงหรือยืนยันบน iPhone จริง Backup ของ dev อยู่ `tmp/registration-20261022/development-before-registration.dump` และไม่ได้อยู่ใน commit
- Migration มีเพียง CREATE TABLE ใหม่; downgrade ถูกหยุดไว้เพื่อรักษาข้อมูลตามกฎไม่ลบของโปรเจกต์ หากต้องย้อน application สามารถคงตารางใหม่นี้ไว้ได้ การลบตารางต้องรีวิวแยก

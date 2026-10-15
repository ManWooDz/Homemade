# Login, Register และ Onboarding Quiz — ตรวจและปรับด้วย Impeccable

วันที่ 14 ตุลาคม 2026 (Asia/Bangkok). Operate-mode refinement ของหน้าเดิม: คงโลโก้ Noto Sans Thai กรอบ 430px และสีส้มของ HomeMade. งานนี้เป็น product envelope ไม่เพิ่ม contribution หรือ KPI ทางวิชาการ.

Follow-up ในวันเดียวกัน: ผู้ใช้ขอเว้นช่องว่างอายุ ย้าย error ลงใต้กลุ่มตัวเลือก และตรวจ Reset Password. รายละเอียดด้านล่างในหัวข้อ follow-up supersede ตำแหน่ง error ใน footer ที่บันทึกไว้ในรอบแรก.

## จุดที่พบและแก้

| ระดับ | จุดเดิมและผลกระทบ | การปรับ |
| --- | --- | --- |
| P1 | Quiz พาไป `/home` แม้ PUT preferences ล้มเหลว ผู้ใช้ไม่เห็น error ที่เพิ่งตั้งไว้ | รอผลบันทึกสำเร็จก่อนนำทาง; ล้มเหลวคงคำตอบและแสดง alert ใกล้ปุ่ม; retry ได้ |
| P1 | ช่องอีเมล/รหัสผ่านใช้ placeholder เป็นป้ายกำกับและไม่มี autocomplete ที่ระบุบทบาท | เพิ่ม label, id, name และ email/current-password/new-password; แสดงเงื่อนไข 8 ตัวอักษรเดิมก่อนกรอก |
| P1 | Age picker ไม่มีเส้นทางคีย์บอร์ด; ตัวเลือกไม่มี selected semantics | เพิ่ม spinbutton/ArrowUp/ArrowDown/Home/End ในช่วงเดิม 15–80 และ aria-pressed; โฟกัสหัวข้อเมื่อเปลี่ยนขั้น |
| P1 | สีส้มเดิมกับข้อความขาวขนาดเล็กมี contrast ไม่พอ | ใช้ส้มเข้มเฉพาะ `.auth-screen` #c94328 (4.86:1 กับขาว); ขอบควบคุม #8a8f99 (3.25:1); focus-visible; reduced motion |
| P2 | Register มีช่องว่างตายตัวประมาณ 96–98px; Quiz กันพื้นที่ใต้ปุ่ม 240px | ลดระยะให้เป็นกลุ่มเดียวกัน, h-dvh, เนื้อหาเลื่อนได้, footer ของ Quiz อยู่ล่างพร้อม safe-area และปุ่มข้อความชัดเจน |
| P2 | ตัวเลือกแบบ list ตัดข้อความยาวด้วย truncate | ให้ข้อความขึ้นบรรทัดได้และใช้ min-height; ตัวเลือกที่เลือกใช้สีพื้น/ขอบแทน halo |
| P2 | Login ไม่มีชื่อหน้าและลิงก์สมัครสมาชิกมีบริบทน้อย | เพิ่มหัวข้อและข้อความเชื่อมระหว่างเข้าสู่ระบบ/สมัครสมาชิก พร้อมเป้าหมายสัมผัส 44px |

รูปแบบเดิมที่เก็บไว้: โลโก้ ภาษาหลักไทย ฟอนต์และ layout มือถือ คำถามทั้งหก ขั้นบังคับเลือก รายการตัวเลือก/emoji เดิม การเลือกไม่มีข้อจำกัดแบบ exclusive ช่วงอายุและ drag/wheel ของ picker รวมถึง password-reset routes. ไม่ได้ตรวจ Figma ต้นฉบับหรือเปลี่ยน DESIGN.md.

## ขอบเขตโค้ดและผลข้างเคียง

- แก้ Login/Register/Onboarding และ CSS ที่ scope ด้วย `.auth-screen`; เพิ่มคำแปลไทย/อังกฤษใน catalog เดิมโดยรักษา WIP ที่มีอยู่.
- PasswordInput เพิ่มการส่งต่อ native input props และเป้าหมายปุ่มตา 44px; ResetPasswordConfirm ซึ่งใช้ component เดียวกันยังใช้ props เดิมได้.
- OptionPicker เพิ่ม aria-pressed/การ wrap/ซ่อน emoji จาก accessible name; หน้า Profile ได้การปรับ shared component เหล่านี้ด้วย. ไม่แก้ payload หรือหน้า Profile.
- BackButton เพิ่ม optional disabled ที่ default false; Onboarding ใช้เพื่อป้องกันการย้อนระหว่างบันทึก. Callers อื่นคง default เดิม.
- PUT `/api/user-preferences`, field names และ canonical Thai values เดิมทั้งหมด; ไม่มี external data-contract change. ไม่มี backend edit, package installation, deletion, commit หรือ push.
- เปลี่ยน behavior เมื่อบันทึกล้มเหลวอย่างตั้งใจ: ต้อง retry ให้สำเร็จก่อนจบ Quiz. Draft อยู่เฉพาะ memory ของหน้านี้; refresh/ออกจากหน้าอาจทำให้คำตอบหาย. ไม่เพิ่มการเก็บ allergies ใน localStorage.

## หลักฐานการตรวจ

- Targeted ESLint สำหรับสามหน้าและสาม shared components: exit 0.
- `node --test test/authOnboarding.test.js test/authValidation.test.js test/profileLanguage.test.js`: 17/17 ผ่าน. Regression tests รัน handler จริงที่ดึงจาก JSX ด้วย AST: HTTP/network failure, retry ด้วย payload เดิม, concurrent save, required/Other selections และ keyboard age bounds. Catalog coverage ทั้งสองภาษาผ่าน.
- Final `npm run build`: exit 0, 2,227 modules; warning bundle >500kB เดิมยังมี. ไม่มีการเพิ่ม dependency.
- Full frontend suite ก่อนเพิ่ม age check: 63/67 ผ่าน. สี่ข้อที่ล้มเหลวคือ Cooking Page servings/nutrition basis, Cooking Page reminder, fridge create excludes quantity และ Add Ingredient no stock amount. ไฟล์ source/test ที่สี่ข้อนี้อ้างไม่มี diff จาก HEAD; ไม่แก้ข้อเหล่านี้ในงานนี้.
- Browser: 320×568 และ 390×844, desktop 1366×900; intermediate 768×800 ตรวจ geometry. กรอบ 430px บนจอกว้าง, ไม่ล้นแนวนอนใน geometry checks; label left-aligned, button touch targets 44px. เดิน Quiz ครบหกขั้น, required selection/Other error, pending disables, failed-save answer retention, retry ไป home, back preserves cuisine, keyboard End=80; English long options ไม่ clipped. Login show-password/error, Register mismatch และ fixture duplicate-email error ยังรักษา input.
- QA fixture `frontend/test/authOnboarding.preview.html` บล็อก API ใน fresh document และมี DOM marker/request log. Final duplicate-email run ยืนยัน marker และ intercepted POST; English run ยืนยัน lang=en. Browser console ของ final isolated Login ไม่มี error. ไม่ได้ทดสอบบัญชี/session หรือ persistence กับ backend จริง, physical touch/IME, browser matrix หรือ screen reader จริง; ไม่ใช่ WCAG certification.
- รอบแรก Vite reload ทำให้ fixture ที่เปลี่ยน URL เป็น application route หลุด interception. Dev-server log ยืนยัน register proxy หนึ่งครั้งล้มเหลว ECONNREFUSED 127.0.0.1:8000; ไม่มี backend listening ในครั้งนั้น. ผล generic error ไม่นับเป็น duplicate-email fixture evidence. เปิด fresh fixture และยืนยัน DOM marker ก่อนทดสอบซ้ำ; snapshot ที่เก่ากว่าหน้าปัจจุบันไม่นำมาใช้เป็นภาพ final.
- `git diff --check` ผ่าน; hash ของ initial unrelated dirty files ตรงทั้งหมด (ยกเว้นไฟล์ CSS/translations/spec/MEMORY ที่อยู่ในขอบเขต). Backend WIP คงเดิม.

Logs และภาพอยู่ `tmp/auth-onboarding-20261014/`: targeted-tests.log, all-tests.log, lint.log, build.log, before-hashes.json และภาพ `*-final.jpg`. Fixture เป็น QA เท่านั้นและติด deprecated ตามกฎห้ามลบไฟล์; production build ใช้ index.html เดิม.

ขั้นถัดไป: ทีมลอง flow กับ backend/session จริงเมื่อพร้อม และแยกแก้สี่ regression mismatches ของสูตรอาหาร/ตู้เย็นในงานของส่วนนั้น.

## Follow-up — Onboarding และ Reset Password

- Onboarding แสดง `25 ปี`/`25 years`; ย้าย alert จาก footer ไปท้ายกลุ่มตัวเลือกหรือหลังช่อง Other. Fieldset เชื่อมกับ alert ผ่าน aria-describedby; scrollIntoView แบบ nearest ทำให้ข้อความอยู่ในพื้นที่อ่านบนจอเล็ก. Validation/save/retry และ payload เดิมคงอยู่.
- ResetPasswordEmail/OtpVerify/ResetPasswordConfirm ใช้ `.auth-screen` และ h-dvh เดิมจากรอบแรก, padding 24px, ระยะหัวข้อ/ฟอร์ม 24px, BackButton 44px, main landmarks และ role=alert. Email/new-password inputs มี label/name/autocomplete; เงื่อนไขรหัสผ่าน 8 ตัวอักษรเป็นกฎเดิม.
- P1 ที่แก้: OTP เดิมมีหกช่องไม่ติด label และกลุ่มกว้าง 280px เทียบพื้นที่ฟอร์ม 240.8px บนจอ 320px; แต่ละช่องรับได้หนึ่งตัวอักษรและไม่มี whole-code paste/autofill path. เปลี่ยนเป็นช่อง native เดียว, numeric keyboard, one-time-code, pattern หกเลข ASCII, รับ paste ทั้งชุดพร้อม normalize/เก็บศูนย์นำหน้า. ไม่มีการปรับ backend code/ticket/auth validation.
- P2 ที่แก้: ช่องว่างตายตัว 96px ก่อนฟอร์ม/ปุ่ม OTP ทำให้ต้องเลื่อนมาก; ปรับเป็นระยะเดียวกับ Register. เพิ่มอีเมลปลายทางที่ผู้ใช้กรอกแบบ break-words และ helper ที่บอกขั้นตอนชัดเจน โดยไม่อ้างว่าส่งอีเมลสำเร็จแล้ว.
- ตรวจพบและแก้ระหว่าง inspection: ส่ง OTP ใหม่แล้ว focus เดิมถูกเรียกขณะ input ยัง disabled. เลื่อน focus ไป requestAnimationFrame หลังจบ busy state; browser ยืนยัน activeElement.id=otp-code. Verify/resend ป้องกันการเริ่มซ้อนกัน, confirm ป้องกัน submit ซ้ำและล็อก fields/back ระหว่างบันทึก.
- คง `void requestOtp(email)` เพื่อเปิด OTP โดยไม่รอ SMTP, cooldown 60 วินาที, resetTicket-at-mount guard และ success notice ที่ Login. API field/endpoint และ six-digit string contract เดิมทั้งหมด; ไม่มี external data-contract change. ข้อจำกัดเดิม: ผลล้มเหลวของคำขอส่งรหัสครั้งแรกยังไม่ส่งกลับมาแสดงในหน้า OTP; ผู้ใช้ใช้เส้นทางส่งใหม่หลัง cooldown. ไม่เพิ่มสถานะใหม่ใน AuthContext ในงาน UI นี้.

### Verification ของ follow-up

- Targeted ESLint สี่หน้าที่แก้ exit0; 27/27 tests ผ่าน: auth/onboarding/locale/OTP-request plus seven new actual AST-extracted reset handlers. ครอบคลุม paste normalization/leading zeros, malformed/short code, pending guards, verify success/error, resend success/error/cooldown และ confirm success/error/pending.
- Final production build 2,227 modules, exit0; warning >500kB เดิมยังอยู่. ไม่รัน full frontend suite หรือ full-repo lint ซ้ำ; สี่ mismatches ในส่วนอื่นที่บันทึกจากรอบก่อนยังแยกไว้นอกงานนี้.
- Browser fixture บล็อกทุก API จริงและตรวจ DOM marker ก่อน submit. เดิน email → OTP → confirm → Login, invalid OTP/retry, paste รหัสที่มีช่องว่าง, cooldown จริง → resend → clear code/reset countdown, mismatch/failed reset/retry/success notice; ตรวจ pending disabled states. ข้อมูลทั้งหมดเป็น synthetic QA; ไม่มีการส่ง SMTP หรือเปลี่ยน credential จริง.
- Captures/geometry ที่ 320×568,390×844,1366×900: OTP controls อย่างน้อย44px, single input56px, ไม่มี horizontal overflow, long email wrap; Quiz alert อยู่ใน main หลัง choices และพ้น footer. Geometry ใช้ tolerance1px สำหรับ browser fractional rounding (ครั้งหนึ่งต่าง0.2px). Current fresh reset fixture ไม่มี console error; log HMR LocaleProvider เก่าถูกแยกจากผล fresh document.
- Browser ใช้ masked credential DOM จึงตรวจ enabled/focus/navigation/alerts แทนการเปรียบเทียบ OTP/password value ที่ถูก redact. ความถูกต้องของ string ทดสอบด้วย handler unit tests; ไม่มีการพยายามอ่านค่าที่ถูก mask. Fixture HTML ติด deprecated/ห้าม deploy เช่นเดิมตาม AGENTS.md.
- Logs, browser assertions, source hashes และ final captures: `tmp/reset-password-20261014/`. Hash ของ unrelated prior dirty files ตรง; ไม่มี backend/AuthContext/shared-component/package/delete/commit/push edits ใน follow-up.

ยังไม่ตรวจ SMTP/session/credential persistence จริง, physical mobile keyboard/SMS autofill, browser matrix หรือ screen reader จริง. ขั้นถัดไปคือ live integration check เมื่อทีมเปิด backend พร้อม ไม่ใช่หลักฐาน security/WCAG certification.

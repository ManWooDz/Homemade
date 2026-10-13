import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";
import { COPY, translate } from "../src/utils/translations.js";
import { isValidDisplayName, profileImageError, profileErrorKey, cropAvatar } from "../src/utils/profileValidation.js";
import { toUserFacingGenerateError } from "../src/utils/generateError.js";
import { expiryBadgeLabel } from "../src/utils/expiry.js";
import { ALLERGY_OPTIONS } from "../src/constants/preferenceOptions.js";

test("Unicode names count code points and reject blank/control/overlong values", () => {
    for (const name of [" เชฟไทย ", "😀".repeat(50)]) assert.equal(isValidDisplayName(name), true);
    for (const name of [" ", "😀".repeat(51), "chef\0", "a\nb", "a\u0085b"]) assert.equal(isValidDisplayName(name), false);
});

test("picture checks reject unsupported types and oversize uploads with safe messages", () => {
    assert.equal(profileImageError({ type: "image/jpeg", size: 5 * 1024 * 1024 }), null);
    assert.equal(profileImageError({ type: "image/png", size: 5 * 1024 * 1024 + 1 }), "profile_image_too_large");
    assert.equal(profileImageError({ type: "image/svg+xml", size: 1 }), "profile_image_invalid");
    assert.equal(profileErrorKey("database password leaked"), "บันทึกโปรไฟล์ไม่สำเร็จ กรุณาลองอีกครั้ง");
    for (const code of ["__proto__", "constructor", "toString"]) assert.equal(profileErrorKey(code), "บันทึกโปรไฟล์ไม่สำเร็จ กรุณาลองอีกครั้ง");
});

test("both locales translate UI without changing Thai recipe/user content or allergy values", () => {
    assert.equal(translate("Language", "th"), "ภาษา");
    assert.equal(translate("สร้างเมนูอาหารกันเลย", "en"), "Generate a recipe");
    assert.equal(translate("ไข่เจียวของฉัน 🌶️", "en"), "ไข่เจียวของฉัน 🌶️");
    const original = [...ALLERGY_OPTIONS];
    const labels = ALLERGY_OPTIONS.map(value => translate(value, "en"));
    assert.equal(labels[original.indexOf("แพ้งา")], "Sesame allergy");
    assert.deepEqual(ALLERGY_OPTIONS, original);
    assert.equal(translate("กำลังค้นหาสินค้าจากบาร์โค้ด {barcode}", "en", { barcode: "00123456" }), "Looking up barcode 00123456");
});

test("English generation errors stay safe and actionable while Thai behavior remains", () => {
    const kg = "ระบบตรวจสอบสารก่อภูมิแพ้ยังไม่พร้อม จึงยังสร้างสูตรไม่ได้ กรุณาลองใหม่ภายหลัง";
    assert.equal(toUserFacingGenerateError(kg), kg);
    assert.equal(toUserFacingGenerateError(kg, "en"), "Allergy validation is unavailable. Please try again later.");
    assert.match(toUserFacingGenerateError("ไม่สามารถสร้างสูตรได้ เพราะมีวัตถุดิบที่ขัดกับอาการแพ้ของคุณ: ซีอิ๊ว", "en"), /conflict with your allergies/);
    assert.doesNotMatch(toUserFacingGenerateError("ข้อผิดพลาด secret provider exception", "en"), /secret|provider|ข้อ/);
    assert.equal(toUserFacingGenerateError("API Key missing secret", "en"), null);
});

test("expiry badges use the active locale without changing sort/date values", () => {
    assert.equal(expiryBadgeLabel("2000-01-01", "en"), "Expired");
    assert.equal(expiryBadgeLabel("2000-01-01"), "หมดอายุแล้ว");
    assert.equal(expiryBadgeLabel(null, "en"), null);
});

test("crop export uses the chosen source region, square output and a white background", async () => {
    const calls = [];
    const context = { fillRect: (...args) => calls.push(["fill", ...args]), drawImage: (...args) => calls.push(["draw", ...args]) };
    const canvas = { getContext: () => context, toBlob: callback => callback(new Blob(["image"], { type: "image/jpeg" })) };
    const originalDocument = globalThis.document;
    globalThis.document = { createElement: () => canvas };
    try {
        const image = { naturalWidth: 800, naturalHeight: 600 };
        const blob = await cropAvatar(image, { x: 100, y: 50, width: 400, height: 400 });
        assert.equal(blob.type, "image/jpeg");
        assert.equal(canvas.width, 512);
        assert.equal(canvas.height, 512);
        assert.equal(context.fillStyle, "white");
        assert.deepEqual(calls[1], ["draw", image, 100, 50, 400, 400, 0, 0, 512, 512]);
        for (const area of [{ x: -1, y: 0, width: 10, height: 10 }, { x: 700, y: 0, width: 200, height: 200 }, { x: 0, y: 0, width: 20, height: 10 }]) await assert.rejects(cropAvatar(image, area), /Invalid crop/);
    } finally { globalThis.document = originalDocument; }
});

test("every static translation call in shipped source has both language entries", () => {
    const parse = createRequire(import.meta.url)("@babel/parser").parse;
    const known = new Set(COPY.flat());
    const files = [];
    function findFiles(directory) {
        for (const entry of readdirSync(directory, { withFileTypes: true })) {
            const url = new URL(entry.name + (entry.isDirectory() ? "/" : ""), directory);
            if (entry.isDirectory() && entry.name !== "pages_v2") findFiles(url);
            else if (/\.[jt]sx?$/.test(entry.name)) files.push(url);
        }
    }
    findFiles(new URL("../src/", import.meta.url));
    function walk(node) {
        if (!node || typeof node !== "object") return;
        if (node.type === "CallExpression" && node.callee.name === "t" && node.arguments[0]?.type === "StringLiteral") assert.ok(known.has(node.arguments[0].value), `Missing translation: ${node.arguments[0].value}`);
        for (const [key, child] of Object.entries(node)) {
            if (["loc", "extra", "comments"].includes(key)) continue;
            if (Array.isArray(child)) child.forEach(walk);
            else if (child && typeof child === "object") walk(child);
        }
    }
    files.forEach(file => walk(parse(readFileSync(file, "utf8"), { sourceType: "module", plugins: ["jsx"] })));
});

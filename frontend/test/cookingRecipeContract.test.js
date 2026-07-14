import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(
  new URL("../src/pages/CookingPage.jsx", import.meta.url),
  "utf8",
);

test("Cooking Page displays servings and nutrition basis", () => {
  assert.match(source, /generatedRecipe\.servings/);
  assert.match(source, /generatedRecipe\.nutrition\.basis/);
  assert.match(source, /สำหรับ \{generatedRecipe\.servings\} ที่/);
  assert.match(source, /"โภชนาการต่อ 1 ที่ \(คาดการณ์\)"/);
  assert.match(source, /"โภชนาการที่คาดการณ์"/);
  assert.match(source, /\? "แคลอรี่ต่อ 1 ที่"/);
  assert.match(source, /: "แคลอรี่"/);
});

test("Cooking Page shows the approved general reminder", () => {
  assert.match(
    source,
    /ตรวจสอบวัตถุดิบและปริมาณจริงก่อนเริ่มทำอาหาร/,
  );
});

test("Cooking Page makes no shortage or purchase claim", () => {
  assert.doesNotMatch(source, /วัตถุดิบไม่พอ|ต้องซื้อเพิ่ม/);
});

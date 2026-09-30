import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
const cookingPage = readFileSync(
    new URL("../src/pages/CookingPage.jsx", import.meta.url),
    "utf8",
);

test("both generate handlers clear and set the backend error message", () => {
    assert.equal((app.match(/setGenerateError\(null\)/g) || []).length, 2);
    assert.equal(
        (app.match(/setGenerateError\(result\.message\)/g) || []).length,
        2,
    );
    assert.match(app, /generateError=\{generateError\}/);
});

test("CookingPage renders the backend message as plain text under the heading", () => {
    assert.match(cookingPage, /เกิดข้อผิดพลาดในการสร้างสูตรอาหาร/);
    assert.match(cookingPage, /\{generateError\}/);
    assert.doesNotMatch(cookingPage, /dangerouslySetInnerHTML/);
});

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { toUserFacingGenerateError } from "../src/utils/generateError.js";

const app = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
const cookingPage = readFileSync(
    new URL("../src/pages/CookingPage.jsx", import.meta.url),
    "utf8",
);

test("Thai backend message is kept as-is", () => {
    const msg =
        "ไม่สามารถสร้างสูตรได้ เพราะมีวัตถุดิบที่ขัดกับอาการแพ้ของคุณ: ซีอิ๊วขาว (มีแป้งสาลี) กรุณาลองเอาออกแล้วสร้างใหม่";
    assert.equal(toUserFacingGenerateError(msg), msg);
});

test("English / dev messages are dropped", () => {
    assert.equal(
        toUserFacingGenerateError("API Key is missing. Please check your .env file."),
        null,
    );
    assert.equal(toUserFacingGenerateError("Ingredient name is required"), null);
    assert.equal(toUserFacingGenerateError("'recipe_name'"), null);
});

test("mixed Thai + ASCII message is kept", () => {
    const msg = "ไม่พบวัตถุดิบ oyster sauce ในระบบ";
    assert.equal(toUserFacingGenerateError(msg), msg);
});

test("empty, missing and non-string messages give null", () => {
    for (const value of ["", undefined, null, 42, {}, ["ไทย"], true]) {
        assert.equal(toUserFacingGenerateError(value), null);
    }
});

test("both generate handlers route the message through the helper", () => {
    assert.equal((app.match(/setGenerateError\(null\)/g) || []).length, 2);
    assert.equal(
        (app.match(/setGenerateError\(toUserFacingGenerateError\(result\.message\)\)/g) || []).length,
        2,
    );
    assert.match(app, /generateError=\{generateError\}/);
});

test("CookingPage renders the message as plain, wrapping text", () => {
    assert.match(cookingPage, /\{generateError\}/);
    assert.match(cookingPage, /break-words/);
    assert.doesNotMatch(cookingPage, /dangerouslySetInnerHTML/);
});

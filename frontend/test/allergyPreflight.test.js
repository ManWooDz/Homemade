import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { toUserFacingGenerateError, validateAllergyPreferences } from "../src/utils/generateError.js";

const response = (payload, ok = true) => ({ ok, json: async () => payload });

test("KG unavailability stays actionable Thai copy in both generation handlers", () => {
    const message = "ระบบตรวจสอบสารก่อภูมิแพ้ยังไม่พร้อม จึงยังสร้างสูตรไม่ได้ กรุณาลองใหม่ภายหลัง";
    assert.equal(toUserFacingGenerateError(message), message);
    const app = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
    for (const handler of app.split("onGenerate={async ").slice(1)) {
        assert.match(handler, /toUserFacingGenerateError\(result.message, locale\)/);
    }
});

test("valid preferences use the pure preflight with the original frontend shape", async () => {
    const preferences = { allergies: "แพ้งา", taste: "", equipment: "", extra: "" };
    let calls = 0;
    const apiFetch = async (url, options) => {
        calls++;
        assert.equal(url, "/api/validate-allergy-preferences");
        assert.equal(options.method, "POST");
        assert.deepEqual(JSON.parse(options.body), { preferences });
        return response({ status: "success" });
    };
    assert.equal(await validateAllergyPreferences(apiFetch, preferences), null);
    assert.equal(calls, 1);
});

test("ambiguous input gets actionable Thai copy without exposing the raw message", async () => {
    const error = await validateAllergyPreferences(async () => response({
        status: "error", code: "allergy_preferences_ambiguous", message: "secret exception",
    }), { allergies: "ลดแป้ง" });
    assert.match(error, /กรุณาระบุอาหารที่แพ้/);
    assert.doesNotMatch(error, /secret/);
});

test("HTTP errors, bad payloads, JSON errors and network failures fail closed", async () => {
    for (const apiFetch of [
        async () => response({ status: "success" }, false),
        async () => response({}),
        async () => ({ ok: true, json: async () => { throw new Error("raw parser"); } }),
        async () => { throw new Error("raw network"); },
    ]) {
        const error = await validateAllergyPreferences(apiFetch, { allergies: "แพ้นม" });
        assert.match(error, /ตรวจสอบอาการแพ้ไม่ได้/);
        assert.doesNotMatch(error, /raw/);
    }
});

test("both App handlers validate before changing view or calling the generator", () => {
    const app = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
    const handlers = app.split("onGenerate={async ").slice(1);
    assert.equal(handlers.length, 2);
    for (const handler of handlers) {
        const guard = handler.indexOf("if (preferenceError) return preferenceError;");
        assert.ok(guard > handler.indexOf("await validateAllergyPreferences(apiFetch, preferences)"));
        assert.ok(handler.indexOf('setCurrentView("cooking-page")') > guard);
        assert.ok(handler.indexOf('apiFetch("/api/generate-recipe-text"') > guard);
    }
});

test("both forms preserve editable state, announce errors and prevent double submit", () => {
    for (const page of ["CreateRecipe", "CustomCookingPage"]) {
        const source = readFileSync(new URL(`../src/pages/${page}.jsx`, import.meta.url), "utf8");
        assert.match(source, /await onGenerate\(/);
        assert.match(source, /if \(submitting.current/);
        assert.match(source, /disabled=\{[^}]*isSubmitting/);
        assert.match(source, /allergyError=\{allergyError\} allergyInput=\{allergyInput\}/);
        const fields = readFileSync(new URL("../src/components/CookingPreferenceFields.jsx", import.meta.url), "utf8");
        assert.match(fields, /aria-invalid=\{group.key === "allergies" && Boolean\(allergyError\)\}/);
        assert.match(fields, /aria-describedby=\{group.key === "allergies" && allergyError \? "allergy-error"/);
        assert.match(source, /id="allergy-error" role="alert"/);
        assert.match(source, /allergyInput.current\?\.focus\(\)/);
        assert.doesNotMatch(source, /dangerouslySetInnerHTML/);
    }
});

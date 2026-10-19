import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { setImmediate } from "node:timers";
import { ALLERGY_OPTIONS, ALLERGY_NONE, DIETARY_NONE, OTHER_OPTION, EQUIPMENT_NONE, TASTE_OPTIONS } from "../src/constants/preferenceOptions.js";
import { emptyCookingPreferences, readCookingPreferences, serializeCookingPreferences, classifyRestriction, toggleCookingChoice, cookingPreferenceError, generationPreferences, loadCookingPreferences, mergeUntouchedPreferences, orderedPreferenceSaver } from "../src/utils/cookingPreferences.js";
import { translate } from "../src/utils/translations.js";

test("all ten groups round-trip and stay distinct from dietary guidance and taste", () => {
    const allergies = ALLERGY_OPTIONS.filter(value => ![OTHER_OPTION, ALLERGY_NONE].includes(value));
    assert.equal(allergies.length, 10);
    const model = readCookingPreferences({ dietary_restrictions: [...allergies, "ทาน Vegan"], equipment: ["กระทะ", "หม้อ", "เตาไฟฟ้า", "เตาแก๊ส"] });
    assert.deepEqual(readCookingPreferences(serializeCookingPreferences(model)), model);
    const request = generationPreferences(model, "ไม่เผ็ด", "ใช้เวลาไม่เกินครึ่งชั่วโมง");
    assert.equal(request.allergies, allergies.join(", "));
    assert.equal(request.equipment, "กระทะ, หม้อ, เตาไฟฟ้า, เตาแก๊ส");
    assert.equal(request.extra, "ข้อจำกัดในการกิน: ทาน Vegan\nใช้เวลาไม่เกินครึ่งชั่วโมง");
    assert.deepEqual(Object.keys(request), ["taste", "allergies", "equipment", "extra"]);
    for (const value of [...ALLERGY_OPTIONS, "ข้อจำกัดในการกิน", "ไม่เผ็ด"]) assert.notEqual(translate(value, "en"), value);
    for (const value of ["ไม่ระบุ", "ไม่เผ็ด", "เผ็ดน้อย"]) assert.ok(TASTE_OPTIONS.includes(value));
});

test("legacy peanut and seafood keep their implemented meaning without implying tree nuts", () => {
    const model = readCookingPreferences({ dietary_restrictions: ["แพ้ถั่ว", "แพ้อาหารทะเล", "แพ้ปลา"], equipment: ["กระทะ/เตาแก๊สทั่วไป"] });
    assert.deepEqual(model.allergies, ["แพ้ถั่วลิสง", "แพ้กุ้ง", "แพ้ปู/หอย", "แพ้ปลา"]);
    assert.deepEqual(model.equipment, ["กระทะ", "เตาแก๊ส"]);
    assert.deepEqual(model.unclassified, []);
});

test("multiple unknowns require classification; custom category/text survive reload exactly", () => {
    const values = ["แพ้กีวี 🥝\nและผลไม้อื่น", "ไม่กินเนื้อวัว, เนื้อแกะ"];
    let model = readCookingPreferences({ dietary_restrictions: values, equipment: ["ตะหลิว", "ซึ้งนึ่ง"] });
    assert.deepEqual(model.unclassified, values);
    assert.ok(cookingPreferenceError(model));
    assert.deepEqual(serializeCookingPreferences(model).dietary_restrictions, values);
    model = classifyRestriction(model, 0, "allergy");
    model = classifyRestriction(model, 0, "dietary");
    assert.equal(cookingPreferenceError(model), null);
    assert.deepEqual(readCookingPreferences(serializeCookingPreferences(model)), model);
    const request = generationPreferences(model, "", "extra");
    assert.equal(request.allergies, values[0]);
    assert.equal(request.extra, "ข้อจำกัดในการกิน: " + values[1] + "\nextra");
    assert.equal(request.equipment, "ตะหลิว, ซึ้งนึ่ง");
    assert.doesNotMatch(JSON.stringify(request), /homemade:preference/);
    const invalid = "homemade:preference:v1:{broken";
    assert.deepEqual(readCookingPreferences({ dietary_restrictions: [invalid] }).unclassified, [invalid]);
    assert.deepEqual(readCookingPreferences({ dietary_restrictions: ["constructor", "__proto__", "toString"] }).unclassified, ["constructor", "__proto__", "toString"]);
});

test("no allergy is compatible with Vegan; each None is exclusive only in its own group", () => {
    let model = readCookingPreferences({ dietary_restrictions: [ALLERGY_NONE, "ทาน Vegan"], equipment: [EQUIPMENT_NONE] });
    assert.deepEqual(model.allergies, [ALLERGY_NONE]);
    assert.deepEqual(model.dietary, ["ทาน Vegan"]);
    model = toggleCookingChoice(model, "allergies", "แพ้นม / ผลิตภัณฑ์จากนม", ALLERGY_NONE, "allergyOther");
    assert.deepEqual(model.allergies, ["แพ้นม / ผลิตภัณฑ์จากนม"]);
    assert.deepEqual(model.dietary, ["ทาน Vegan"]);
    model = toggleCookingChoice(model, "allergies", ALLERGY_NONE, ALLERGY_NONE, "allergyOther");
    assert.deepEqual(model.allergies, [ALLERGY_NONE]);
    const empty = readCookingPreferences({});
    assert.deepEqual(empty.allergies, []);
    assert.deepEqual(readCookingPreferences({ dietary_restrictions: ["ไม่มีข้อจำกัด"] }).dietary, [DIETARY_NONE]);
});

test("new Other stays editable and requires text; account roundtrip strips UI sentinels", () => {
    let model = toggleCookingChoice(emptyCookingPreferences(), "allergies", OTHER_OPTION, ALLERGY_NONE, "allergyOther");
    assert.ok(cookingPreferenceError(model));
    model = { ...model, allergyOther: ["แพ้กีวี"] };
    assert.equal(cookingPreferenceError(model), null);
    assert.ok(readCookingPreferences(serializeCookingPreferences(model)).allergies.includes(OTHER_OPTION));
    assert.deepEqual(model.allergyOther, ["แพ้กีวี"]);
    const legacyEmpty = classifyRestriction(readCookingPreferences({ dietary_restrictions: [OTHER_OPTION] }), 0, "allergy");
    assert.ok(cookingPreferenceError(legacyEmpty));
});

test("late defaults and retries preserve deliberately cleared choices and typed text", () => {
    const loaded = readCookingPreferences({ dietary_restrictions: ["แพ้ไข่", "แพ้กีวี", "ทาน Vegan"], equipment: ["หม้อ"] });
    const current = { ...emptyCookingPreferences(), allergies: [], allergyOther: ["typed"], equipment: [EQUIPMENT_NONE] };
    const result = mergeUntouchedPreferences(current, loaded, new Set(["allergies", "allergyOther", "equipment"]));
    assert.deepEqual(result.allergies, []);
    assert.deepEqual(result.allergyOther, ["typed"]);
    assert.deepEqual(result.equipment, [EQUIPMENT_NONE]);
    assert.deepEqual(result.dietary, ["ทาน Vegan"]);
    assert.deepEqual(result.unclassified, ["แพ้กีวี"]);
    assert.deepEqual(loaded.allergies, ["แพ้ไข่"]);
});

test("successful empty account is distinct from transport, HTTP, JSON and payload errors", async () => {
    assert.deepEqual(await loadCookingPreferences(async () => ({ ok: true, json: async () => ({ data: null }) })), {});
    for (const fetch of [async () => { throw Error("offline"); }, async () => ({ ok: false }), async () => ({ ok: true, json: async () => { throw Error("JSON"); } }), async () => ({ ok: true, json: async () => ({}) }), async () => ({ ok: true, json: async () => ({ data: [] }) }), async () => ({ ok: true, json: async () => ({ data: { equipment: "bad" } }) }), async () => ({ ok: true, json: async () => ({ status: "error", data: null }) })]) {
        await assert.rejects(loadCookingPreferences(fetch));
    }
});

test("Profile snapshots save in order even after failure, with no concurrent stale writes", async () => {
    const releases = [], calls = [];
    const save = orderedPreferenceSaver(async (url, options) => {
        calls.push({ url, body: JSON.parse(options.body) });
        return new Promise(resolve => releases.push(resolve));
    });
    const first = save({ equipment: ["กระทะ"] });
    const failed = assert.rejects(first);
    const body = { equipment: ["กระทะ", "หม้อ"] };
    const second = save(body);
    body.equipment.push("mutated later");
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(calls.length, 1);
    releases.shift()({ ok: false });
    await failed;
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(calls.length, 2);
    assert.deepEqual(calls[1].body.equipment, ["กระทะ", "หม้อ"]);
    releases.shift()({ ok: true });
    await second;
});

const parse = createRequire(import.meta.url)("@babel/parser").parse;
for (const page of ["CreateRecipe", "CustomCookingPage"]) {
    test(`${page} blocks until defaults/classification are ready and sends only request overrides`, async () => {
        const source = readFileSync(new URL(`../src/pages/${page}.jsx`, import.meta.url), "utf8");
        const component = parse(source, { sourceType: "module", plugins: ["jsx"] }).program.body.find(node => node.type === "ExportDefaultDeclaration").declaration;
        const handler = component.body.body.flatMap(node => node.declarations || []).find(node => node.id.name === "handleGenerateClick").init;
        const account = readCookingPreferences({ dietary_restrictions: ["แพ้ไข่", "ทาน Vegan"], equipment: ["หม้อ"] });
        for (const [status, issue, count] of [["loading", null, 0], ["error", null, 0], ["ready", "unclassified", 0], ["ready", null, 1]]) {
            const calls = [];
            const context = { submitting: { current: false }, preferences: { status, value: { ...account, allergies: [ALLERGY_NONE] } }, preferenceIssue: issue,
                selectedIngredients: [1], userIngredients: [{ id: 1, name: "ผัก" }], currentIngredients: [{ id: 1, name: "ผัก" }],
                setIsSubmitting: () => {}, setAllergyError: () => {}, allergyInput: { current: null }, onGenerate: async (...args) => { calls.push(args); return null; },
                taste: "ไม่เผ็ด", tasteOther: "", extra: "note", OTHER_OPTION, generationPreferences };
            await new Function(...Object.keys(context), `return ${source.slice(handler.start, handler.end)}`)(...Object.values(context))();
            assert.equal(calls.length, count);
            if (count) { assert.equal(calls[0][0].allergies, ALLERGY_NONE); assert.match(calls[0][0].extra, /Vegan/); }
            assert.deepEqual(account.allergies, ["แพ้ไข่"]);
        }
    });
}

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { OTHER_OPTION, toggleInList, NO_RESTRICTION } from "../src/constants/preferenceOptions.js";
import { emptyCookingPreferences, serializeCookingPreferences, cookingPreferenceError } from "../src/utils/cookingPreferences.js";

const parse = createRequire(import.meta.url)("@babel/parser").parse;
const source = readFileSync(new URL("../src/pages/auth/Onboarding.jsx", import.meta.url), "utf8");
const ast = parse(source, { sourceType: "module", plugins: ["jsx"] });
const component = ast.program.body.find(node => node.type === "ExportDefaultDeclaration").declaration;
const handler = component.body.body.flatMap(node => node.declarations || []).find(node => node.id.name === "handleNext").init;

function setup(apiFetch, overrides = {}) {
    const calls = [], errors = [], loading = [], steps = [];
    const context = {
        step: 6, pickerValue: { age: "25" }, cuisinePreferences: ["อาหารไทย"],
        preferences: { ...emptyCookingPreferences(), allergies: ["แพ้งา", OTHER_OPTION], allergyOther: ["ข้อจำกัดทดสอบ"], dietary: ["ไม่มีข้อจำกัดในการกิน"] },
        serializeCookingPreferences, cookingPreferenceError,
        equipment: [OTHER_OPTION], equipmentOther: "อุปกรณ์ทดสอบ", cookingFrequency: "ทำอาหารทุกวัน — 7 ครั้งขึ้นไป/สัปดาห์",
        cookingGoals: ["ประหยัดเวลา"], savePending: { current: false },
        OTHER_OPTION, SELECT_ONE_ERROR: "กรุณาเลือกอย่างน้อย 1 ตัวเลือก",
        setStepError: value => errors.push(value), setIsSaving: value => loading.push(value),
        setStep: value => steps.push(value), setRestrictionShakeKey: () => {}, setEquipmentShakeKey: () => {},
        navigate: (...args) => calls.push(args), apiFetch, console: { error: () => {} }, ...overrides,
    };
    const next = new Function(...Object.keys(context), `return ${source.slice(handler.start, handler.end)}`)(...Object.values(context));
    return { next, context, calls, errors, loading, steps };
}

test("failed saves retain the final step and can be retried with the original contract", async () => {
    const requests = [];
    const state = setup(async (url, options) => { requests.push({ url, options }); return { ok: requests.length > 1 }; });
    await state.next();
    assert.deepEqual(state.calls, []);
    assert.match(state.errors.at(-1), /คำตอบยังอยู่/);
    assert.equal(state.context.savePending.current, false);
    await state.next();
    assert.deepEqual(state.calls, [["/home", { replace: true }]]);
    assert.deepEqual(state.loading, [true, false, true, false]);
    assert.equal(requests[0].url, "/api/user-preferences");
    assert.equal(requests[0].options.method, "PUT");
    assert.deepEqual(JSON.parse(requests[0].options.body), {
        age: 25, cuisine_preferences: ["อาหารไทย"], dietary_restrictions: ["แพ้งา", "ไม่มีข้อจำกัดในการกิน", 'homemade:preference:v1:{"kind":"allergy","text":"ข้อจำกัดทดสอบ"}'],
        equipment: ["อุปกรณ์ทดสอบ"], cooking_frequency: state.context.cookingFrequency, cooking_goals: ["ประหยัดเวลา"],
    });
    assert.equal(requests[0].options.body, requests[1].options.body);
});

test("network failure stays recoverable and concurrent next calls save once", async () => {
    let rejectSave, requests = 0;
    const state = setup(() => { requests++; return new Promise((_, reject) => { rejectSave = reject; }); });
    const pending = state.next();
    await state.next();
    assert.equal(requests, 1);
    assert.equal(state.context.savePending.current, true);
    rejectSave(new Error("offline"));
    await pending;
    assert.deepEqual(state.calls, []);
    assert.match(state.errors.at(-1), /ลองอีกครั้ง/);
    assert.deepEqual(state.loading, [true, false]);
});

test("required selections and Other details block advancement before any save", async () => {
    for (const overrides of [
        { step: 2, cuisinePreferences: [] }, { step: 3, preferences: emptyCookingPreferences() },
        { step: 3, preferences: { ...emptyCookingPreferences(), allergies: [OTHER_OPTION], allergyOther: [" "], dietary: ["ฮาลาล"] } }, { step: 4, equipment: [] },
        { step: 4, equipmentOther: " " }, { step: 5, cookingFrequency: "" }, { cookingGoals: [] },
    ]) {
        const state = setup(() => assert.fail("Unexpected save"), overrides);
        await state.next();
        assert.equal(state.errors.length, 2);
        assert.deepEqual(state.steps, []);
    }
    assert.deepEqual(toggleInList(["แพ้งา"], NO_RESTRICTION, NO_RESTRICTION), [NO_RESTRICTION]);
    assert.deepEqual(toggleInList([NO_RESTRICTION], "แพ้งา", NO_RESTRICTION), ["แพ้งา"]);
});

test("age keyboard controls respect the existing 15–80 bounds", () => {
    let keyboard;
    function visit(node) {
        if (!node || typeof node !== "object") return;
        if (node.type === "JSXAttribute" && node.name.name === "onKeyDown") keyboard = node.value.expression;
        for (const value of Object.values(node)) {
            if (Array.isArray(value)) value.forEach(visit);
            else if (value && typeof value === "object") visit(value);
        }
    }
    visit(component);
    for (const [age, key, expected] of [["25", "ArrowUp", "26"], ["25", "ArrowDown", "24"], ["80", "ArrowUp", "80"], ["15", "ArrowDown", "15"], ["25", "Home", "15"], ["25", "End", "80"]]) {
        let result, prevented = false;
        const onKeyDown = new Function("pickerValue", "setPickerValue", `return ${source.slice(keyboard.start, keyboard.end)}`)({ age }, value => { result = value; });
        onKeyDown({ key, preventDefault: () => { prevented = true; } });
        assert.deepEqual(result, { age: expected });
        assert.equal(prevented, true);
    }
});

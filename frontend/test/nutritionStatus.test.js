import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const result = await build({
    stdin: { contents: 'export { default as RecipeNutrition } from "./src/components/RecipeNutrition.jsx"; export { default as RecipeContent } from "./src/components/RecipeContent.jsx"; export { default as RecipeDetail } from "./src/pages/RecipeDetail.jsx"; export { setLocale } from "./src/context/LocaleContext";', resolveDir: fileURLToPath(new URL("../", import.meta.url)), loader: "jsx" },
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", jsx: "automatic", loader: { ".png": "dataurl" },
    plugins: [{ name: "test-locale", setup(build) {
        build.onResolve({ filter: /\/context\/LocaleContext$/ }, () => ({ path: "locale", namespace: "test" }));
        build.onLoad({ filter: /.*/, namespace: "test" }, () => ({ contents: 'import { translate } from "./translations.js"; let locale = "th"; export function setLocale(value) { locale = value; } export function useLocale() { return { locale, t: (text, values) => translate(text, locale, values) }; }', resolveDir: fileURLToPath(new URL("../src/utils/", import.meta.url)) }));
    } }],
});
const module = { exports: {} };
new Function("require", "module", "exports", result.outputFiles[0].text)(require, module, module.exports);
const { RecipeNutrition, RecipeContent, RecipeDetail, setLocale } = module.exports;
const macros = { basis: "per_serving", calories: 400, carbs_g: 50, protein_g: 20, fat_g: 0 };
const render = recipe => renderToStaticMarkup(createElement(RecipeNutrition, { recipe }));

for (const locale of ["th", "en"]) {
    test(`base-menu time shows an approximate total range and rejects invalid values in ${locale}`, () => {
        setLocale(locale);
        const renderDetail = time => renderToStaticMarkup(createElement(RecipeDetail, { recipe: {
            id: 1, name: "Chashu Ramen", ingredients: [], estimated_total_time: time, usage_time: "legacy unsupported time",
        } }));
        const html = renderDetail({ min_minutes: 15, max_minutes: 20 });
        assert.ok(html.includes(locale === "en" ? "About 15–20 min" : "ประมาณ 15–20 นาที"));
        assert.ok(html.includes(locale === "en" ? "Named prepared ingredients are ready to use." : "วัตถุดิบสำเร็จรูปที่ระบุถือว่าเตรียมแล้ว"));
        assert.ok(!html.includes("legacy unsupported time"));
        for (const time of [undefined, null, {}, { min_minutes: 0, max_minutes: 10 },
            { min_minutes: 20, max_minutes: 10 }, { min_minutes: "15", max_minutes: 20 },
            { min_minutes: 1.5, max_minutes: 20 }, { min_minutes: true, max_minutes: 20 },
            { min_minutes: 15, max_minutes: Infinity }, { min_minutes: 15, max_minutes: null }]) {
            const missing = renderDetail(time);
            assert.ok(missing.includes(locale === "en" ? "Time unavailable" : "ยังไม่มีข้อมูลเวลา"));
            assert.ok(!missing.includes(locale === "en" ? "Includes prep" : "รวมเตรียม ปรุง"));
            assert.ok(!missing.includes("legacy unsupported time"));
        }
    });
    test(`nutrition shows confirmed, partial and unknown provenance in ${locale}`, () => {
        setLocale(locale);
        const calculated = render({ nutrition: macros, computed_nutrition: macros, llm_estimated_nutrition: { ...macros, calories: 600 }, nutrition_partially_estimated: false });
        assert.ok(calculated.includes(locale === "en" ? "Calculated from nutrition data" : "คำนวณจากฐานข้อมูล"));
        assert.ok(calculated.includes("600 kcal"));
        const partial = render({ nutrition: macros, computed_nutrition: { ...macros, calories: 200 }, nutrition_partially_estimated: true });
        assert.ok(partial.includes(locale === "en" ? "Includes estimates" : "ยังมีค่าประมาณ"));
        assert.ok(partial.indexOf("400 kcal") < partial.indexOf("200 kcal"));
        const legacy = render({ nutrition: macros });
        assert.ok(legacy.includes(locale === "en" ? "Calculation method unavailable" : "ไม่ระบุวิธีคำนวณ"));
        assert.ok(!legacy.includes("400g"));
    });

    test(`missing and invalid nutrition stays unknown, zero stays zero in ${locale}`, () => {
        setLocale(locale);
        const html = render({ nutrition: { ...macros, protein_g: null, calories: NaN }, computed_nutrition: { ...macros, protein_g: null }, nutrition_partially_estimated: false });
        assert.ok(html.includes("—"));
        assert.ok(html.includes(locale === "en" ? "0 g" : "0 กรัม"));
        assert.ok(!html.includes("NaN"));
        assert.ok(!html.includes(locale === "en" ? "Calculated from nutrition data" : "คำนวณจากฐานข้อมูล"));
        const empty = render({});
        assert.ok(empty.includes(locale === "en" ? "Quantity basis unavailable" : "ไม่ระบุฐานปริมาณ"));
    });
}

test("the actual shared recipe body displays partial status for cooking/history callers", () => {
    setLocale("en");
    const html = renderToStaticMarkup(createElement(RecipeContent, { recipe: { recipe_name: "Test", nutrition: macros, nutrition_partially_estimated: true } }));
    assert.ok(html.includes("Includes estimates"));
    assert.ok(html.includes("View calculation details"));
});

for (const locale of ["th", "en"]) {
    test(`base calculations use fresh values and never claim an AI estimate in ${locale}`, () => {
        setLocale(locale);
        const html = render({ nutrition: macros, computed_nutrition: macros, nutrition_origin: "base_calculation", nutrition_partially_estimated: true, nutrition_calculation_status: "limited", nutrition_calculation_reasons: ["source_unverified", "proxy_composition", "constructor", "private error"] });
        assert.ok(html.includes(locale === "en" ? "Calculated with data limitations" : "คำนวณแล้ว แต่ข้อมูลยังมีข้อจำกัด"));
        assert.ok(html.includes(locale === "en" ? "Some ingredient data sources have not been verified." : "แหล่งข้อมูลของวัตถุดิบบางรายการยังไม่ผ่านการยืนยัน"));
        assert.ok(html.includes("400 kcal"));
        assert.ok(!html.includes("private error"));
        assert.ok(!html.includes(locale === "en" ? "The main values are AI estimates" : "ตัวเลขหลักเป็นค่าประมาณของ AI"));
        const unavailable = render({ nutrition: null, computed_nutrition: null, nutrition_origin: "base_calculation", nutrition_partially_estimated: true, nutrition_calculation_status: "unavailable", nutrition_calculation_reasons: ["inputs_incomplete"] });
        assert.ok(unavailable.includes(locale === "en" ? "Calculation unavailable" : "ยังคำนวณไม่ได้"));
        assert.ok(unavailable.includes("—"));
        assert.ok(!unavailable.includes("0 kcal"));
    });
    test(`actual base-menu page consumes calculated nutrition and status in ${locale}`, () => {
        setLocale(locale);
        const html = renderToStaticMarkup(createElement(RecipeDetail, { recipe: { id: 1, name: "Base menu", review: 72, ingredients: [{ name: "kale" }], nutrition: macros, computed_nutrition: macros, nutrition_origin: "base_calculation", nutrition_partially_estimated: true, nutrition_calculation_reasons: ["source_unverified"] } }));
        assert.ok(html.includes(locale === "en" ? "(72 Reviews)" : "(72 รีวิว)"));
        assert.ok(html.includes("Base menu"));
        assert.ok(html.includes("400 kcal"));
        assert.ok(html.includes(locale === "en" ? "Calculated with data limitations" : "คำนวณแล้ว แต่ข้อมูลยังมีข้อจำกัด"));
    });
}

import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const result = await build({
    stdin: { contents: 'export { default as RecipeDetail } from "./src/pages/RecipeDetail.jsx"; export { setLocale } from "./src/context/LocaleContext";', resolveDir: fileURLToPath(new URL("../", import.meta.url)), loader: "jsx" },
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", jsx: "automatic", loader: { ".png": "dataurl" },
    plugins: [{ name: "test-locale", setup(build) {
        build.onResolve({ filter: /\/context\/LocaleContext$/ }, () => ({ path: "locale", namespace: "test" }));
        build.onLoad({ filter: /.*/, namespace: "test" }, () => ({ contents: 'import { translate } from "./translations.js"; let locale = "th"; export function setLocale(value) { locale = value; } export function useLocale() { return { locale, t: (text, values) => translate(text, locale, values) }; }', resolveDir: fileURLToPath(new URL("../src/utils/", import.meta.url)) }));
    } }],
});
const module = { exports: {} };
new Function("require", "module", "exports", result.outputFiles[0].text)(require, module, module.exports);
const { RecipeDetail, setLocale } = module.exports;
const render = time => renderToStaticMarkup(createElement(RecipeDetail, { recipe: {
    id: 1, name: "Chashu Ramen", review: 72, ingredients: [],
    estimated_total_time: time, usage_time: "legacy unsupported time",
} }));

for (const locale of ["th", "en"]) {
    test(`base-menu time shows approximate elapsed range and assumptions in ${locale}`, () => {
        setLocale(locale);
        const html = render({ min_minutes: 15, max_minutes: 20 });
        assert.ok(html.includes(locale === "en" ? "About 15–20 min" : "ประมาณ 15–20 นาที"));
        assert.ok(html.includes(locale === "en" ? "Named prepared ingredients are ready to use." : "วัตถุดิบสำเร็จรูปที่ระบุถือว่าเตรียมแล้ว"));
        assert.ok(html.includes(locale === "en" ? "(72 Reviews)" : "(72 รีวิว)"));
        assert.ok(!html.includes("legacy unsupported time"));
    });
    test(`missing or invalid base-menu time stays unknown in ${locale}`, () => {
        setLocale(locale);
        for (const time of [undefined, null, {}, { min_minutes: 0, max_minutes: 10 },
            { min_minutes: 20, max_minutes: 10 }, { min_minutes: "15", max_minutes: 20 },
            { min_minutes: 1.5, max_minutes: 20 }, { min_minutes: true, max_minutes: 20 },
            { min_minutes: 15, max_minutes: Infinity }, { min_minutes: 15, max_minutes: null }]) {
            const html = render(time);
            assert.ok(html.includes(locale === "en" ? "Time unavailable" : "ยังไม่มีข้อมูลเวลา"));
            assert.ok(!html.includes(locale === "en" ? "Includes prep" : "รวมเตรียม ปรุง"));
            assert.ok(!html.includes("legacy unsupported time"));
        }
    });
}

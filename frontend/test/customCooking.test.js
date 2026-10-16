import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const bundle = await build({
    stdin: {
        contents: 'export { default as Page } from "./src/pages/CustomCookingPage.jsx"; export { setLocale } from "./src/context/LocaleContext";',
        resolveDir: fileURLToPath(new URL("../", import.meta.url)), loader: "jsx",
    },
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", jsx: "automatic", loader: { ".png": "dataurl" },
    plugins: [{
        name: "test-locale",
        setup(build) {
            build.onResolve({ filter: /\/context\/LocaleContext$/ }, () => ({ path: "locale", namespace: "test" }));
            build.onLoad({ filter: /.*/, namespace: "test" }, () => ({
                contents: 'import { translate } from "./translations.js"; let locale="th"; export function setLocale(value){locale=value} export function useLocale(){return {locale,t:(text,values)=>translate(text,locale,values)}}',
                resolveDir: fileURLToPath(new URL("../src/utils/", import.meta.url)),
            }));
        },
    }],
});
const compiled = { exports: {} };
new Function("require", "module", "exports", bundle.outputFiles[0].text)(require, compiled, compiled.exports);
const { Page, setLocale } = compiled.exports;

for (const locale of ["th", "en"]) {
    for (const empty of [true, false]) {
        test(`Custom Cooking exposes choices and recovery (${locale}, ${empty ? "empty" : "populated"})`, () => {
            setLocale(locale);
            const html = renderToStaticMarkup(createElement(Page, {
                userIngredients: empty ? [] : [
                    { id: 1, name: "ไข่ไก่", expiry_date: "2000-01-01" },
                    { id: 2, name: "Chicken & basil", image: "/fixture.png" },
                ], activeTab: "cooking",
            }));
            assert.equal((html.match(/<fieldset/g) || []).length, 3);
            assert.ok(html.includes('aria-pressed="false"'));
            assert.match(html, /<button[^>]*disabled=""[^>]*aria-busy="false"/);
            assert.ok(html.includes('for="cooking-extra"'));
            if (empty) assert.ok(html.includes(locale === "th" ? "ไปที่ตู้เย็นของฉัน" : "Go to My Fridge"));
            else {
                assert.ok(html.includes("ไข่ไก่"));
                assert.ok(html.includes("Chicken &amp; basil"));
                assert.ok(html.includes(locale === "th" ? "หมดอายุแล้ว" : "Expired"));
            }
        });
    }
}

import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const result = await build({
    stdin: {
        contents: 'export { default as Favorites } from "./src/pages/Favorites.jsx"; export { default as UserIngredients } from "./src/pages/UserIngredients.jsx"; export { setLocale } from "./src/context/LocaleContext";',
        resolveDir: fileURLToPath(new URL("../", import.meta.url)),
        loader: "jsx",
    },
    bundle: true, write: false, platform: "node", format: "cjs",
    packages: "external", jsx: "automatic", loader: { ".png": "dataurl" },
    plugins: [{
        name: "test-locale",
        setup(build) {
            build.onResolve({ filter: /\/context\/LocaleContext$/ }, () => ({ path: "locale", namespace: "test" }));
            build.onLoad({ filter: /.*/, namespace: "test" }, () => ({
                contents: 'import { translate } from "./translations.js"; let locale = "th"; export function setLocale(value) { locale = value; } export function useLocale() { return { t: text => translate(text, locale) }; }',
                resolveDir: fileURLToPath(new URL("../src/utils/", import.meta.url)),
            }));
        },
    }],
});
const module = { exports: {} };
new Function("require", "module", "exports", result.outputFiles[0].text)(require, module, module.exports);
const { Favorites, UserIngredients, setLocale } = module.exports;

for (const locale of ["th", "en"]) {
    for (const tab of ["base", "mine"]) {
        for (const populated of [false, true]) {
            test(`Favorites renders ${locale}/${tab}/${populated ? "populated" : "empty"} without the translation crash`, () => {
                setLocale(locale);
                const html = renderToStaticMarkup(createElement(Favorites, {
                    recipes: populated ? [{ id: 1, name: "ไข่เจียว", tags: ["ไข่"] }] : [],
                    categories: ["All", "ไข่"], favoriteRecipeIds: [1],
                    historyFavorites: populated ? [{ id: 2, recipe_name: "สูตรของฉัน", stars: 4 }] : [],
                    activeTab: "favorites", tab,
                }));
                assert.ok(html.includes(locale === "th" ? "เมนูพื้นฐาน" : "Base recipes"));
                assert.ok(html.includes(locale === "th" ? "✨ สูตรของฉัน" : "✨ My recipes"));
                assert.ok(html.includes('aria-current="page"'));
                assert.equal(html.includes('id="favorites-categories"'), tab === "base");
                assert.ok(html.includes(`${populated ? 1 : 0} ${locale === "th" ? "รายการ" : "Items"}</span>`));
                if (populated) assert.ok(html.includes(tab === "base" ? "ไข่เจียว" : "สูตรของฉัน"));
            });
        }
    }
}

for (const locale of ["th", "en"]) {
    for (const count of [0, 1, 12]) {
        test(`My Fridge separates the count and unit (${locale}, ${count})`, () => {
            setLocale(locale);
            const html = renderToStaticMarkup(createElement(UserIngredients, {
                userIngredients: Array.from({ length: count }, (_, id) => ({ id, name: `ingredient ${id}` })),
            }));
            assert.ok(html.includes(`${count} ${locale === "th" ? "รายการ" : "Items"}</span>`));
            assert.ok(html.includes('id="fridge-categories"'));
            assert.ok(html.includes('aria-pressed="true"'));
        });
    }
}

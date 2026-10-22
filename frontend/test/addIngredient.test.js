import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { QUANTITY_UNITS, ENGLISH_QUANTITY_LABELS } from "../src/utils/quantityUnits.js";

const directory = fileURLToPath(new URL("../", import.meta.url));
const bundle = await build({
    stdin: { contents: 'export {default as Add} from "./src/pages/AddIngredient.jsx"; export {setLocale} from "./src/context/LocaleContext";', resolveDir: directory, loader: "jsx" },
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", jsx: "automatic", loader: { ".png": "dataurl" },
    plugins: [{ name: "test-context", setup(build) {
        build.onResolve({ filter: /AvatarCropper$/ }, () => ({path: "crop", namespace: "mock"}));
        build.onResolve({ filter: /\/context\/AuthContext$/ }, () => ({path: "auth", namespace: "mock"}));
        build.onResolve({ filter: /\/context\/LocaleContext$/ }, () => ({path: "locale", namespace: "mock"}));
        build.onLoad({filter: /.*/, namespace: "mock"}, ({path}) => ({
            contents: path === "crop" ? 'export default function Crop(){return null}' : path === "auth" ? 'export function useAuth(){return {apiFetch:async()=>{throw Error("Unexpected API call")}}}' : 'import {translate} from "./src/utils/translations.js";let locale="th";export function setLocale(value){locale=value}export function useLocale(){return {locale,t:(text,values)=>translate(text,locale,values)}}', resolveDir: directory,
        }));
    }}],
});
const compiled = {exports:{}};
new Function("require", "module", "exports", bundle.outputFiles[0].text)(createRequire(import.meta.url), compiled, compiled.exports);
const {Add, setLocale} = compiled.exports;
for (const locale of ["th", "en"]) test(`image picker precedes name and quantity values stay canonical (${locale})`, () => {
    setLocale(locale);
    const html = renderToStaticMarkup(createElement(Add, {userIngredients:[], activeTab:"fridge", prefill:{name:"Eggs", image:"/eggs.jpg", category:"Other"}}));
    assert.ok(html.indexOf('<section') < html.indexOf('id="ingredient-name"'));
    assert.match(html, /src="\/eggs.jpg"/);
    for (const unit of QUANTITY_UNITS) assert.ok(html.includes(`<option value="${unit}">${locale === "en" ? ENGLISH_QUANTITY_LABELS[unit] : unit}</option>`));
    assert.match(html, /accept="image\/jpeg,image\/png,image\/webp"/);
    assert.doesNotMatch(html, /capture="environment"/);
    if (locale === "en") for (const label of ["g (grams)", "kg (kilograms)", "ml (milliliters)", "pcs (pieces)"]) assert.ok(html.includes(label));
});

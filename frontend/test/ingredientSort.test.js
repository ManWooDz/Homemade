import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { translate } from "../src/utils/translations.js";

const require = createRequire(import.meta.url);
const source = readFileSync(new URL("../src/pages/UserIngredients.jsx", import.meta.url), "utf8");
const options = source.slice(source.indexOf("const SORT_OPTIONS"), source.indexOf("function applySort"));
const start = source.indexOf("{/* Sort sheet */}");
const end = source.indexOf("{/* === Bottom Navigation === */}", start);
assert.ok(start >= 0 && end > start);
const result = await build({
    stdin: {
        contents: `import { CalendarClock, TrendingUp, Type, Tag, X } from "lucide-react";
            ${options}
            export function SortSheet({t,pendingSort}) {
                const showSortSheet=true,sortSheetRef={current:null},sheetTop=0;
                const setPendingSort=()=>{},setSortBy=()=>{},setShowSortSheet=()=>{},handleSortKeyDown=()=>{};
                return <>${source.slice(start, end)}</>;
            }`,
        resolveDir: fileURLToPath(new URL("../", import.meta.url)), loader: "jsx",
    },
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", jsx: "automatic",
});
const compiled = { exports: {} };
new Function("require", "module", "exports", result.outputFiles[0].text)(require, compiled, compiled.exports);

for (const locale of ["th", "en"]) {
    for (const pendingSort of ["expiry", "quantity", "alphabetical", "category"]) {
        test(`sort sheet exposes a labelled dialog and one selected native radio (${locale}/${pendingSort})`, () => {
            const html = renderToStaticMarkup(createElement(compiled.exports.SortSheet, { pendingSort, t: text => translate(text, locale) }));
            assert.ok(html.includes('role="dialog"'));
            assert.ok(html.includes('aria-modal="true"'));
            assert.ok(html.includes('aria-labelledby="ingredient-sort-title"'));
            assert.ok(html.includes('role="radiogroup"'));
            assert.equal((html.match(/type="radio"/g) || []).length, 4);
            assert.equal((html.match(/checked=""/g) || []).length, 1);
            assert.ok(html.includes(`checked="" value="${pendingSort}"`));
            assert.ok(html.includes(translate("น้อยไปมาก ภายในกลุ่มหน่วยที่เปรียบเทียบกันได้", locale)));
            assert.ok(html.includes(`aria-label="${locale === "en" ? "Close" : "ปิด"}"`));
        });
    }
}

const ast = require("@babel/parser").parse(source, { sourceType: "module", plugins: ["jsx"] });
const component = ast.program.body.find(node => node.type === "ExportDefaultDeclaration").declaration;
const keyHandler = component.body.body.flatMap(node => node.declarations || []).find(node => node.id.name === "handleSortKeyDown").init;

test("Escape closes the sheet and Tab wraps only at its enabled-control boundaries", () => {
    let open = true, prevented = 0, focused;
    const controls = ["close", "radio", "clear", "apply"].map(name => ({ focus: () => { focused = name; } }));
    const doc = { activeElement: controls[3] };
    const handler = new Function("setShowSortSheet", "document", `return (${source.slice(keyHandler.start, keyHandler.end)});`)(value => { open = value; }, doc);
    const event = overrides => ({ key: "Tab", shiftKey: false, currentTarget: { querySelectorAll: () => controls }, preventDefault: () => { prevented++; }, ...overrides });
    handler(event());
    assert.equal(focused, "close");
    doc.activeElement = controls[0];
    handler(event({ shiftKey: true }));
    assert.equal(focused, "apply");
    doc.activeElement = controls[1];
    handler(event());
    assert.equal(prevented, 2);
    handler(event({ key: "Escape" }));
    assert.equal(open, false);
    assert.equal(prevented, 3);
});

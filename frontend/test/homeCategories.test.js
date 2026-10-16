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

const source = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
const start = source.indexOf("{/* Categories */}");
const end = source.indexOf("{/* Recipe Cards */}", start);
assert.ok(start >= 0 && end > start);
const result = await build({
    stdin: {
        contents: `import DragScrollRow from "./src/components/DragScrollRow.jsx"; export { DragScrollRow }; export function Categories({t,categories,selectedCategory,setSelectedCategory}) { return <>${source.slice(start, end)}</>; }`,
        resolveDir: fileURLToPath(new URL("../", import.meta.url)), loader: "jsx",
    },
    bundle: true, write: false, packages: "external", platform: "node", jsx: "automatic", format: "cjs",
});
const compiled = { exports: {} };
new Function("require", "module", "exports", result.outputFiles[0].text)(require, compiled, compiled.exports);
const { Categories, DragScrollRow } = compiled.exports;
const categories = ["All", "Breakfast", "Vegan", "Thai"];

for (const locale of ["th", "en"]) {
        test(`Home categories stay scrollable without See all (${locale})`, () => {
            const html = renderToStaticMarkup(createElement(Categories, {
                t: text => translate(text, locale), categories, selectedCategory: "Vegan",
            }));
            assert.doesNotMatch(html, /See all|ดูทั้งหมด|Show less|ย่อหมวดหมู่|aria-expanded/);
            assert.ok(html.includes('id="home-categories"'));
            assert.ok(html.includes("overflow-x-auto"));
            assert.equal((html.match(/aria-pressed="true"/g) || []).length, 1);
            assert.equal((html.match(/aria-pressed=/g) || []).length, categories.length);
        });
}

const rowSource = readFileSync(new URL("../src/components/DragScrollRow.jsx", import.meta.url), "utf8");
const ast = require("@babel/parser").parse(rowSource, { sourceType: "module", plugins: ["jsx"] });
const component = ast.program.body.find(node => node.type === "ExportDefaultDeclaration").declaration;
const declarations = new Map(component.body.body.flatMap(node => node.declarations || []).map(node => [node.id.name, node.init]));
function dragFixture() {
    const drag = { current: { isDown: false, startX: 0, scrollLeft: 0, moved: false } };
    const handlers = Object.fromEntries(["handleMouseDown", "handleMouseMove", "stopDrag", "handleClickCapture"].map(name => {
        const node = declarations.get(name);
        return [name, new Function("drag", `return (${rowSource.slice(node.start, node.end)});`)(drag)];
    }));
    const row = { offsetLeft: 10, scrollLeft: 20 };
    let prevented = 0, selected;
    const event = (pageX, overrides = {}) => ({ currentTarget: row, button: 0, buttons: 1, pageX, detail: 1,
        preventDefault: () => { prevented++; }, stopPropagation() { this.stopped = true; }, ...overrides });
    const activate = (value, detail = 1) => {
        const click = event(0, { detail });
        handlers.handleClickCapture(click);
        if (!click.stopped) selected = value;
    };
    return { ...handlers, row, drag, event, activate, result: () => ({ prevented, selected }) };
}

test("Home row wires shared drag handlers and ordinary category selection", () => {
    let selected;
    const tree = Categories({ t: text => text, categories, selectedCategory: "All",
        setSelectedCategory: value => { selected = value; },
    });
    const list = tree.props.children[1];
    assert.equal(list.type, DragScrollRow);
    list.props.children[1].props.onClick();
    assert.equal(selected, "Breakfast");
});

test("drag scrolls the row and suppresses its trailing mouse click, then a normal click works", () => {
    const f = dragFixture();
    f.handleMouseDown(f.event(120));
    f.handleMouseMove(f.event(50));
    f.stopDrag();
    assert.equal(f.row.scrollLeft, 90);
    f.activate("Vegan");
    assert.deepEqual(f.result(), { prevented: 2, selected: undefined });
    f.handleMouseDown(f.event(80));
    f.handleMouseMove(f.event(77));
    f.stopDrag();
    f.activate("Breakfast");
    assert.equal(f.result().selected, "Breakfast");
});

test("keyboard selection after leaving a drag remains available", () => {
    const f = dragFixture();
    f.handleMouseDown(f.event(120));
    f.handleMouseMove(f.event(40));
    f.stopDrag();
    f.activate("Thai", 0);
    assert.equal(f.result().selected, "Thai");
});

test("secondary buttons and a released primary button do not continue scrolling", () => {
    const f = dragFixture();
    f.handleMouseDown(f.event(120, { button: 2, buttons: 2 }));
    f.handleMouseMove(f.event(40, { buttons: 2 }));
    assert.equal(f.row.scrollLeft, 20);
    f.handleMouseDown(f.event(120));
    f.handleMouseMove(f.event(40, { buttons: 0 }));
    assert.equal(f.row.scrollLeft, 20);
    assert.equal(f.drag.current.isDown, false);
});

test("the same handlers scroll the event's row rather than a different strip", () => {
    const f = dragFixture();
    const otherRow = { offsetLeft: 80, scrollLeft: 100 };
    f.handleMouseDown(f.event(200, { currentTarget: otherRow }));
    f.handleMouseMove(f.event(140, { currentTarget: otherRow }));
    assert.equal(otherRow.scrollLeft, 160);
    assert.equal(f.row.scrollLeft, 20);
});

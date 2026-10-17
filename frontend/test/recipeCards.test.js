import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const result = await build({
  stdin: { contents: 'export {default as Detail} from "./src/pages/RecipeDetail.jsx"; export {default as Cooking} from "./src/pages/CookingPage.jsx"; export {default as Instructions} from "./src/components/RecipeInstructions.jsx"; export {setLocale} from "./src/context/LocaleContext";', resolveDir: fileURLToPath(new URL("../", import.meta.url)), loader: "jsx" },
  bundle: true, write: false, platform: "node", format: "cjs", packages: "external", jsx: "automatic", loader: { ".png": "dataurl" },
  plugins: [{ name: "test-locale", setup(build) {
    build.onResolve({ filter: /\/context\/LocaleContext$/ }, () => ({ path: "locale", namespace: "test" }));
    build.onLoad({ filter: /.*/, namespace: "test" }, () => ({ contents: 'import {translate} from "./translations.js"; let locale="th"; export function setLocale(value){locale=value} export function useLocale(){return {locale,t:(text,values)=>translate(text,locale,values)}}', resolveDir: fileURLToPath(new URL("../src/utils/", import.meta.url)) }));
  } }],
});
const compiled = { exports: {} };
new Function("require", "module", "exports", result.outputFiles[0].text)(require, compiled, compiled.exports);
const { Detail, Cooking, Instructions, setLocale } = compiled.exports;
const recipe = { id: 1, name: "Vegetable Bowl", recipe_name: "Vegetable Bowl", ingredients: [{ name: "Kale" }], adjusted_ingredients: ["Kale 200 g"],
  servings: 2, tags: ["Vegan"], diet_tags: ["Vegan"], instructions: ["1. Prepare\nWash the kale.", "2. Cook until tender."],
  nutrition: { basis: "per_serving", calories: 320, carbs_g: 42, protein_g: 12, fat_g: 8 }, nutrition_partially_estimated: true, safety_warning: "Keep the allergy warning." };

for (const locale of ["th", "en"]) {
  for (const mode of ["detail", "cooking", "custom"]) {
    test(`recipe card retains content and accessible controls (${locale}, ${mode})`, () => {
      setLocale(locale);
      const html = renderToStaticMarkup(createElement(mode === "detail" ? Detail : Cooking, {
        recipe, generatedRecipe: recipe, isCustom: mode === "custom", onConfirm() {},
      }));
      assert.ok(html.includes("recipe-sheet-scroll recipe-reading"));
      assert.ok(html.includes('tabindex="0"'));
      assert.ok(html.includes('role="region"'));
      assert.equal(html.includes('aria-expanded="false"'), mode !== "custom");
      assert.ok(html.includes('<ol class="recipe-steps'));
      assert.ok(html.includes("Wash the kale."));
      assert.ok(html.includes("Cook until tender."));
      assert.ok(html.includes("320 kcal"));
      assert.ok(html.includes(locale === "en" ? "Includes estimates" : "ยังมีค่าประมาณ"));
      assert.ok(!html.includes("400g"));
      if (mode === "detail") {
        assert.ok(html.includes('type="checkbox"'));
        assert.ok(html.includes('aria-describedby="recipe-ingredient-help"'));
        assert.ok(html.includes(locale === "en" ? "Select the ingredients you want to use in this recipe." : "เลือกวัตถุดิบที่ต้องการใช้ในสูตร"));
        assert.ok(html.includes(locale === "en" ? "Continue" : "ดำเนินการต่อ"));
      }
      else assert.ok(html.includes("Keep the allergy warning."));
    });
  }
}

test("steps use supplied titles, escape content and omit absent instructions", () => {
  setLocale("en");
  const html = renderToStaticMarkup(createElement(Instructions, { instructions: ["1) <script>\nOriginal body", "2. Untitled step"] }));
  assert.ok(html.includes("&lt;script&gt;"));
  assert.ok(html.includes("Original body"));
  assert.ok(!html.includes("1)"));
  for (const instructions of [undefined, null, []]) assert.equal(renderToStaticMarkup(createElement(Instructions, { instructions })), "");
});

const sheetSource = readFileSync(new URL("../src/components/RecipeSheet.jsx", import.meta.url), "utf8");
const ast = require("@babel/parser").parse(sheetSource, { sourceType: "module", plugins: ["jsx"] });
const component = ast.program.body.find(node => node.type === "ExportDefaultDeclaration").declaration;
const declarations = new Map(component.body.body.flatMap(node => node.declarations || []).map(node => [node.id.name, node.init]));
function gestureFixture() {
  const gesture = { current: null }, dragged = { current: false };
  let expanded = false;
  const setExpanded = value => { expanded = typeof value === "function" ? value(expanded) : value; };
  const handlers = Object.fromEntries(["startDrag", "endDrag", "toggleSheet"].map(name => {
    const node = declarations.get(name);
    return [name, new Function("gesture", "dragged", "setExpanded", `return (${sheetSource.slice(node.start, node.end)});`)(gesture, dragged, setExpanded)];
  }));
  return { ...handlers, expanded: () => expanded, event: (y, extra = {}) => ({ button: 0, pointerId: 1, clientY: y, detail: 1, currentTarget: { setPointerCapture() {} }, ...extra }) };
}
test("up/down handle drags snap without the trailing click reversing the result", () => {
  const f = gestureFixture();
  f.startDrag(f.event(200)); f.endDrag(f.event(100)); f.toggleSheet(f.event(100));
  assert.equal(f.expanded(), true);
  f.startDrag(f.event(100)); f.endDrag(f.event(200)); f.toggleSheet(f.event(200));
  assert.equal(f.expanded(), false);
});
test("keyboard activation after a drag still toggles and small pointer movement remains a click", () => {
  const f = gestureFixture();
  f.startDrag(f.event(200)); f.endDrag(f.event(100)); f.toggleSheet(f.event(100, { detail: 0 }));
  assert.equal(f.expanded(), false);
  f.startDrag(f.event(100)); f.endDrag(f.event(105)); f.toggleSheet(f.event(105));
  assert.equal(f.expanded(), true);
});
test("secondary-button and unrelated-pointer releases cannot move the card", () => {
  const f = gestureFixture();
  f.startDrag(f.event(200, { button: 2 })); f.endDrag(f.event(100));
  assert.equal(f.expanded(), false);
  f.startDrag(f.event(200)); f.endDrag(f.event(100, { pointerId: 2 }));
  assert.equal(f.expanded(), false);
});

function scrollFixture(inline = false) {
  assert.ok(declarations.has("resizeAtEdge"), "RecipeSheet must restore automatic resize at scroll boundaries");
  const lastScrollTop = { current: 0 }, touchY = { current: null };
  let expanded = false;
  const setExpanded = value => { expanded = value; };
  const factory = name => {
    const node = declarations.get(name);
    assert.ok(node, `Missing shared scroll handler: ${name}`);
    return sheetSource.slice(node.start, node.end);
  };
  const resizeAtEdge = new Function("inline", "setExpanded", `return (${factory("resizeAtEdge")});`)(inline, setExpanded);
  const handlers = Object.fromEntries(["handleScroll", "handleWheel", "handleTouchStart", "handleTouchMove"].map(name => [name,
    new Function("resizeAtEdge", "lastScrollTop", "touchY", `return (${factory(name)});`)(resizeAtEdge, lastScrollTop, touchY),
  ]));
  const row = { scrollTop: 0, scrollHeight: 1000, clientHeight: 300 };
  return { ...handlers, row, event: extra => ({ currentTarget: row, ...extra }), expanded: () => expanded };
}

test("native scrolling expands at the bottom and collapses at the top, without changing state mid-content", () => {
  const f = scrollFixture();
  f.row.scrollTop = 350; f.handleScroll(f.event()); assert.equal(f.expanded(), false);
  f.row.scrollTop = 700; f.handleScroll(f.event()); assert.equal(f.expanded(), true);
  f.row.clientHeight = 550; f.row.scrollTop = 450; f.handleScroll(f.event()); assert.equal(f.expanded(), true);
  f.row.scrollTop = 100; f.handleScroll(f.event()); assert.equal(f.expanded(), true);
  f.row.scrollTop = 0; f.handleScroll(f.event()); assert.equal(f.expanded(), false);
});
test("wheel overscroll respects direction and the inline Custom reader never snaps", () => {
  const f = scrollFixture();
  f.handleWheel(f.event({ deltaY: 100 })); assert.equal(f.expanded(), false);
  f.row.scrollTop = 700; f.handleWheel(f.event({ deltaY: 0 })); assert.equal(f.expanded(), false);
  f.handleWheel(f.event({ deltaY: 100 })); assert.equal(f.expanded(), true);
  f.row.scrollTop = 0; f.handleWheel(f.event({ deltaY: -100 })); assert.equal(f.expanded(), false);
  const inline = scrollFixture(true);
  inline.row.scrollTop = 700; inline.handleScroll(inline.event()); inline.handleWheel(inline.event({ deltaY: 100 }));
  assert.equal(inline.expanded(), false);
});
test("single-finger swipes resize at the edges without intercepting native scrolling or multi-touch", () => {
  const f = scrollFixture();
  f.row.scrollTop = 700;
  f.handleTouchStart(f.event({ touches: [{ clientY: 200 }] }));
  f.handleTouchMove(f.event({ touches: [{ clientY: 100 }] })); assert.equal(f.expanded(), true);
  f.row.scrollTop = 0;
  f.handleTouchMove(f.event({ touches: [{ clientY: 200 }] })); assert.equal(f.expanded(), false);
  f.row.scrollTop = 700;
  f.handleTouchStart(f.event({ touches: [{ clientY: 200 }, { clientY: 300 }] }));
  f.handleTouchMove(f.event({ touches: [{ clientY: 100 }, { clientY: 200 }] })); assert.equal(f.expanded(), false);
});
test("layout expansion that makes short content fit does not immediately collapse the card", () => {
  const f = scrollFixture();
  f.row.scrollHeight = 400; f.row.scrollTop = 100; f.handleScroll(f.event()); assert.equal(f.expanded(), true);
  f.row.clientHeight = 550; f.row.scrollTop = 0; f.handleScroll(f.event()); assert.equal(f.expanded(), true);
  f.handleWheel(f.event({ deltaY: -100 })); assert.equal(f.expanded(), false);
  f.handleWheel(f.event({ deltaY: 100 })); assert.equal(f.expanded(), false);
});

function animationFixture({ expanded = false, reduce = false, initial = "45%", inline = false } = {}) {
  const call = component.body.body.find(node => node.type === "ExpressionStatement" && node.expression.callee?.name === "useLayoutEffect")?.expression;
  assert.ok(call, "RecipeSheet must restore a measured spring animation");
  const node = call.arguments[0];
  const parent = { clientHeight: 800 };
  let value = initial, stopped = 0, disconnected = false, resize;
  const calls = [];
  const sheetTop = { get: () => value, set: next => { value = next; } };
  const animate = (motionValue, target, options) => {
    calls.push({ motionValue, target, options });
    return { stop() { stopped++; } };
  };
  class Observer {
    constructor(callback) { resize = callback; }
    observe(target) { assert.equal(target, parent); }
    disconnect() { disconnected = true; }
  }
  const effect = new Function("inline", "sheetRef", "sheetTop", "expanded", "shouldReduceMotion", "animate", "ResizeObserver", `return (${sheetSource.slice(node.start, node.end)});`)(inline, { current: { parentElement: parent } }, sheetTop, expanded, reduce, animate, Observer);
  const cleanup = effect();
  return { parent, calls, cleanup, resize: () => resize?.(), state: () => ({ value, stopped, disconnected }) };
}
test("first paint sets the collapsed position without an entrance jump", () => {
  const f = animationFixture();
  assert.equal(f.state().value, 360);
  assert.equal(f.calls.length, 0);
});
test("expansion and collapse reuse the original spring and stop it on cleanup", () => {
  for (const expanded of [true, false]) {
    const f = animationFixture({ expanded, initial: expanded ? 360 : 128 });
    assert.equal(f.calls[0].target, expanded ? 128 : 360);
    assert.deepEqual(f.calls[0].options, { type: "spring", stiffness: 300, damping: 30 });
    f.resize(); assert.equal(f.state().stopped, 0);
    f.cleanup(); assert.deepEqual(f.state(), { value: expanded ? 360 : 128, stopped: 1, disconnected: true });
  }
});
test("viewport resizing recalculates the bound and cancels an obsolete spring", () => {
  const f = animationFixture({ expanded: true, initial: 360 });
  f.parent.clientHeight = 400; f.resize();
  assert.equal(f.state().value, 80);
  assert.equal(f.state().stopped, 1);
});
test("reduced-motion and inline readers skip the spring", () => {
  const reduced = animationFixture({ expanded: true, reduce: true, initial: 360 });
  assert.equal(reduced.state().value, 128); assert.equal(reduced.calls.length, 0);
  const inline = animationFixture({ inline: true });
  assert.equal(inline.cleanup, undefined); assert.equal(inline.calls.length, 0);
});

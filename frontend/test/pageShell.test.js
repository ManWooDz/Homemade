import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const result = await build({
  stdin: { contents: 'export {default as PageShell} from "./src/components/PageShell.jsx"; export {effects,frame} from "react";', resolveDir: fileURLToPath(new URL("../", import.meta.url)), loader: "jsx" },
  bundle: true, write: false, platform: "node", format: "cjs", packages: "external", jsx: "automatic",
  plugins: [{ name: "capture-layout-effects", setup(build) {
    build.onResolve({ filter: /^react$/ }, () => ({ path: "hooks", namespace: "test" }));
    build.onLoad({ filter: /.*/, namespace: "test" }, () => ({ contents: 'export const effects=[]; export const frame={current:null}; export const useRef=()=>frame; export const useLayoutEffect=fn=>effects.push(fn);' }));
  } }],
});
const compiled = { exports: {} };
new Function("require", "module", "exports", result.outputFiles[0].text)(require, compiled, compiled.exports);
const { PageShell, effects, frame } = compiled.exports;
const mount = props => { effects.length = 0; return PageShell(props); };

test("ordinary pages grow with document content; recipe sheets retain a bounded frame", () => {
  const page = renderToStaticMarkup(mount({ children: "content" }));
  assert.match(page, /min-h-dvh/);
  assert.doesNotMatch(page, /overflow-hidden|page-frame--contained/);
  const sheet = renderToStaticMarkup(mount({ contained: true, children: "content" }));
  assert.match(sheet, /h-dvh overflow-hidden/);
  assert.match(sheet, /page-frame--contained/);
});

test("page and notification-tab entry restore the requested document position", () => {
  const previous = globalThis.window;
  const calls = [];
  globalThis.window = { scrollTo: value => calls.push(value) };
  try {
    mount({}); effects[0]();
    mount({ initialScroll: 350, scrollKey: "read" }); effects[0]();
    assert.deepEqual(calls, [{ top: 0, behavior: "instant" }, { top: 350, behavior: "instant" }]);
  } finally { globalThis.window = previous; }
});

test("fixed action height changes reserve real content clearance and disconnect on exit", () => {
  const previous = globalThis.ResizeObserver;
  const properties = {};
  const observed = [];
  let update, disconnected = false, actionHeight = 90;
  const nav = { getBoundingClientRect: () => ({ height: 89 }) };
  const actions = { getBoundingClientRect: () => ({ height: actionHeight }) };
  globalThis.ResizeObserver = class {
    constructor(callback) { update = callback; }
    observe(element) { observed.push(element); }
    disconnect() { disconnected = true; }
  };
  try {
    mount({});
    frame.current = { querySelector: selector => selector === "nav" ? nav : actions, style: { setProperty: (key, value) => { properties[key] = value; } } };
    const cleanup = effects[1]();
    assert.deepEqual(observed, [nav, actions]);
    assert.equal(properties["--page-bottom-clearance"], "179px");
    actionHeight = 180; update();
    assert.equal(properties["--page-bottom-clearance"], "269px");
    assert.equal(properties["--bottom-menu-height"], "89px");
    cleanup(); assert.equal(disconnected, true);
  } finally { globalThis.ResizeObserver = previous; }
});

for (const props of [{ lockScroll: true }, { contained: true }]) {
  test(`sheets lock Safari's background and restore position/styles on close (${JSON.stringify(props)})`, () => {
    const previousWindow = globalThis.window, previousDocument = globalThis.document;
    const style = { position: "relative", top: "2px", width: "80%", overflow: "clip" };
    const original = { ...style };
    const rootStyle = { overscrollBehaviorY: "auto" };
    const calls = [];
    globalThis.window = { scrollY: 250, scrollTo: value => calls.push(value) };
    globalThis.document = { body: { style }, documentElement: { style: rootStyle } };
    try {
      mount(props); const cleanup = effects[2]();
      assert.equal(style.position, "fixed");
      assert.equal(style.top, "-250px");
      assert.equal(rootStyle.overscrollBehaviorY, "none");
      cleanup();
      assert.deepEqual(style, original);
      assert.equal(rootStyle.overscrollBehaviorY, "auto");
      assert.deepEqual(calls, [{ top: 250, behavior: "instant" }]);
    } finally { globalThis.window = previousWindow; globalThis.document = previousDocument; }
  });
}

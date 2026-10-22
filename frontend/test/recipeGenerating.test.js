import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const require = createRequire(import.meta.url);
const bundle = await build({
  entryPoints: [fileURLToPath(new URL("../src/components/RecipeGenerating.jsx", import.meta.url))],
  bundle: true, write: false, platform: "node", format: "cjs", packages: "external",
  jsx: "automatic", loader: { ".png": "dataurl" },
  plugins: [{ name: "locale", setup(build) {
    build.onResolve({ filter: /\/context\/LocaleContext$/ }, () => ({ path: "locale", namespace: "test" }));
    build.onLoad({ filter: /.*/, namespace: "test" }, () => ({ contents: "export function useLocale(){return {t:text=>text}}" }));
  } }],
});

test("notes and matching icons cycle, wrap, and stop their timer on unmount", () => {
  let noteIndex = 0;
  let setup;
  let tick;
  let cleared;
  const compiled = { exports: {} };
  const fakeRequire = name => name === "react" ? {
    ...require(name),
    useState: () => [noteIndex, update => { noteIndex = update(noteIndex); }],
    useEffect: effect => { setup ??= effect; },
  } : require(name);
  new Function("require", "module", "exports", bundle.outputFiles[0].text)(fakeRequire, compiled, compiled.exports);
  const Page = compiled.exports.default;
  const originalWindow = globalThis.window;
  globalThis.window = {
    setInterval(callback, delay) { assert.equal(delay, 3500); tick = callback; return 42; },
    clearInterval(id) { cleared = id; },
  };
  const walk = element => {
    if (Array.isArray(element)) return element.flatMap(walk);
    if (!element || typeof element !== "object") return [element];
    return [element.type?.displayName, ...walk(element.props?.children)];
  };
  try {
    Page();
    const cleanup = setup();
    for (const [icon, text] of [
      ["Carrot", "เริ่มต้นจากวัตถุดิบที่คุณเลือก"],
      ["SlidersHorizontal", "นำความต้องการของคุณมาปรับสูตร"],
      ["CookingPot", "เรียบเรียงส่วนผสมและวิธีทำ"],
      ["ClipboardCheck", "ตรวจทานสูตรก่อนแสดงผล"],
      ["Carrot", "เริ่มต้นจากวัตถุดิบที่คุณเลือก"],
    ]) {
      const content = walk(Page());
      assert.ok(content.includes(icon), icon);
      assert.ok(content.includes(text), text);
      tick();
    }
    cleanup();
    assert.equal(cleared, 42);
  } finally {
    globalThis.window = originalWindow;
  }
});

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { filterHistory } from "../src/utils/history.js";

const require = createRequire(import.meta.url);
const parser = require("@babel/parser");
const appSource = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
const detailSource = readFileSync(new URL("../src/pages/HistoryDetail.jsx", import.meta.url), "utf8");
function find(source, name) {
    let found;
    function visit(node) {
        if (!node || typeof node !== "object") return;
        if (node.type === "VariableDeclarator" && node.id.name === name) found = node.init;
        for (const value of Object.values(node)) {
            if (Array.isArray(value)) value.forEach(visit);
            else if (value && typeof value === "object") visit(value);
        }
    }
    visit(parser.parse(source, { sourceType: "module", plugins: ["jsx"] }));
    assert.ok(found, name);
    return source.slice(found.start, found.end);
}
function handler(source, name, context) {
    return new Function(...Object.keys(context), `return (${find(source, name)});`)(...Object.values(context));
}

for (const currentView of ["home", "user-ingredients", "add-ingredient", "barcode-scan", "ingredient-detail", "favorites", "profile"]) {
    test(`Cooking navigation opens ingredient selection from ${currentView}`, () => {
        const state = { activeTab: "home", currentView, selectedRecipe: { id: 1 }, openedFromNotification: true };
        const changeTab = handler(appSource, "handleTabChange", {
            currentView,
            setOpenedFromNotification: value => { state.openedFromNotification = value; },
            setActiveTab: value => { state.activeTab = value; },
            setCurrentView: value => { state.currentView = value; },
            setSelectedRecipe: value => { state.selectedRecipe = value; },
        });
        changeTab("cooking");
        assert.deepEqual(state, { activeTab: "cooking", currentView: "custom-cooking", selectedRecipe: null, openedFromNotification: false });
    });
}

const entries = [
    { id: 4, recipe_name: "กะเพราหมู", adjusted_ingredients: ["หมูสับ 100 กรัม", "กระเทียม 2 กลีบ"], stars: 5, is_favorite: true },
    { id: 3, recipe_name: "Chicken Soup", adjusted_ingredients: ["chicken breast", "น้ำปลา"], stars: 3, is_favorite: true },
    { id: 2, recipe_name: "ไข่เจียว", adjusted_ingredients: ["ไข่ไก่"], stars: 0, is_favorite: false, feedback: "หมู", instructions: ["ใส่หมู"] },
    { id: 1, recipe_name: "น้ำซุป", adjusted_ingredients: [], stars: null, is_favorite: true },
];
const defaults = { query: "", favorite: "all", rating: "all" };
const ids = patch => filterHistory(entries, { ...defaults, ...patch }).map(item => item.id);

test("history search matches partial name/ingredient text with Thai normalization, case and whitespace", () => {
    assert.deepEqual(ids({ query: "  CHICKEN " }), [3]);
    assert.deepEqual(ids({ query: "หมู" }), [4]);
    assert.deepEqual(ids({ query: "นํ้าปลา" }), [3]);
    assert.deepEqual(ids({ query: "  " }), [4, 3, 2, 1]);
});
test("search treats a phrase literally within one field and excludes steps and feedback", () => {
    assert.deepEqual(ids({ query: "หมู กระเทียม" }), []);
    assert.deepEqual(ids({ query: "หมูสับ" }), [4]);
    assert.deepEqual(ids({ query: "pork" }), []);
    assert.deepEqual(ids({ query: "100 กรัม" }), [4]);
});
test("favorite, rating and query intersect while retaining server order and source values", () => {
    const before = JSON.stringify(entries);
    assert.deepEqual(ids({ favorite: "favorites", rating: "3", query: "soup" }), [3]);
    assert.deepEqual(ids({ favorite: "favorites", rating: "5", query: "soup" }), []);
    assert.deepEqual(ids({ rating: "unrated" }), [2, 1]);
    assert.deepEqual(ids({ favorite: "favorites", rating: "unrated" }), [1]);
    assert.deepEqual(filterHistory([], defaults), []);
    assert.equal(JSON.stringify(entries), before);
});

function ratingContext(response = { ok: true, json: async () => ({ status: "success", data: { stars: 2, tag: null, feedback: "confirmed" } }) }) {
    const state = { list: [{ id: 7, stars: 5, recipe_name: "keep" }], selected: { id: 7, stars: 5, recipe_name: "keep" }, calls: [] };
    const context = {
        historySessionRef: { current: { pending: new Set() } },
        apiFetch: async (path, options) => { state.calls.push({ path, options }); return response; },
        setCookingHistory: update => { state.list = update(state.list); },
        setSelectedHistoryItem: update => { state.selected = update(state.selected); },
        console: { error() {} },
    };
    return { context, state, rate: () => handler(appSource, "rateRecipe", context) };
}
const edited = { stars: 4, tag: "Great", feedback: "draft" };
test("actual rating handler uses the owned endpoint and server-confirmed rating in list and detail", async () => {
    const { state, rate } = ratingContext();
    assert.equal(await rate()(7, edited), true);
    assert.equal(state.calls[0].path, "/api/history/7/rating");
    assert.equal(state.calls[0].options.method, "PUT");
    assert.deepEqual(JSON.parse(state.calls[0].options.body), edited);
    assert.deepEqual(state.selected, { id: 7, stars: 2, tag: null, feedback: "confirmed", recipe_name: "keep" });
    assert.deepEqual(state.list[0], state.selected);
});
test("notification-only detail updates even when absent from cached history; another selected entry is retained", async () => {
    const { state, rate } = ratingContext();
    state.list = [];
    assert.equal(await rate()(7, edited), true);
    assert.equal(state.selected.stars, 2);
    assert.deepEqual(state.list, []);
    state.selected = { id: 8, stars: 1 };
    await rate()(7, edited);
    assert.deepEqual(state.selected, { id: 8, stars: 1 });
});
test("HTTP, status, JSON and network failures preserve confirmed ratings and release pending state", async () => {
    for (const failure of [
        async () => ({ ok: false }),
        async () => ({ ok: true, json: async () => ({ status: "error" }) }),
        async () => ({ ok: true, json: async () => { throw new Error("invalid JSON"); } }),
        async () => { throw new Error("offline"); },
    ]) {
        const { context, state, rate } = ratingContext();
        context.apiFetch = failure;
        assert.equal(await rate()(7, edited), false);
        assert.equal(state.list[0].stars, 5);
        assert.equal(state.selected.stars, 5);
        assert.equal(context.historySessionRef.current.pending.size, 0);
    }
});
test("duplicate rating calls are ignored and a departed session cannot commit a late response", async () => {
    const { context, state, rate } = ratingContext();
    let release;
    const response = await context.apiFetch("setup", {});
    state.calls = [];
    context.apiFetch = async () => { state.calls.push("save"); return new Promise(resolve => { release = () => resolve(response); }); };
    const save = rate();
    const pending = save(7, edited);
    assert.equal(await save(7, edited), false);
    assert.deepEqual(state.calls, ["save"]);
    context.historySessionRef.current = null;
    release();
    assert.equal(await pending, false);
    assert.equal(state.selected.stars, 5);
    assert.equal(await save(7, edited), false);
});
test("a new session cannot receive an older session's rating or pending cleanup", async () => {
    const { context, state, rate } = ratingContext();
    let finish;
    context.apiFetch = () => new Promise(resolve => { finish = resolve; });
    const pending = rate()(7, edited);
    const next = { pending: new Set([7]) };
    context.historySessionRef.current = next;
    finish({ ok: true, json: async () => ({ status: "success", data: edited }) });
    assert.equal(await pending, false);
    assert.equal(state.list[0].stars, 5);
    assert.equal(next.pending.has(7), true);
});
test("initial history load ignores a response from an unmounted session", async () => {
    let finish;
    const writes = [];
    const context = {
        historySessionRef: { current: {} }, apiFetch: () => new Promise(resolve => { finish = resolve; }),
        setCookingHistory: rows => writes.push(rows), toHistoryItem: value => value, console: { error() {} },
    };
    const pending = handler(appSource, "fetchHistory", context)();
    context.historySessionRef.current = null;
    finish({ ok: true, json: async () => ({ status: "success", data: [{ id: 7 }] }) });
    await pending;
    assert.deepEqual(writes, []);
});

function editorContext(ok, draft = { stars: 3, tag: null, feedback: "draft text" }) {
    const state = { editing: true, saving: false, error: "", saved: false, calls: [] };
    const context = {
        draft, item: { id: 7 }, savingRef: { current: false },
        setSaving: value => { state.saving = value; }, setError: value => { state.error = value; },
        setEditing: value => { state.editing = value; }, setSaved: value => { state.saved = value; },
        onRateRecipe: async (...args) => { state.calls.push(args); if (ok instanceof Error) throw ok; return ok; },
    };
    return { context, state, save: () => handler(detailSource, "saveRating", context)({ preventDefault() {} }) };
}
test("editor closes only on successful save; failed/throwing saves retain the edit for retry", async () => {
    for (const ok of [true, false, new Error("offline")]) {
        const { context, state, save } = editorContext(ok);
        await save();
        assert.equal(state.editing, ok !== true);
        assert.equal(state.saved, ok === true);
        assert.equal(state.saving, false);
        assert.equal(context.savingRef.current, false);
        assert.equal(context.draft.feedback, "draft text");
        assert.equal(Boolean(state.error), ok !== true);
    }
});
test("editor sends empty feedback as null and blocks invalid or duplicate submissions", async () => {
    const { state, save } = editorContext(true, { stars: 1, tag: null, feedback: "  " });
    await save();
    assert.deepEqual(state.calls[0], [7, { stars: 1, tag: null, feedback: null }]);
    for (const draft of [{ stars: 0, feedback: "" }, { stars: 6, feedback: "" }, { stars: 2, feedback: "x".repeat(241) }]) {
        const invalid = editorContext(true, draft);
        await invalid.save();
        assert.deepEqual(invalid.state.calls, []);
    }
    const duplicate = editorContext(true);
    duplicate.context.savingRef.current = true;
    await duplicate.save();
    assert.deepEqual(duplicate.state.calls, []);
});
test("cancel/back/tab leaving asks only for dirty edits and blocks leaving during save", () => {
    for (const [dirty, saving, expectedActions, expectedPrompts] of [
        [true, false, 0, 1], [false, false, 1, 0], [true, true, 0, 0],
    ]) {
        let actions = 0, prompts = 0, scrollLocked = false;
        const leave = handler(detailSource, "leave", {
            dirty, savingRef: { current: saving }, pendingLeaveRef: { current: null },
            discardDialogRef: { current: { showModal: () => { prompts++; } } },
            setConfirmingLeave: value => { scrollLocked = value; },
        });
        leave(() => { actions++; });
        assert.equal(actions, expectedActions);
        assert.equal(prompts, expectedPrompts);
        assert.equal(scrollLocked, expectedPrompts > 0);
    }
});
test("discard confirmation runs the requested navigation once and closes the dialog", () => {
    let navigations = 0, closes = 0;
    const context = { pendingLeaveRef: { current: () => { navigations++; } }, discardDialogRef: { current: { close: () => { closes++; } } } };
    const confirm = handler(detailSource, "confirmLeave", context);
    confirm();
    confirm();
    assert.equal(navigations, 1);
    assert.equal(closes, 2);
});

const bundle = await build({
    stdin: { contents: 'export { default as Detail } from "./src/pages/HistoryDetail.jsx"; export { default as Profile } from "./src/pages/Profile.jsx"; export { setLocale } from "./src/context/LocaleContext";', resolveDir: fileURLToPath(new URL("../", import.meta.url)), loader: "jsx" },
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", jsx: "automatic", loader: { ".png": "dataurl" },
    plugins: [{ name: "fixture-context", setup(build) {
        build.onResolve({ filter: /\/context\/(LocaleContext|AuthContext)$/ }, args => ({ path: args.path.includes("Locale") ? "locale" : "auth", namespace: "fixture" }));
        build.onLoad({ filter: /.*/, namespace: "fixture" }, args => ({ contents: args.path === "locale"
            ? 'import { translate } from "./translations.js"; let locale="th"; export function setLocale(value){locale=value} export function useLocale(){return {locale,t:(text,values)=>translate(text,locale,values)}}'
            : 'export function useAuth(){return {user:{id:1,locale:"th",email:"fixture@example.com"},apiFetch:async()=>{throw new Error("unexpected request")}}}',
        resolveDir: fileURLToPath(new URL("../src/utils/", import.meta.url)) }));
    } }],
});
const compiled = { exports: {} };
new Function("require", "module", "exports", bundle.outputFiles[0].text)(require, compiled, compiled.exports);
const { Detail, Profile, setLocale } = compiled.exports;
for (const locale of ["th", "en"]) {
    test(`${locale} Help keeps all guidance and the visible allergy caution`, () => {
        setLocale(locale);
        const markup = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(Profile, {
            view: "helps", activeTab: "me", historyBrowse: defaults, cookingHistory: [],
        })));
        assert.equal((markup.match(/<section/g) || []).length, 3);
        assert.ok(markup.includes('aria-labelledby="help-how-to"'));
        assert.ok(markup.includes('aria-labelledby="help-tips"'));
        assert.ok(markup.includes('aria-labelledby="help-terms"'));
        assert.ok(markup.includes(locale === "th" ? "โดยเฉพาะผู้ที่มีอาการแพ้อาหาร" : "allerg"));
        assert.doesNotMatch(markup, /<details/);
        assert.match(markup, /aria-label="(?:กลับ|Back)"/);
        assert.ok(markup.includes('aria-current="page"'));
    });
    test(`${locale} history controls expose search, rating filter, result counts and keyboard-operable entries`, () => {
        setLocale(locale);
        const markup = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(Profile, {
            view: "history", historyBrowse: { ...defaults, query: "หมู", rating: "5" }, cookingHistory: entries,
        })));
        assert.match(markup, /id="history-search"/);
        assert.match(markup, /id="history-rating-filter"/);
        assert.match(markup, /role="status"/);
        assert.match(markup, /<button[^>]+class="w-full text-left/);
        assert.ok(markup.includes("กะเพราหมู"));
        assert.ok(!markup.includes("Chicken Soup"));
        assert.ok(markup.includes(locale === "th" ? "พบ 1 รายการ" : "Results: 1"));
    });
    test(`${locale} detail shows full user feedback and a first-rating action without treating it as completed cooking`, () => {
        setLocale(locale);
        const feedback = "ความคิดเห็นยาว ".repeat(15);
        const rated = renderToStaticMarkup(createElement(Detail, { item: { ...entries[0], feedback, tag: "Great" } }));
        assert.ok(rated.includes(feedback));
        assert.ok(rated.includes(locale === "th" ? "แก้ไขคะแนน" : "Edit rating"));
        const unrated = renderToStaticMarkup(createElement(Detail, { item: entries[2] }));
        assert.ok(unrated.includes(locale === "th" ? "ให้คะแนนเมนูนี้" : "Rate this recipe"));
    });
}

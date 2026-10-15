import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";

const require = createRequire(import.meta.url);
const result = await build({
    stdin: { contents: 'export { default as Notifications } from "./src/pages/Notifications.jsx"; export { default as Bell } from "./src/components/NotificationBell.jsx"; export { default as Toast } from "./src/components/NotificationToast.jsx"; export { setLocale } from "./src/context/LocaleContext";', resolveDir: fileURLToPath(new URL("../", import.meta.url)), loader: "jsx" },
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", jsx: "automatic", loader: { ".png": "dataurl" },
    plugins: [{ name: "locale", setup(build) {
        build.onResolve({ filter: /\/context\/LocaleContext$/ }, () => ({ path: "locale", namespace: "test" }));
        build.onLoad({ filter: /.*/, namespace: "test" }, () => ({ contents: 'import { translate } from "./translations.js"; let locale="th"; export function setLocale(value){locale=value} export function useLocale(){return {locale,t:(text,values)=>translate(text,locale,values)}}', resolveDir: fileURLToPath(new URL("../src/utils/", import.meta.url)) }));
    } }],
});
const module = { exports: {} };
new Function("require", "module", "exports", result.outputFiles[0].text)(require, module, module.exports);
const { Notifications, Bell, Toast, setLocale } = module.exports;
const record = { id: 1, kind: "expiry_near", target_type: "ingredient", target_id: 1, payload: { name: "ไข่ไก่ขนาดใหญ่ที่บันทึกไว้สำหรับทำอาหารหลายมื้อ", expiry_date: "2026-10-18" }, created_at: "2026-10-15T03:00:00+00:00", read_at: null };

const appSource = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
const ast = require("@babel/parser").parse(appSource, { sourceType: "module", plugins: ["jsx"] });
const generateHandlers = [];
function visit(node) {
    if (!node || typeof node !== "object") return;
    if (node.type === "JSXAttribute" && node.name.name === "onGenerate") generateHandlers.push(node.value.expression);
    for (const value of Object.values(node)) {
        if (Array.isArray(value)) value.forEach(visit);
        else if (value && typeof value === "object") visit(value);
    }
}
visit(ast.program);
assert.equal(generateHandlers.length, 2);
const effectNodes = [];
function effects(node) {
    if (!node || typeof node !== "object") return;
    if (node.type === "CallExpression" && node.callee.name === "useEffect") effectNodes.push(node.arguments[0]);
    for (const value of Object.values(node)) {
        if (Array.isArray(value)) value.forEach(effects);
        else if (value && typeof value === "object") effects(value);
    }
}
effects(ast.program);
const reconcileEffect = effectNodes.find(node => appSource.slice(node.start, node.end).includes("signature === notificationFridgeRef.current"));
test("authoritative ingredient refetch does not collapse notification pages when IDs and expiry dates match", () => {
    const signatureRef = { current: "1:2026-10-18" };
    let checks = 0;
    const run = ingredients => new Function("userIngredients", "notificationFridgeRef", "setToastQueue", "syncNotifications", `return (${appSource.slice(reconcileEffect.start, reconcileEffect.end)})();`)(ingredients, signatureRef, update => update([]), async () => { checks++; });
    run([{ id: 1, expiry_date: "2026-10-18", name: "Changed name" }]);
    assert.equal(checks, 0);
    run([{ id: 1, expiry_date: "2026-10-19" }]);
    assert.equal(checks, 1);
    run([]);
    assert.equal(checks, 2);
});
const appComponent = ast.program.body.find(node => node.type === "FunctionDeclaration" && node.id.name === "App");
const openHandler = appComponent.body.body.flatMap(node => node.declarations || []).find(node => node.id.name === "openNotificationTarget").init;
test("opening a confirmed notification retains loaded pages and uses the authoritative unread count", async () => {
    let items = Array.from({ length: 25 }, (_, index) => ({ ...record, id: 25 - index }));
    const requested = [], counts = [], views = [];
    const context = {
        apiFetch: async path => { requested.push(path); return { ok: true, json: async () => path.endsWith("/read") ? { status: "success", data: { ...record, read_at: "2026-10-15T03:01:00Z" }, unread_count: 24 } : { status: "success", data: [{ id: 1, name: "Egg" }] } }; },
        notificationReadRef: { current: false }, notificationOwnerRef: { current: 1 }, notificationLoadRef: { current: 3 }, user: { id: 1 },
        notificationTabRef: { current: "unread" }, setNotificationPending: () => {}, setNotificationLoading: () => {},
        setNotificationCount: value => counts.push(value), setNotificationItems: update => { items = update(items); }, setToastQueue: update => update([]),
        setNotificationError: () => {}, setOpenedFromNotification: () => {}, setUserIngredients: () => {}, setSelectedIngredientDetail: () => {},
        setCurrentView: value => views.push(value),
    };
    const open = new Function(...Object.keys(context), `return ${appSource.slice(openHandler.start, openHandler.end)}`)(...Object.values(context));
    await open(record);
    assert.equal(items.length, 24);
    assert.deepEqual(items.map(item => item.id), Array.from({ length: 24 }, (_, index) => 25 - index));
    assert.deepEqual(counts, [24]);
    assert.deepEqual(requested, ["/api/notifications/1/read", "/api/user-ingredients"]);
    assert.deepEqual(views, ["ingredient-detail"]);
    assert.equal(context.notificationLoadRef.current, 4);
    assert.equal(context.notificationReadRef.current, false);
    const errors = [];
    context.setNotificationError = value => errors.push(value);
    context.apiFetch = async path => {
        if (!path.endsWith("/read")) throw new Error("synthetic target fetch failure");
        return { ok: true, json: async () => ({ status: "success", data: { ...record, read_at: "2026-10-15T03:01:00Z" }, unread_count: 24 }) };
    };
    const retryOpen = new Function(...Object.keys(context), `return ${appSource.slice(openHandler.start, openHandler.end)}`)(...Object.values(context));
    await retryOpen(record);
    assert.deepEqual(errors, ["รายการนี้เปลี่ยนแปลงหรือไม่พร้อมใช้งานแล้ว"]);
});
for (const [index, handler] of generateHandlers.entries()) {
    test(`actual generation handler ${index + 1} announces only confirmed history persistence`, async () => {
        for (const scenario of ["saved", "history-failed", "http-failed"]) {
            const notices = [], generated = [];
            const context = {
                apiFetch: async () => ({ ok: scenario !== "http-failed", json: async () => ({ status: "success", data: { history_id: scenario === "history-failed" ? null : 1 }, notification: { ...record, kind: "recipe_history_saved" } }) }),
                validateAllergyPreferences: async () => null, toPresenceIngredients: items => items,
                selectedRecipe: { name: "Omelet" }, selectedIngredients: [], locale: "th",
                setCurrentView: () => {}, setCookingSource: () => {}, setGenerateError: () => {}, setIsGenerating: () => {},
                setGeneratedRecipe: value => generated.push(value), setCookingHistory: () => {},
                enqueueNotification: value => notices.push(value), loadNotifications: () => {}, notificationTabRef: { current: "unread" },
                toUserFacingGenerateError: () => "Error", console: { error: () => {} },
            };
            const generate = new Function(...Object.keys(context), `return ${appSource.slice(handler.start, handler.end)}`)(...Object.values(context));
            await generate({}, []);
            assert.equal(notices.length, scenario === "saved" ? 1 : 0);
            assert.equal(generated.filter(Boolean).length, scenario === "http-failed" ? 0 : 1);
        }
    });
}

for (const locale of ["th", "en"]) {
    test(`notification list has readable dates, source name, unread semantics and pagination in ${locale}`, () => {
        setLocale(locale);
        const html = renderToStaticMarkup(createElement(Notifications, { items: [record], count: 25, tab: "unread", nextCursor: 1, activeTab: "home" }));
        assert.ok(html.includes(record.payload.name));
        assert.ok(html.includes('aria-pressed="true"'));
        assert.match(html, /datetime="2026-10-15T03:00:00\+00:00"/i);
        assert.ok(html.includes(locale === "en" ? "Read all" : "อ่านทั้งหมด"));
        assert.ok(html.includes(locale === "en" ? "Load more" : "โหลดเพิ่มเติม"));
        assert.ok(html.includes(locale === "en" ? "Recorded expiry:" : "วันที่บันทึก:"));
        assert.ok(!html.includes("Dates use Thailand time"));
        assert.ok(!html.includes("วันที่อ้างอิงเวลาไทย"));
    });
    test(`empty and loading/error states are distinct in ${locale}`, () => {
        setLocale(locale);
        const empty = renderToStaticMarkup(createElement(Notifications, { items: [], count: 0, tab: "unread" }));
        assert.ok(empty.includes(locale === "en" ? "No unread notifications" : "ไม่มีแจ้งเตือนที่ยังไม่อ่าน"));
        const error = renderToStaticMarkup(createElement(Notifications, { items: [], tab: "unread", error: "โหลดแจ้งเตือนไม่สำเร็จ กรุณาลองอีกครั้ง" }));
        assert.ok(error.includes('role="alert"'));
        assert.ok(!error.includes(locale === "en" ? "No unread notifications" : "ไม่มีแจ้งเตือนที่ยังไม่อ่าน"));
    });
    test(`bell speaks exact large count while the badge is bounded in ${locale}`, () => {
        setLocale(locale);
        const html = renderToStaticMarkup(createElement(Bell, { count: 125 }));
        assert.ok(html.includes("125"));
        assert.ok(html.includes("99+"));
        assert.ok(renderToStaticMarkup(createElement(Bell, {})).includes(locale === "en" ? 'aria-label="Notifications"' : 'aria-label="แจ้งเตือน"'));
    });
    test(`expiry summary and confirmed save toast carry different copy in ${locale}`, () => {
        setLocale(locale);
        const expiry = renderToStaticMarkup(createElement(Toast, { notice: { kind: "expiry_summary", items: [record, record] } }));
        assert.ok(expiry.includes('role="status"'));
        assert.ok(expiry.includes(locale === "en" ? "Check 2 ingredients" : "2 รายการ"));
        for (const kind of ["recipe_history_saved", "recipe_favorite_added"]) {
            const html = renderToStaticMarkup(createElement(Toast, { notice: { ...record, kind } }));
            assert.ok(html.includes(record.payload.name));
            assert.ok(html.includes(locale === "en" ? (kind === "recipe_history_saved" ? "saved to history" : "added to favorites") : (kind === "recipe_history_saved" ? "ในประวัติ" : "สูตรที่ชอบ")));
        }
    });
}

test("expiry rows use the matching ingredient photo and keep icons for missing photos and recipe saves", () => {
    const photo = "/images/ingredients/egg.png";
    const render = (item, ingredients) => renderToStaticMarkup(createElement(Notifications, { items: [item], ingredients, tab: "unread" }));
    assert.ok(render(record, [{ id: 1, image: photo }]).includes(`src="${photo}"`));
    for (const ingredients of [[], [{ id: 2, image: photo }], [{ id: 1, image: null }], [{ id: 1, image: "/images/No-image-available.png" }]]) {
        const html = render(record, ingredients);
        assert.ok(!html.includes(`src="${photo}"`));
        assert.ok(html.includes("lucide-clock"));
    }
    const recipe = render({ ...record, kind: "recipe_history_saved", target_type: "history" }, [{ id: 1, image: photo }]);
    assert.ok(!recipe.includes(`src="${photo}"`));
    assert.ok(recipe.includes("lucide-bookmark-check"));
});

test("only a single-ingredient expiry toast uses its photo; grouped reminders keep the bell", () => {
    const photo = "/images/ingredients/egg.png";
    const render = items => renderToStaticMarkup(createElement(Toast, { notice: { kind: "expiry_summary", items }, ingredients: [{ id: 1, image: photo }] }));
    assert.ok(render([record]).includes(`src="${photo}"`));
    assert.ok(!render([record, record]).includes(`src="${photo}"`));
    assert.ok(render([record, record]).includes("lucide-bell"));
});

import test from "node:test";
import assert from "node:assert/strict";
import { Buffer } from "node:buffer";
import { build } from "esbuild";

const compiled = await build({
    entryPoints: [new URL("../src/context/AuthContext.jsx", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1")],
    bundle: true, write: false, platform: "node", format: "esm", jsx: "automatic",
    plugins: [{ name: "auth-hooks", setup(builder) {
        builder.onResolve({ filter: /^react(?:\/jsx-runtime)?$/ }, args => ({ path: args.path, namespace: "test" }));
        builder.onLoad({ filter: /.*/, namespace: "test" }, args => ({ contents: args.path === "react/jsx-runtime" ? `
            export const jsx = (type, props) => ({ type, props });
        ` : `
            export const createContext = () => ({ Provider: "provider" });
            export const useCallback = fn => fn;
            export const useEffect = () => {};
            export function useState(initial) {
                const h = globalThis.__registrationHooks, i = h.cursor++;
                if (!(i in h.slots)) h.slots[i] = typeof initial === "function" ? initial() : initial;
                return [h.slots[i], value => { h.slots[i] = typeof value === "function" ? value(h.slots[i]) : value; }];
            }
            export const useRef = value => useState({ current: value })[0];
            export const useContext = () => null;
        ` }));
    } }],
});
const { AuthProvider } = await import(`data:text/javascript;base64,${Buffer.from(compiled.outputFiles[0].text).toString("base64")}`);

function setup(saved = null) {
    globalThis.__registrationHooks = { cursor: 0, slots: [] };
    const storage = new Map(saved ? [["homemade:registration", JSON.stringify(saved)]] : []);
    globalThis.sessionStorage = {
        getItem: key => storage.get(key) || null,
        setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key),
    };
    const requests = [];
    let respond = () => new Response(JSON.stringify({ status: "success", data: { email: "new@example.com", registration_token: "x".repeat(43) } }), { status: 202 });
    globalThis.fetch = async (path, init) => { requests.push({ path, body: JSON.parse(init.body) }); return respond(path, init); };
    return {
        storage, requests, respond: fn => { respond = fn; },
        render() { globalThis.__registrationHooks.cursor = 0; return AuthProvider({ children: null }).props.value; },
    };
}

test("registration stores only a challenge and waits for verification before login", async () => {
    const h = setup();
    assert.deepEqual(await h.render().register("new@example.com", "passwordA1", "passwordA1"), { success: true });
    const context = h.render();
    assert.equal(context.isAuthenticated, false);
    assert.equal(context.user, null);
    assert.equal(context.pendingRegistration.email, "new@example.com");
    assert.equal(h.requests.length, 1);
    assert.equal(h.requests[0].path, "/api/auth/register");
    const stored = JSON.parse(h.storage.get("homemade:registration"));
    assert.deepEqual(Object.keys(stored).sort(), ["email", "registration_token"]);
    assert.equal(JSON.stringify(stored).includes("passwordA1"), false);
});

test("verification authenticates and clears reload state without a login request", async () => {
    const h = setup({ email: "new@example.com", registration_token: "x".repeat(43) });
    h.respond(() => new Response(JSON.stringify({ status: "success", data: { id: 1, email: "new@example.com", locale: "th" } })));
    assert.equal((await h.render().verifyRegistration("123456")).success, true);
    assert.equal(h.render().isAuthenticated, true);
    assert.equal(h.render().user.id, 1);
    assert.equal(h.render().pendingRegistration, null);
    assert.equal(h.storage.size, 0);
    assert.equal(h.requests.length, 1);
    assert.equal(h.requests[0].path, "/api/auth/verify-registration");
    assert.equal("password" in h.requests[0].body, false);
});

test("bad code and delivery/rate failures keep challenge retryable", async () => {
    const h = setup({ email: "new@example.com", registration_token: "x".repeat(43) });
    h.respond(() => new Response(JSON.stringify({ detail: "Invalid or expired registration code" }), { status: 400 }));
    assert.equal((await h.render().verifyRegistration("000000")).success, false);
    assert.equal(h.render().isAuthenticated, false);
    assert.ok(h.render().pendingRegistration);
    h.respond(() => new Response(JSON.stringify({ detail: "limited" }), { status: 429 }));
    assert.match((await h.render().resendRegistration()).error, /1 ชั่วโมง/);
    h.respond(() => { throw new Error("offline"); });
    assert.equal((await h.render().resendRegistration()).success, false);
    assert.ok(h.render().pendingRegistration);
});

test("duplicate registration requests are blocked until prior request finishes", async () => {
    const h = setup();
    let release;
    h.respond(() => new Promise(resolve => { release = resolve; }));
    const context = h.render();
    const first = context.register("new@example.com", "passwordA1", "passwordA1");
    assert.equal((await context.register("new@example.com", "passwordB1", "passwordB1")).success, false);
    assert.equal(h.requests.length, 1);
    release(new Response(JSON.stringify({ status: "success", data: { email: "new@example.com", registration_token: "x".repeat(43) } }), { status: 202 }));
    assert.equal((await first).success, true);
});

test("malformed responses and invalid inputs never authenticate", async () => {
    const h = setup();
    const context = h.render();
    assert.equal((await context.register("bad", "passwordA1", "passwordA1")).success, false);
    assert.equal((await context.register("new@example.com", "ก".repeat(25), "ก".repeat(25))).success, false);
    assert.equal((await context.verifyRegistration("123456")).success, false);
    assert.equal(h.requests.length, 0);
    h.respond(() => new Response("not-json", { status: 202 }));
    assert.equal((await context.register("new@example.com", "passwordA1", "passwordA1")).success, false);
    assert.equal(h.render().pendingRegistration, null);
});

test("registration resend uses its token and never the reset endpoint", async () => {
    const h = setup({ email: "new@example.com", registration_token: "x".repeat(43) });
    h.respond(() => new Response(JSON.stringify({ status: "success" })));
    assert.equal((await h.render().resendRegistration()).success, true);
    assert.deepEqual(h.requests, [{ path: "/api/auth/resend-registration", body: { registration_token: "x".repeat(43) } }]);
});

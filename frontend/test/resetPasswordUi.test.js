import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const parse = createRequire(import.meta.url)("@babel/parser").parse;
const otpSource = readFileSync(new URL("../src/pages/auth/OtpVerify.jsx", import.meta.url), "utf8");
const confirmSource = readFileSync(new URL("../src/pages/auth/ResetPasswordConfirm.jsx", import.meta.url), "utf8");

function handler(source, name, context) {
    const ast = parse(source, { sourceType: "module", plugins: ["jsx"] });
    const component = ast.program.body.find(node => node.type === "ExportDefaultDeclaration").declaration;
    const node = component.body.body.flatMap(statement => statement.declarations || []).find(declaration => declaration.id.name === name).init;
    return new Function(...Object.keys(context), `return ${source.slice(node.start, node.end)}`)(...Object.values(context));
}

test("OTP input accepts an entire pasted/autofilled code and preserves leading zeroes", () => {
    for (const [input, expected] of [["000123", "000123"], ["012 345", "012345"], ["OTP: 012345", "012345"], ["12345678", "123456"], ["๑๒๓abc", ""], ["", ""]]) {
        let code, error;
        handler(otpSource, "handleChange", { OTP_LENGTH: 6, setCode: value => { code = value; }, setError: value => { error = value; } })(input);
        assert.equal(code, expected);
        assert.equal(error, "");
    }
});

test("OTP verification blocks incomplete/non-ASCII codes and simultaneous actions", async () => {
    for (const override of [{ code: "123" }, { code: "12345a" }, { code: "๑๒๓๔๕๖" }, { isSubmitting: true }, { isResending: true }]) {
        await handler(otpSource, "handleSubmit", {
            code: "000123", isSubmitting: false, isResending: false,
            setError: () => assert.fail("Should not change state"), setIsSubmitting: () => assert.fail("Should not submit"),
            verifyOtp: () => assert.fail("Should not verify"), navigate: () => assert.fail("Should not navigate"), ...override,
        })({ preventDefault() {} });
    }
});

test("OTP verification uses the complete code and only advances on success", async () => {
    for (const success of [false, true]) {
        const calls = [], errors = [], loading = [];
        await handler(otpSource, "handleSubmit", {
            code: "000123", isSubmitting: false, isResending: false,
            setError: value => errors.push(value), setIsSubmitting: value => loading.push(value),
            verifyOtp: async code => { assert.equal(code, "000123"); return { success, error: "invalid" }; },
            navigate: url => calls.push(url),
        })({ preventDefault() {} });
        assert.deepEqual(calls, success ? ["/reset-password/confirm"] : []);
        assert.deepEqual(loading, [true, false]);
        assert.deepEqual(errors, success ? [""] : ["", "invalid"]);
    }
});

test("resend respects cooldown and busy states", async () => {
    for (const override of [{ cooldown: 1 }, { isSubmitting: true }, { isResending: true }]) {
        await handler(otpSource, "handleResend", {
            cooldown: 0, isSubmitting: false, isResending: false,
            setError: () => assert.fail("No state change"), ...override,
        })();
    }
});

test("successful resend resets the code and cooldown; failed resend keeps the draft", async () => {
    for (const success of [false, true]) {
        const codes = [], countdowns = [], loading = [], errors = [];
        let focused = false;
        await handler(otpSource, "handleResend", {
            cooldown: 0, isSubmitting: false, isResending: false, RESEND_COOLDOWN_SECONDS: 60,
            setError: value => errors.push(value), setIsResending: value => loading.push(value),
            resendOtp: async () => ({ success, error: "unavailable" }),
            setCooldown: value => countdowns.push(value), setCode: value => codes.push(value),
            inputRef: { current: { focus: () => { focused = true; } } },
            requestAnimationFrame: callback => callback(),
        })();
        assert.deepEqual(loading, [true, false]);
        assert.deepEqual(codes, success ? [""] : []);
        assert.deepEqual(countdowns, success ? [60] : []);
        assert.equal(focused, success);
        assert.deepEqual(errors, success ? [""] : ["", "unavailable"]);
    }
});

test("password reset preserves failure and routes success to the existing login notice", async () => {
    for (const success of [false, true]) {
        const calls = [], errors = [], loading = [];
        await handler(confirmSource, "handleSubmit", {
            password: "qa-password", confirmPassword: "qa-password", isSubmitting: false,
            setError: value => errors.push(value), setIsSubmitting: value => loading.push(value),
            resetPassword: async (password, confirm) => { assert.equal(password, confirm); return { success, error: "expired" }; },
            navigate: (...args) => calls.push(args),
        })({ preventDefault() {} });
        assert.deepEqual(calls, success ? [["/login", { state: { message: "Password reset — please log in." } }]] : []);
        assert.deepEqual(loading, [true, false]);
        assert.deepEqual(errors, success ? [""] : ["", "expired"]);
    }
});

test("password reset does not submit again while waiting", async () => {
    await handler(confirmSource, "handleSubmit", { isSubmitting: true })({ preventDefault() {} });
});

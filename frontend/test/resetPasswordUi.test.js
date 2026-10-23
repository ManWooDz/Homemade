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
        let digits = Array(6).fill(""), error = "";
        handler(otpSource, "handleChange", {
            OTP_LENGTH: 6, inputRefs: { current: [] },
            setDigits: value => { digits = typeof value === "function" ? value(digits) : value; },
            setError: value => { error = value; },
        })(input);
        assert.equal(digits.join(""), expected);
        assert.equal(error, "");
    }
});

test("OTP digits retain their positions when editing and backspacing across cells", () => {
    let digits = ["0", "1", "2", "3", "4", "5"], focused;
    const context = {
        OTP_LENGTH: 6, setError() {},
        setDigits: value => { digits = typeof value === "function" ? value(digits) : value; },
        inputRefs: { current: Array.from({ length: 6 }, (_, i) => ({ focus() { focused = i; } })) },
    };
    const change = handler(otpSource, "handleChange", context);
    change("", 2);
    assert.deepEqual(digits, ["0", "1", "", "3", "4", "5"]);
    assert.equal(digits.join("").length, 5);
    let prevented = false;
    handler(otpSource, "handleKeyDown", { ...context, digits, handleChange: change })({
        key: "Backspace", preventDefault() { prevented = true; },
    }, 2);
    assert.equal(prevented, true);
    assert.equal(focused, 1);
    assert.deepEqual(digits, ["0", "", "", "3", "4", "5"]);
    change("7", 1);
    assert.equal(focused, 2);
    assert.deepEqual(digits, ["0", "7", "", "3", "4", "5"]);
    change("x", 2);
    assert.equal(digits[2], "");
    change("012345");
    assert.equal(digits.join(""), "012345");
    assert.equal(focused, 5);
    for (const [key, index, expected] of [["ArrowLeft", 3, 2], ["ArrowRight", 3, 4]]) {
        handler(otpSource, "handleKeyDown", { ...context, digits, handleChange: change })({ key, preventDefault() {} }, index);
        assert.equal(focused, expected);
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
    for (const [isRegistration, success] of [[false, false], [false, true], [true, false], [true, true]]) {
        const calls = [], errors = [], loading = [];
        await handler(otpSource, "handleSubmit", {
            code: "000123", isSubmitting: false, isResending: false,
            isRegistration, submittingRef: { current: false },
            setError: value => errors.push(value), setIsSubmitting: value => loading.push(value),
            verifyOtp: async code => { assert.equal(isRegistration, false); assert.equal(code, "000123"); return { success, error: "invalid" }; },
            verifyRegistration: async code => { assert.equal(isRegistration, true); assert.equal(code, "000123"); return { success, error: "invalid" }; },
            navigate: url => calls.push(url),
        })({ preventDefault() {} });
        assert.deepEqual(calls, success ? [isRegistration ? "/onboarding" : "/reset-password/confirm"] : []);
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
    for (const [isRegistration, success] of [[false, false], [false, true], [true, false], [true, true]]) {
        const codes = [], countdowns = [], loading = [], errors = [];
        let focused = false;
        await handler(otpSource, "handleResend", {
            cooldown: 0, isSubmitting: false, isResending: false, RESEND_COOLDOWN_SECONDS: 60,
            isRegistration,
            setError: value => errors.push(value), setIsResending: value => loading.push(value),
            resendOtp: async () => { assert.equal(isRegistration, false); return { success, error: "unavailable" }; },
            resendRegistration: async () => { assert.equal(isRegistration, true); return { success, error: "unavailable" }; },
            OTP_LENGTH: 6,
            setCooldown: value => countdowns.push(value), setDigits: value => codes.push(value.join("")),
            inputRefs: { current: [{ focus: () => { focused = true; } }] },
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

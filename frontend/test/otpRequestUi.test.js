import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const authContext = readFileSync(
    new URL("../src/context/AuthContext.jsx", import.meta.url),
    "utf8",
);
const emailPage = readFileSync(
    new URL("../src/pages/auth/ResetPasswordEmail.jsx", import.meta.url),
    "utf8",
);
const otpPage = readFileSync(
    new URL("../src/pages/auth/OtpVerify.jsx", import.meta.url),
    "utf8",
);

test("OTP screen opens without waiting for email delivery", () => {
    assert.match(emailPage, /void requestOtp\(email\);/);
    assert.ok(
        emailPage.indexOf("void requestOtp(email);") <
            emailPage.indexOf('navigate("/reset-password/otp")'),
    );
    assert.ok(
        authContext.indexOf("setPendingResetEmail(trimmedEmail)") <
            authContext.indexOf("await sendOtpRequest(trimmedEmail)"),
    );
});

test("duplicate OTP requests share one in-flight request", () => {
    assert.match(authContext, /otpRequestInFlightRef/);
    assert.match(authContext, /current\?\.email === email/);
});

test("OTP screen explains the wait and shows resend progress", () => {
    assert.match(otpPage, /รหัสอาจใช้เวลาสักครู่/);
    assert.match(otpPage, /isResending/);
    assert.match(otpPage, /กำลังส่งใหม่\.\.\./);
});

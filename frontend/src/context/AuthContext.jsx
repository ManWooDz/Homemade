import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import {
    isValidEmail,
    isValidPassword,
    passwordsMatch,
} from "../utils/authValidation";

const AuthContext = createContext(null);

function readPendingRegistration() {
    try {
        const saved = JSON.parse(sessionStorage.getItem("homemade:registration"));
        return typeof saved?.registration_token === "string" && typeof saved?.email === "string" ? saved : null;
    } catch {
        return null;
    }
}

async function registrationRequest(path, body) {
    const { response, networkError } = await safeFetch(path, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    if (networkError) return { success: false, error: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองอีกครั้ง" };
    const payload = await response.json().catch(() => null);
    if (!response.ok || payload?.status !== "success") {
        const errors = {
            "Invalid email": "Enter a valid email",
            "Password must be at least 8 characters": "Password must be at least 8 characters",
            "Password must be at most 72 bytes": "รหัสผ่านยาวเกินไป กรุณาใช้ไม่เกิน 72 ไบต์",
            "Email already registered": "Email already registered",
            "Invalid or expired registration code": "รหัสไม่ถูกต้องหรือหมดอายุ กรุณาส่งใหม่หรือเริ่มสมัครอีกครั้ง",
            "Could not send registration code": "ส่งรหัสยืนยันไม่สำเร็จ กรุณาลองอีกครั้ง",
        };
        return { success: false, error: response.status === 429
            ? "ส่งหรือกรอกรหัสถี่เกินไป กรุณารอสักครู่ หากยังไม่ได้ให้ลองใหม่ใน 1 ชั่วโมง"
            : Object.hasOwn(errors, payload?.detail) ? errors[payload.detail] : "Could not create account" };
    }
    return { success: true, data: payload.data };
}

// Never lets the caller's await reject — login/register/logout must
// always resolve to a {success, error?} shape (Login.jsx/Register.jsx
// have no try/finally around their `await`, so a rejected promise would
// leave the submit button stuck disabled forever).
async function safeFetch(path, options) {
    try {
        const response = await fetch(path, options);
        return { response, networkError: null };
    } catch (err) {
        return { response: null, networkError: err };
    }
}

export function AuthProvider({ children }) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [user, setUser] = useState(null);
    const [authLoading, setAuthLoading] = useState(true);
    const [pendingResetEmail, setPendingResetEmail] = useState(null);
    const [resetTicket, setResetTicket] = useState(null);
    const [pendingRegistration, setPendingRegistration] = useState(readPendingRegistration);

    const refreshInFlightRef = useRef(null);
    const otpRequestInFlightRef = useRef(null);
    const registrationInFlightRef = useRef(false);

    const savePendingRegistration = useCallback((value) => {
        setPendingRegistration(value);
        try {
            if (value) sessionStorage.setItem("homemade:registration", JSON.stringify(value));
            else sessionStorage.removeItem("homemade:registration");
        } catch { /* A blocked storage policy only disables reload recovery. */ }
    }, []);

    const clearAuthState = useCallback(() => {
        setIsAuthenticated(false);
        setUser(null);
    }, []);

    // Raw fetch only — must never be called from inside apiFetch, or a
    // 401 from /refresh itself would recurse.
    const sharedRefresh = useCallback(async () => {
        if (refreshInFlightRef.current) {
            return refreshInFlightRef.current;
        }
        const promise = (async () => {
            try {
                const res = await fetch("/api/auth/refresh", { method: "POST" });
                return res.ok;
            } catch {
                return false;
            }
        })();
        refreshInFlightRef.current = promise;
        try {
            return await promise;
        } finally {
            refreshInFlightRef.current = null;
        }
    }, []);

    // Only for non-auth-endpoint calls (bootstrap /me now; Phase-2
    // endpoints later). login/register/logout use raw fetch directly —
    // that's what keeps a wrong password at /login from ever triggering
    // a refresh attempt, with no path-exclusion list needed. A network
    // error here propagates to the caller (not a definitive 401) — only
    // an actual 401 response clears auth state.
    const apiFetch = useCallback(
        async (path, options) => {
            let res = await fetch(path, options);
            if (res.status === 401) {
                const refreshed = await sharedRefresh();
                if (!refreshed) {
                    clearAuthState();
                    return res;
                }
                res = await fetch(path, options);
                if (res.status === 401) {
                    clearAuthState();
                }
            }
            return res;
        },
        [sharedRefresh, clearAuthState]
    );

    const login = useCallback(async (email, password) => {
        if (!isValidEmail(email) || !password) {
            return { success: false, error: "Enter a valid email and password" };
        }
        const body = new URLSearchParams({ username: email.trim(), password });
        const { response, networkError } = await safeFetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body,
        });
        if (networkError) {
            return { success: false, error: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองอีกครั้ง" };
        }
        if (!response.ok) {
            return { success: false, error: "Enter a valid email and password" };
        }
        let payload;
        try {
            payload = await response.json();
        } catch {
            return { success: false, error: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองอีกครั้ง" };
        }
        setIsAuthenticated(true);
        setUser(payload.data);
        return { success: true };
    }, []);

    const register = useCallback(
        async (email, password, confirmPassword) => {
            if (!isValidEmail(email)) {
                return { success: false, error: "Enter a valid email" };
            }
            if (!isValidPassword(password)) {
                return { success: false, error: "Password must be at least 8 characters" };
            }
            if (!passwordsMatch(password, confirmPassword)) {
                return { success: false, error: "Passwords do not match" };
            }
            if (new TextEncoder().encode(password).length > 72) {
                return { success: false, error: "รหัสผ่านยาวเกินไป กรุณาใช้ไม่เกิน 72 ไบต์" };
            }
            if (registrationInFlightRef.current) return { success: false, error: "กรุณารอคำขอก่อนหน้าสักครู่" };
            registrationInFlightRef.current = true;
            try {
                const result = await registrationRequest("/api/auth/register", { email: email.trim(), password });
                if (!result.success) return result;
                if (typeof result.data?.registration_token !== "string" || typeof result.data?.email !== "string") {
                    return { success: false, error: "Could not create account" };
                }
                savePendingRegistration(result.data);
                return { success: true };
            } finally {
                registrationInFlightRef.current = false;
            }
        },
        [savePendingRegistration]
    );

    const verifyRegistration = useCallback(async (code) => {
        if (!pendingRegistration) return { success: false, error: "Session expired — start over" };
        if (!/^[0-9]{6}$/.test(code)) return { success: false, error: "Enter all 6 digits" };
        if (registrationInFlightRef.current) return { success: false, error: "กรุณารอคำขอก่อนหน้าสักครู่" };
        registrationInFlightRef.current = true;
        try {
            const result = await registrationRequest("/api/auth/verify-registration", {
                registration_token: pendingRegistration.registration_token, code,
            });
            if (!result.success) return result;
            if (!result.data?.id || result.data.email !== pendingRegistration.email) {
                return { success: false, error: "Could not create account" };
            }
            setIsAuthenticated(true);
            setUser(result.data);
            savePendingRegistration(null);
            return { success: true };
        } finally {
            registrationInFlightRef.current = false;
        }
    }, [pendingRegistration, savePendingRegistration]);

    const resendRegistration = useCallback(async () => {
        if (!pendingRegistration) return { success: false, error: "Session expired — start over" };
        if (registrationInFlightRef.current) return { success: false, error: "กรุณารอคำขอก่อนหน้าสักครู่" };
        registrationInFlightRef.current = true;
        try {
            return await registrationRequest("/api/auth/resend-registration", {
                registration_token: pendingRegistration.registration_token,
            });
        } finally {
            registrationInFlightRef.current = false;
        }
    }, [pendingRegistration]);

    const sendOtpRequest = useCallback(async (email) => {
        if (otpRequestInFlightRef.current?.email === email) {
            return otpRequestInFlightRef.current.promise;
        }
        const promise = safeFetch("/api/auth/forgot-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email }),
        }).then(({ response, networkError }) => !networkError && response.ok);
        const flight = { email, promise };
        otpRequestInFlightRef.current = flight;
        try {
            return await promise;
        } finally {
            if (otpRequestInFlightRef.current === flight) {
                otpRequestInFlightRef.current = null;
            }
        }
    }, []);

    const requestOtp = useCallback(async (email) => {
        if (!isValidEmail(email)) {
            return { success: false, error: "Enter a valid email" };
        }
        const trimmedEmail = email.trim();
        setPendingResetEmail(trimmedEmail);
        setResetTicket(null);
        const success = await sendOtpRequest(trimmedEmail);
        return success
            ? { success: true }
            : { success: false, error: "ส่งคำขอไม่สำเร็จ กรุณาลองอีกครั้ง" };
    }, [sendOtpRequest]);

    const resendOtp = useCallback(async () => {
        if (!pendingResetEmail) {
            return { success: false, error: "Session expired — start over" };
        }
        const success = await sendOtpRequest(pendingResetEmail);
        return success
            ? { success: true }
            : { success: false, error: "ส่งรหัสใหม่ไม่สำเร็จ กรุณาลองอีกครั้ง" };
    }, [pendingResetEmail, sendOtpRequest]);

    const verifyOtp = useCallback(
        async (code) => {
            if (!code || code.length !== 6) {
                return { success: false, error: "Enter all 6 digits" };
            }
            if (!pendingResetEmail) {
                return { success: false, error: "Session expired — start over" };
            }
            const { response, networkError } = await safeFetch("/api/auth/verify-otp", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: pendingResetEmail, code }),
            });
            if (networkError || !response.ok) {
                return { success: false, error: "รหัสไม่ถูกต้องหรือหมดอายุ" };
            }
            let payload;
            try {
                payload = await response.json();
            } catch {
                return { success: false, error: "เกิดข้อผิดพลาด กรุณาลองอีกครั้ง" };
            }
            setResetTicket(payload.data.reset_ticket);
            return { success: true };
        },
        [pendingResetEmail]
    );

    const resetPassword = useCallback(
        async (newPassword, confirmPassword) => {
            if (!resetTicket) {
                return { success: false, error: "Verify your code first" };
            }
            if (!isValidPassword(newPassword)) {
                return { success: false, error: "Password must be at least 8 characters" };
            }
            if (!passwordsMatch(newPassword, confirmPassword)) {
                return { success: false, error: "Passwords do not match" };
            }
            const { response, networkError } = await safeFetch("/api/auth/reset-password", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ reset_ticket: resetTicket, new_password: newPassword }),
            });
            if (networkError || !response.ok) {
                return { success: false, error: "เปลี่ยนรหัสผ่านไม่สำเร็จ ลิงก์อาจหมดอายุ" };
            }
            setPendingResetEmail(null);
            setResetTicket(null);
            return { success: true };
        },
        [resetTicket]
    );

    const logout = useCallback(async () => {
        const { response, networkError } = await safeFetch("/api/auth/logout", { method: "POST" });
        if (networkError || !response.ok) {
            return {
                success: false,
                error: "ออกจากระบบบนเซิร์ฟเวอร์ไม่สำเร็จ กรุณาลองอีกครั้ง",
            };
        }
        clearAuthState();
        return { success: true };
    }, [clearAuthState]);

    const bootstrap = useCallback(async () => {
        try {
            const res = await apiFetch("/api/auth/me");
            if (res.ok) {
                const payload = await res.json();
                setIsAuthenticated(true);
                setUser(payload.data);
            } else if (res.status === 401) {
                clearAuthState();
            }
            // any other non-ok status: leave auth state as-is, just stop loading
        } catch {
            // Network error during bootstrap — session status unknown;
            // do not falsely claim logged-out, just stop loading.
        } finally {
            setAuthLoading(false);
        }
    }, [apiFetch, clearAuthState]);

    useEffect(() => {
        bootstrap();
    }, [bootstrap]);

    const saveUser = async (path, options) => {
        const ownerId = user?.id;
        try {
            const response = await apiFetch(path, options);
            const payload = await response.json();
            if (!response.ok || payload.status !== "success" || payload.data?.id !== ownerId || !["th", "en"].includes(payload.data.locale)) {
                return { success: false, code: payload.code || "profile_save_failed" };
            }
            if (options.signal?.aborted) return { success: false, code: "profile_save_failed" };
            setUser(current => current?.id !== ownerId ? current : path.endsWith("/language")
                ? { ...current, locale: payload.data.locale }
                : { ...current, display_name: payload.data.display_name, has_avatar: payload.data.has_avatar });
            return { success: true, data: payload.data };
        } catch {
            return { success: false, code: "profile_save_failed" };
        }
    };

    const updateProfile = (body, signal) => saveUser("/api/user-profile", { method: "PUT", body, signal });
    const updateLanguage = locale => saveUser("/api/user-profile/language", {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ locale }),
    });

    const value = {
        isAuthenticated,
        authLoading,
        user,
        pendingResetEmail,
        pendingRegistration,
        verifyRegistration,
        resendRegistration,
        resetTicket,
        login,
        register,
        requestOtp,
        resendOtp,
        verifyOtp,
        resetPassword,
        logout,
        apiFetch,
        updateProfile,
        updateLanguage,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return ctx;
}

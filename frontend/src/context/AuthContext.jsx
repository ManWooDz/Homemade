import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import {
    isValidEmail,
    isValidPassword,
    passwordsMatch,
} from "../utils/authValidation";

const AuthContext = createContext(null);

const MOCK_DELAY_MS = 600;

function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
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
    const [otpVerified, setOtpVerified] = useState(false);

    const refreshInFlightRef = useRef(null);

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
            const { response, networkError } = await safeFetch("/api/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: email.trim(), password }),
            });
            if (networkError) {
                return { success: false, error: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองอีกครั้ง" };
            }
            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                return { success: false, error: payload.detail || "Could not create account" };
            }
            // Account now exists server-side. If auto-login fails below,
            // never suggest registering again — a second register would
            // just hit "Email already registered".
            const loginResult = await login(email, password);
            if (!loginResult.success) {
                return {
                    success: false,
                    error:
                        "สร้างบัญชีแล้ว แต่เข้าสู่ระบบอัตโนมัติไม่สำเร็จ กรุณาเข้าสู่ระบบด้วยตนเอง",
                };
            }
            return { success: true };
        },
        [login]
    );

    const requestOtp = useCallback(async (email) => {
        await delay(MOCK_DELAY_MS);
        if (!isValidEmail(email)) {
            return { success: false, error: "Enter a valid email" };
        }
        setPendingResetEmail(email.trim());
        setOtpVerified(false);
        return { success: true };
    }, []);

    const resendOtp = useCallback(async () => {
        await delay(MOCK_DELAY_MS);
        return { success: true };
    }, []);

    const verifyOtp = useCallback(async (code) => {
        await delay(MOCK_DELAY_MS);
        if (!code || code.length !== 6) {
            return { success: false, error: "Enter all 6 digits" };
        }
        setOtpVerified(true);
        return { success: true };
    }, []);

    const resetPassword = useCallback(
        async (newPassword, confirmPassword) => {
            await delay(MOCK_DELAY_MS);
            if (!otpVerified) {
                return { success: false, error: "Verify your code first" };
            }
            if (!isValidPassword(newPassword)) {
                return { success: false, error: "Password must be at least 8 characters" };
            }
            if (!passwordsMatch(newPassword, confirmPassword)) {
                return { success: false, error: "Passwords do not match" };
            }
            setPendingResetEmail(null);
            setOtpVerified(false);
            return { success: true };
        },
        [otpVerified]
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

    const value = {
        isAuthenticated,
        authLoading,
        user,
        pendingResetEmail,
        otpVerified,
        login,
        register,
        requestOtp,
        resendOtp,
        verifyOtp,
        resetPassword,
        logout,
        apiFetch,
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

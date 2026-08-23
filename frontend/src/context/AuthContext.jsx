import { createContext, useContext, useState, useCallback } from "react";
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

export function AuthProvider({ children }) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [user, setUser] = useState(null);
    const [pendingResetEmail, setPendingResetEmail] = useState(null);
    const [otpVerified, setOtpVerified] = useState(false);

    const login = useCallback(async (email, password) => {
        await delay(MOCK_DELAY_MS);
        if (!isValidEmail(email) || !password) {
            return { success: false, error: "Enter a valid email and password" };
        }
        setIsAuthenticated(true);
        setUser({ email: email.trim() });
        return { success: true };
    }, []);

    const register = useCallback(async (email, password, confirmPassword) => {
        await delay(MOCK_DELAY_MS);
        if (!isValidEmail(email)) {
            return { success: false, error: "Enter a valid email" };
        }
        if (!isValidPassword(password)) {
            return { success: false, error: "Password must be at least 8 characters" };
        }
        if (!passwordsMatch(password, confirmPassword)) {
            return { success: false, error: "Passwords do not match" };
        }
        return { success: true };
    }, []);

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

    const resetPassword = useCallback(async (newPassword, confirmPassword) => {
        await delay(MOCK_DELAY_MS);
        if (!isValidPassword(newPassword)) {
            return { success: false, error: "Password must be at least 8 characters" };
        }
        if (!passwordsMatch(newPassword, confirmPassword)) {
            return { success: false, error: "Passwords do not match" };
        }
        setPendingResetEmail(null);
        setOtpVerified(false);
        return { success: true };
    }, []);

    const logout = useCallback(() => {
        setIsAuthenticated(false);
        setUser(null);
    }, []);

    const value = {
        isAuthenticated,
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
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return ctx;
}

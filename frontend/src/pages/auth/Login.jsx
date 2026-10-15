import { useLocale } from "../../context/LocaleContext";
import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import HeaderLogo from "../../components/HeaderLogo";
import PasswordInput from "../../components/PasswordInput";
import { useAuth } from "../../context/AuthContext";

export default function Login() {
    const { t } = useLocale();
    const navigate = useNavigate();
    const location = useLocation();
    const { login } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const successMessage = location.state?.message;

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (isSubmitting) return;
        setError("");
        setIsSubmitting(true);
        const result = await login(email, password);
        setIsSubmitting(false);
        if (result.success) {
            navigate("/home", { replace: true });
        } else {
            setError(result.error);
        }
    };

    return (
        <div className="auth-screen h-dvh bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative shadow-2xl overflow-y-auto">
                <main className="w-full min-h-full px-6 py-8 bg-background-primary flex flex-col justify-center items-center">
                    <div className="w-full flex flex-col items-center gap-6">
                        <HeaderLogo size="h-28" />
                        <h1 className="text-h2 font-bold text-text-black">{t("Login")}</h1>

                        {successMessage && (
                            <p role="status" className="w-full text-body-medium text-green-800 bg-green-50 border border-green-200 rounded-2xl px-4 py-3 text-center">
                                {t(successMessage)}
                            </p>
                        )}

                        <form
                            onSubmit={handleSubmit}
                            aria-busy={isSubmitting}
                            className="w-full h-auto flex flex-col justify-start items-center gap-4"
                        >
                            <div className="w-full h-auto flex flex-col justify-start items-center gap-3">
                                <label htmlFor="login-email" className="auth-label">{t("Email")}</label>
                                <input
                                    id="login-email"
                                    name="email"
                                    autoComplete="email"
                                    autoCapitalize="none"
                                    type="email"
                                    placeholder={t("Email")}
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="w-full h-11 px-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands"
                                    required
                                />
                                <label htmlFor="login-password" className="auth-label">{t("Password")}</label>
                                <PasswordInput
                                    id="login-password"
                                    name="password"
                                    autoComplete="current-password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder={t("Password")}
                                    required
                                />
                                <div className="w-full flex justify-end">
                                    <Link
                                        to="/reset-password"
                                        className="min-h-11 inline-flex items-center text-text-tertiary text-body-medium hover:underline"
                                    >{t("Forgot password?")}</Link>
                                </div>
                            </div>

                            {error && <p role="alert" className="w-full text-body-medium text-red-700">{t(error)}</p>}

                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="w-full h-11 mt-2 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-all cursor-pointer disabled:opacity-50"
                            >
                                {isSubmitting ? t("กำลังเข้าสู่ระบบ...") : t("Login")}
                            </button>

                            <div className="w-full flex flex-wrap gap-x-2 justify-center items-center text-body-medium mt-1">
                                <span className="text-text-neutral">{t("ยังไม่มีบัญชี?")}</span>
                                <Link
                                    to="/register"
                                    className="min-h-11 inline-flex items-center text-text-brands font-semibold hover:underline"
                                >{t("Sign Up")}</Link>
                            </div>
                        </form>
                    </div>
                </main>
            </div>
        </div>
    );
}

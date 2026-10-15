import { useLocale } from "../../context/LocaleContext";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import HeaderLogo from "../../components/HeaderLogo";
import BackButton from "../../components/BackButton";
import PasswordInput from "../../components/PasswordInput";
import { useAuth } from "../../context/AuthContext";

export default function Register() {
    const { t } = useLocale();
    const navigate = useNavigate();
    const { register } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (isSubmitting) return;
        setError("");
        setIsSubmitting(true);
        const result = await register(email, password, confirmPassword);
        setIsSubmitting(false);
        if (result.success) {
            navigate("/onboarding");
        } else {
            setError(result.error);
        }
    };

    return (
        <div className="auth-screen h-dvh bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative shadow-2xl overflow-y-auto">
                <main className="w-full min-h-full px-6 pt-6 pb-8 bg-background-primary flex flex-col items-center">
                    <HeaderLogo />

                    <div className="w-full flex justify-start items-center">
                        <BackButton to="/login" size="w-11 h-11" />
                    </div>

                    <form
                        onSubmit={handleSubmit}
                        aria-busy={isSubmitting}
                        className="w-full flex flex-col items-center mt-6"
                    >
                        <h1 className="text-h2 font-bold text-text-black text-center mb-4">{t("Sign Up")}</h1>

                        <div className="w-full flex flex-col gap-3">
                            <label htmlFor="register-email" className="auth-label">{t("Email")}</label>
                            <input
                                id="register-email"
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

                            <label htmlFor="register-password" className="auth-label">{t("Password")}</label>
                            <PasswordInput
                                id="register-password"
                                name="password"
                                autoComplete="new-password"
                                minLength={8}
                                aria-describedby="password-hint"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder={t("Password")}
                                required
                            />

                            <p id="password-hint" className="text-caption text-text-neutral">{t("Password must be at least 8 characters")}</p>
                            <label htmlFor="register-confirm-password" className="auth-label">{t("Confirm password")}</label>
                            <PasswordInput
                                id="register-confirm-password"
                                name="confirm-password"
                                autoComplete="new-password"
                                minLength={8}
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder={t("Confirm password")}
                                required
                            />
                        </div>

                        {error && (
                            <p role="alert" className="w-full text-body-medium text-red-700 mt-4">{t(error)}</p>
                        )}

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full h-11 mt-6 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-colors cursor-pointer disabled:opacity-50"
                        >
                            {isSubmitting ? t("Creating account...") : t("Sign Up")}
                        </button>
                        <div className="flex flex-wrap justify-center items-center gap-x-2 mt-4 text-body-medium">
                            <span className="text-text-neutral">{t("มีบัญชีแล้ว?")}</span>
                            <Link to="/login" className="min-h-11 inline-flex items-center text-text-brands font-semibold hover:underline">{t("Login")}</Link>
                        </div>
                    </form>
                </main>
            </div>
        </div>
    );
}

import { useLocale } from "../../context/LocaleContext";
import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import HeaderLogo from "../../components/HeaderLogo";
import BackButton from "../../components/BackButton";
import PasswordInput from "../../components/PasswordInput";
import { useAuth } from "../../context/AuthContext";

export default function ResetPasswordConfirm() {
    const { t } = useLocale();
    const navigate = useNavigate();
    const { resetTicket, resetPassword } = useAuth();
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    // resetPassword() clears resetTicket as part of its own success cleanup, which would
    // otherwise race this guard's redirect against the page's own post-submit navigate().
    // Check the flag once at mount instead of reacting to it.
    const resetTicketAtMount = useRef(resetTicket);

    useEffect(() => {
        if (!resetTicketAtMount.current) {
            navigate("/reset-password", { replace: true });
        }
    }, [navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (isSubmitting) return;
        setError("");
        setIsSubmitting(true);
        const result = await resetPassword(password, confirmPassword);
        setIsSubmitting(false);
        if (result.success) {
            navigate("/login", { state: { message: "Password reset — please log in." } });
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
                        <BackButton to="/reset-password/otp" size="w-11 h-11" disabled={isSubmitting} />
                    </div>

                    <form
                        onSubmit={handleSubmit}
                        aria-busy={isSubmitting}
                        className="w-full flex flex-col items-center mt-6"
                    >
                        <h1 className="w-full text-h2 font-semibold text-text-black text-left mb-4">{t("Reset Password")}</h1>

                        <fieldset disabled={isSubmitting} className="w-full min-w-0 flex flex-col gap-3">
                            <label htmlFor="reset-password" className="auth-label">{t("New Password")}</label>
                            <PasswordInput
                                id="reset-password"
                                name="new-password"
                                autoComplete="new-password"
                                minLength={8}
                                aria-describedby="reset-password-hint"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder={t("New Password")}
                                required
                            />

                            <p id="reset-password-hint" className="text-caption text-text-neutral">{t("Password must be at least 8 characters")}</p>
                            <label htmlFor="reset-confirm-password" className="auth-label">{t("Confirm password")}</label>
                            <PasswordInput
                                id="reset-confirm-password"
                                name="confirm-password"
                                autoComplete="new-password"
                                minLength={8}
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder={t("Confirm password")}
                                required
                            />
                        </fieldset>

                        {error && (
                            <p role="alert" className="w-full text-body-medium text-red-700 mt-4">{t(error)}</p>
                        )}

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full h-11 mt-6 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-all cursor-pointer disabled:opacity-50"
                        >
                            {isSubmitting ? t("Saving...") : t("Confirm")}
                        </button>
                    </form>
                </main>
            </div>
        </div>
    );
}

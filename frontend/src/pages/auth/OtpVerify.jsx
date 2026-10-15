import { useLocale } from "../../context/LocaleContext";
import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import HeaderLogo from "../../components/HeaderLogo";
import BackButton from "../../components/BackButton";
import { useAuth } from "../../context/AuthContext";

const OTP_LENGTH = 6;
const RESEND_COOLDOWN_SECONDS = 60;

export default function OtpVerify() {
    const { t } = useLocale();
    const navigate = useNavigate();
    const { pendingResetEmail, verifyOtp, resendOtp } = useAuth();
    const [code, setCode] = useState("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isResending, setIsResending] = useState(false);
    const [cooldown, setCooldown] = useState(RESEND_COOLDOWN_SECONDS);
    const inputRef = useRef(null);

    useEffect(() => {
        if (!pendingResetEmail) {
            navigate("/reset-password", { replace: true });
        }
    }, [pendingResetEmail, navigate]);

    useEffect(() => {
        if (cooldown <= 0) return;
        const timer = setTimeout(() => setCooldown((s) => s - 1), 1000);
        return () => clearTimeout(timer);
    }, [cooldown]);

    const handleChange = (value) => {
        setCode(value.replace(/[^0-9]/g, "").slice(0, OTP_LENGTH));
        setError("");
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (isSubmitting || isResending || !/^[0-9]{6}$/.test(code)) return;
        setError("");
        setIsSubmitting(true);
        const result = await verifyOtp(code);
        setIsSubmitting(false);
        if (result.success) {
            navigate("/reset-password/confirm");
        } else {
            setError(result.error);
        }
    };

    const handleResend = async () => {
        if (cooldown > 0 || isResending || isSubmitting) return;
        setError("");
        setIsResending(true);
        try {
            const result = await resendOtp();
            if (!result.success) {
                setError(result.error);
                return;
            }
            setCooldown(RESEND_COOLDOWN_SECONDS);
            setCode("");
            requestAnimationFrame(() => inputRef.current?.focus());
        } finally {
            setIsResending(false);
        }
    };

    return (
        <div className="auth-screen h-dvh bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative shadow-2xl overflow-y-auto overflow-x-hidden">
                <main className="w-full min-h-full px-6 pt-6 pb-8 bg-background-primary flex flex-col items-center">
                    <HeaderLogo />

                    <div className="w-full flex justify-start items-center">
                        <BackButton to="/reset-password" size="w-11 h-11" disabled={isSubmitting || isResending} />
                    </div>

                    <form
                        onSubmit={handleSubmit}
                        aria-busy={isSubmitting || isResending}
                        className="w-full flex flex-col items-center mt-6"
                    >
                        <h1 className="w-full text-h2 font-semibold text-text-black text-left mb-4">{t("Enter OTP")}</h1>

                        <p className="w-full text-body-medium text-text-tertiary break-words mb-2">{t("กรอกรหัสสำหรับอีเมล {email}", { email: pendingResetEmail })}</p>
                        <p id="otp-hint" className="w-full text-body-medium text-text-neutral mb-6">{t("รหัสอาจใช้เวลาสักครู่ หากยังไม่ได้รับ ให้รอหมดเวลานับถอยหลังแล้วกดส่งใหม่")}</p>

                        <div className="w-full flex flex-col items-center gap-3">
                            <label htmlFor="otp-code" className="auth-label">{t("รหัส OTP 6 หลัก")}</label>
                            <input
                                id="otp-code"
                                name="code"
                                ref={inputRef}
                                type="text"
                                inputMode="numeric"
                                autoComplete="one-time-code"
                                maxLength={OTP_LENGTH}
                                pattern="[0-9]{6}"
                                required
                                value={code}
                                disabled={isSubmitting || isResending}
                                aria-describedby={error ? "otp-hint otp-error" : "otp-hint"}
                                onChange={(e) => handleChange(e.target.value)}
                                onPaste={(e) => { e.preventDefault(); handleChange(e.clipboardData.getData("text")); }}
                                className="w-full h-14 bg-forms-otp-fill-default border border-stroke-text-field text-center text-2xl tracking-[0.35em] tabular-nums text-text-black rounded-xl focus:outline-none focus:bg-forms-otp-fill-filled focus:border-stroke-brands"
                            />

                            <button
                                type="button"
                                onClick={handleResend}
                                disabled={cooldown > 0 || isResending || isSubmitting}
                                className="h-11 px-4 bg-button-neutral rounded-full border border-stroke-brands text-text-brands text-body-medium font-normal flex justify-center items-center whitespace-nowrap cursor-pointer hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isResending
                                    ? t("กำลังส่งใหม่...")
                                    : cooldown > 0
                                      ? t("ส่งใหม่ได้ใน {seconds} วินาที", { seconds: cooldown })
                                      : t("ส่งใหม่")}
                            </button>
                        </div>

                        {error && (
                            <p id="otp-error" role="alert" className="w-full text-body-medium text-red-700 mt-4">{t(error)}</p>
                        )}

                        <button
                            type="submit"
                            disabled={isSubmitting || isResending || code.length !== OTP_LENGTH}
                            className="w-full h-11 mt-6 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-colors cursor-pointer disabled:opacity-50"
                        >
                            {isSubmitting ? t("Verifying...") : t("Verify")}
                        </button>
                    </form>
                </main>
            </div>
        </div>
    );
}

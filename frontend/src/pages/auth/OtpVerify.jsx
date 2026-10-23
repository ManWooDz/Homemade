import { useLocale } from "../../context/LocaleContext";
import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import HeaderLogo from "../../components/HeaderLogo";
import BackButton from "../../components/BackButton";
import { useAuth } from "../../context/AuthContext";

const OTP_LENGTH = 6;
const RESEND_COOLDOWN_SECONDS = 60;

export default function OtpVerify({ purpose = "reset" }) {
    const { t } = useLocale();
    const navigate = useNavigate();
    const { pendingResetEmail, verifyOtp, resendOtp, pendingRegistration, verifyRegistration, resendRegistration } = useAuth();
    const isRegistration = purpose === "registration";
    const email = isRegistration ? pendingRegistration?.email : pendingResetEmail;
    const backTo = isRegistration ? "/register" : "/reset-password";
    const [digits, setDigits] = useState(Array(OTP_LENGTH).fill(""));
    const code = digits.join("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isResending, setIsResending] = useState(false);
    const [cooldown, setCooldown] = useState(RESEND_COOLDOWN_SECONDS);
    const inputRefs = useRef([]);
    const submittingRef = useRef(false);

    useEffect(() => {
        if (!email && !submittingRef.current) {
            navigate(backTo, { replace: true });
        }
    }, [email, backTo, navigate]);

    useEffect(() => {
        if (cooldown <= 0) return;
        const timer = setTimeout(() => setCooldown((s) => s - 1), 1000);
        return () => clearTimeout(timer);
    }, [cooldown]);

    const handleChange = (value, index = 0) => {
        const numbers = value.replace(/[^0-9]/g, "").slice(0, OTP_LENGTH);
        if (value && !numbers) return;
        if (numbers.length > 1) {
            setDigits(Array.from({ length: OTP_LENGTH }, (_, i) => numbers[i] || ""));
            inputRefs.current[Math.min(numbers.length, OTP_LENGTH - 1)]?.focus();
        } else {
            setDigits((current) => current.map((digit, i) => i === index ? numbers : digit));
            if (numbers) inputRefs.current[index + 1]?.focus();
        }
        setError("");
    };

    const handleKeyDown = (e, index) => {
        if (e.key === "Backspace" && !digits[index] && index > 0) {
            e.preventDefault();
            handleChange("", index - 1);
            inputRefs.current[index - 1]?.focus();
        } else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
            e.preventDefault();
            inputRefs.current[index + (e.key === "ArrowLeft" ? -1 : 1)]?.focus();
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (isSubmitting || isResending || !/^[0-9]{6}$/.test(code)) return;
        setError("");
        setIsSubmitting(true);
        submittingRef.current = true;
        const result = await (isRegistration ? verifyRegistration(code) : verifyOtp(code));
        setIsSubmitting(false);
        if (result.success) {
            navigate(isRegistration ? "/onboarding" : "/reset-password/confirm", { replace: true });
        } else {
            submittingRef.current = false;
            setError(result.error);
        }
    };

    const handleResend = async () => {
        if (cooldown > 0 || isResending || isSubmitting) return;
        setError("");
        setIsResending(true);
        try {
            const result = await (isRegistration ? resendRegistration() : resendOtp());
            if (!result.success) {
                setError(result.error);
                return;
            }
            setCooldown(RESEND_COOLDOWN_SECONDS);
            setDigits(Array(OTP_LENGTH).fill(""));
            requestAnimationFrame(() => inputRefs.current[0]?.focus());
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
                        <BackButton to={backTo} size="w-11 h-11" disabled={isSubmitting || isResending} />
                    </div>

                    <form
                        onSubmit={handleSubmit}
                        aria-busy={isSubmitting || isResending}
                        className="w-full flex flex-col items-center mt-6"
                    >
                        <h1 className="w-full text-h2 font-semibold text-text-black text-left mb-4">{t(isRegistration ? "ยืนยันอีเมลสมัครสมาชิก" : "Enter OTP")}</h1>

                        <p className="w-full text-body-medium text-text-tertiary break-words mb-2">{t("กรอกรหัสสำหรับอีเมล {email}", { email })}</p>
                        <p id="otp-hint" className="w-full text-body-medium text-text-neutral mb-6">{t("รหัสอาจใช้เวลาสักครู่ หากยังไม่ได้รับ ให้รอหมดเวลานับถอยหลังแล้วกดส่งใหม่")}</p>

                        <div className="w-full flex flex-col items-center gap-3">
                            <label id="otp-label" htmlFor="otp-code-0" className="auth-label">{t("รหัส OTP 6 หลัก")}</label>
                            <div role="group" aria-labelledby="otp-label" className="w-full grid grid-cols-6 gap-2 max-[359px]:gap-1 max-[359px]:w-[calc(100%+1rem)]" dir="ltr">
                                {digits.map((digit, index) => <input
                                    key={index}
                                    id={`otp-code-${index}`}
                                    name={`code-${index}`}
                                    ref={(element) => { inputRefs.current[index] = element; }}
                                    type="text"
                                    inputMode="numeric"
                                    autoComplete={index === 0 ? "one-time-code" : "off"}
                                    maxLength={index === 0 ? OTP_LENGTH : 1}
                                    pattern="[0-9]"
                                    required
                                    value={digit}
                                    disabled={isSubmitting || isResending}
                                    aria-label={t("หลักที่ {digit} จาก 6", { digit: index + 1 })}
                                    aria-invalid={Boolean(error)}
                                    aria-describedby={error ? "otp-hint otp-error" : "otp-hint"}
                                    onFocus={(e) => e.target.select()}
                                    onClick={(e) => e.target.select()}
                                    onChange={(e) => handleChange(e.target.value, index)}
                                    onKeyDown={(e) => handleKeyDown(e, index)}
                                    onPaste={(e) => { e.preventDefault(); handleChange(e.clipboardData.getData("text"), index); }}
                                    className="min-w-0 w-full h-14 bg-forms-otp-fill-default border border-stroke-text-field text-center text-2xl tabular-nums text-text-black rounded-xl focus:bg-forms-otp-fill-filled focus:border-stroke-brands disabled:opacity-50"
                                />)}
                            </div>

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

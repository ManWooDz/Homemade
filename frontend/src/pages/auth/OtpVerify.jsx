import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import HeaderLogo from "../../components/HeaderLogo";
import BackButton from "../../components/BackButton";
import { useAuth } from "../../context/AuthContext";

const OTP_LENGTH = 6;
const RESEND_COOLDOWN_SECONDS = 30;

export default function OtpVerify() {
    const navigate = useNavigate();
    const { pendingResetEmail, verifyOtp, resendOtp } = useAuth();
    const [digits, setDigits] = useState(Array(OTP_LENGTH).fill(""));
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [cooldown, setCooldown] = useState(RESEND_COOLDOWN_SECONDS);
    const inputRefs = useRef([]);

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

    const handleChange = (index, value) => {
        const digit = value.replace(/\D/g, "").slice(-1);
        const next = [...digits];
        next[index] = digit;
        setDigits(next);
        if (digit && index < OTP_LENGTH - 1) {
            inputRefs.current[index + 1]?.focus();
        }
    };

    const handleKeyDown = (index, e) => {
        if (e.key === "Backspace" && !digits[index] && index > 0) {
            inputRefs.current[index - 1]?.focus();
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setIsSubmitting(true);
        const code = digits.join("");
        const result = await verifyOtp(code);
        setIsSubmitting(false);
        if (result.success) {
            navigate("/reset-password/confirm");
        } else {
            setError(result.error);
        }
    };

    const handleResend = async () => {
        if (cooldown > 0) return;
        await resendOtp();
        setCooldown(RESEND_COOLDOWN_SECONDS);
        setDigits(Array(OTP_LENGTH).fill(""));
        inputRefs.current[0]?.focus();
    };

    return (
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative shadow-2xl overflow-y-auto overflow-x-hidden">
                <div className="w-full min-h-full px-8 pt-6 pb-10 bg-background-primary flex flex-col justify-start items-center">
                    <HeaderLogo />

                    <div className="w-full flex justify-start items-center">
                        <BackButton to="/reset-password" />
                    </div>

                    <form
                        onSubmit={handleSubmit}
                        className="w-full flex flex-col justify-start items-center mt-24"
                    >
                        <h1 className="w-full text-h2 font-semibold text-text-black text-left mb-4">
                            Enter OTP
                        </h1>

                        <div className="w-full flex flex-col items-center gap-3">
                            <div className="flex gap-2">
                                {digits.map((digit, index) => (
                                    <input
                                        key={index}
                                        ref={(el) => (inputRefs.current[index] = el)}
                                        type="text"
                                        inputMode="numeric"
                                        maxLength={1}
                                        value={digit}
                                        onChange={(e) => handleChange(index, e.target.value)}
                                        onKeyDown={(e) => handleKeyDown(index, e)}
                                        className="w-10 h-11 bg-forms-otp-fill-default border border-stroke-text-field text-center text-body-large text-text-black rounded-lg focus:outline-none focus:bg-forms-otp-fill-filled focus:border-stroke-brands"
                                    />
                                ))}
                            </div>

                            <button
                                type="button"
                                onClick={handleResend}
                                disabled={cooldown > 0}
                                className="h-11 px-4 bg-button-neutral rounded-full border border-stroke-brands text-text-brands text-body-medium font-normal flex justify-center items-center whitespace-nowrap cursor-pointer hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {cooldown > 0 ? `Resend (${cooldown}s)` : "Resend"}
                            </button>
                        </div>

                        {error && (
                            <p className="w-full text-body-medium text-red-500 mt-4">{error}</p>
                        )}

                        <button
                            type="submit"
                            disabled={isSubmitting || digits.some((d) => !d)}
                            className="w-full h-11 mt-24 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-all cursor-pointer disabled:opacity-50"
                        >
                            {isSubmitting ? "Verifying..." : "Verify"}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}

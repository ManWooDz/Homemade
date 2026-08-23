import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import AuthHeader from "../../components/AuthHeader";
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

    const handleBack = () => {
        if (window.history.state?.idx > 0) {
            navigate(-1);
        } else {
            navigate("/reset-password");
        }
    };

    return (
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                <AuthHeader onBack={handleBack} />
                <div className="flex-1 overflow-y-auto px-6 pb-10 flex flex-col">
                    <h2 className="text-xl font-bold text-gray-900 text-center mb-2">
                        Enter verification code
                    </h2>
                    <p className="text-sm text-gray-500 text-center mb-8">
                        We sent a code to {pendingResetEmail}
                    </p>

                    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
                        <div className="flex justify-center gap-2">
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
                                    className="w-11 h-13 text-center text-xl font-bold bg-gray-50 border border-gray-300 rounded-2xl outline-none focus:border-[#EF5A3A] transition"
                                />
                            ))}
                        </div>

                        {error && <p className="text-sm text-red-500 text-center">{error}</p>}

                        <button
                            type="submit"
                            disabled={isSubmitting || digits.some((d) => !d)}
                            className="w-full bg-[#EF5A3A] text-white py-4 rounded-full text-lg font-bold shadow-md hover:bg-orange-600 disabled:opacity-50 transition"
                        >
                            {isSubmitting ? "Verifying..." : "Verify"}
                        </button>
                    </form>

                    <div className="text-center mt-6">
                        {cooldown > 0 ? (
                            <p className="text-sm text-gray-400">
                                Resend code in {cooldown}s
                            </p>
                        ) : (
                            <button
                                onClick={handleResend}
                                className="text-sm font-bold text-[#EF5A3A]"
                            >
                                Resend code
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

import { useLocale } from "../../context/LocaleContext";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import HeaderLogo from "../../components/HeaderLogo";
import BackButton from "../../components/BackButton";
import { useAuth } from "../../context/AuthContext";
import { isValidEmail } from "../../utils/authValidation";

export default function ResetPasswordEmail() {
    const { t } = useLocale();
    const navigate = useNavigate();
    const { requestOtp } = useAuth();
    const [email, setEmail] = useState("");
    const [error, setError] = useState("");

    const handleSubmit = (e) => {
        e.preventDefault();
        setError("");
        if (!isValidEmail(email)) {
            setError("กรุณากรอกอีเมลให้ถูกต้อง");
            return;
        }
        void requestOtp(email);
        navigate("/reset-password/otp");
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
                        className="w-full flex flex-col items-center mt-6"
                    >
                        <h1 className="w-full text-h2 font-semibold text-text-black text-left mb-4">{t("Reset Password")}</h1>
                        <p id="reset-email-hint" className="w-full text-body-medium text-text-neutral mb-6">{t("ใช้อีเมลที่สมัครสมาชิกเพื่อรับรหัสยืนยัน")}</p>

                        <div className="w-full flex flex-col gap-3">
                            <label htmlFor="reset-email" className="auth-label">{t("Email")}</label>
                            <input
                                id="reset-email"
                                name="email"
                                autoComplete="email"
                                autoCapitalize="none"
                                aria-describedby="reset-email-hint"
                                type="email"
                                placeholder={t("Email")}
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full h-11 px-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands"
                                required
                            />
                        </div>

                        {error && (
                            <p role="alert" className="w-full text-body-medium text-red-700 mt-4">{t(error)}</p>
                        )}

                        <button
                            type="submit"
                            className="w-full h-11 mt-6 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-all cursor-pointer"
                        >{t("Send OTP")}</button>
                    </form>
                </main>
            </div>
        </div>
    );
}

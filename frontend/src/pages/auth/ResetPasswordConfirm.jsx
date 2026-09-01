import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import HeaderLogo from "../../components/HeaderLogo";
import BackButton from "../../components/BackButton";
import PasswordInput from "../../components/PasswordInput";
import { useAuth } from "../../context/AuthContext";

export default function ResetPasswordConfirm() {
    const navigate = useNavigate();
    const { otpVerified, resetPassword } = useAuth();
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    // resetPassword() clears otpVerified as part of its own success cleanup, which would
    // otherwise race this guard's redirect against the page's own post-submit navigate().
    // Check the flag once at mount instead of reacting to it.
    const otpVerifiedAtMount = useRef(otpVerified);

    useEffect(() => {
        if (!otpVerifiedAtMount.current) {
            navigate("/reset-password", { replace: true });
        }
    }, [navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
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
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative shadow-2xl overflow-y-auto">
                <div className="w-full min-h-full px-8 pt-6 pb-10 bg-background-primary flex flex-col justify-start items-center">
                    <HeaderLogo />

                    <div className="w-full flex justify-start items-center">
                        <BackButton to="/reset-password/otp" />
                    </div>

                    <form
                        onSubmit={handleSubmit}
                        className="w-full flex flex-col justify-start items-center mt-24"
                    >
                        <h1 className="w-full text-h2 font-semibold text-text-black text-left mb-4">
                            Reset Password
                        </h1>

                        <div className="w-full flex flex-col justify-start items-center gap-4.25">
                            <PasswordInput
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="New Password"
                                required
                            />

                            <PasswordInput
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Confirm password"
                                required
                            />
                        </div>

                        {error && (
                            <p className="w-full text-body-medium text-red-500 mt-4">{error}</p>
                        )}

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full h-11 mt-6 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-all cursor-pointer disabled:opacity-50"
                        >
                            {isSubmitting ? "Saving..." : "Confirm"}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}

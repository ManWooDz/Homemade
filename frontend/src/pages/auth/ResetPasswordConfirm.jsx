import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import AuthHeader from "../../components/AuthHeader";
import PasswordInput from "../../components/PasswordInput";
import { useAuth } from "../../context/AuthContext";

export default function ResetPasswordConfirm() {
    const navigate = useNavigate();
    const { otpVerified, resetPassword } = useAuth();
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (!otpVerified) {
            navigate("/reset-password", { replace: true });
        }
    }, [otpVerified, navigate]);

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
                <div className="flex-1 overflow-y-auto px-6 pb-10">
                    <h2 className="text-xl font-bold text-gray-900 text-center mb-8">
                        Set a new password
                    </h2>

                    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                        <div>
                            <label className="text-sm font-bold text-gray-700 mb-2 block">
                                New Password
                            </label>
                            <PasswordInput
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="At least 8 characters"
                                required
                            />
                        </div>
                        <div>
                            <label className="text-sm font-bold text-gray-700 mb-2 block">
                                Confirm New Password
                            </label>
                            <PasswordInput
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Re-enter new password"
                                required
                            />
                        </div>

                        {error && <p className="text-sm text-red-500">{error}</p>}

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full mt-4 bg-[#EF5A3A] text-white py-4 rounded-full text-lg font-bold shadow-md hover:bg-orange-600 disabled:opacity-50 transition"
                        >
                            {isSubmitting ? "Saving..." : "Save New Password"}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}

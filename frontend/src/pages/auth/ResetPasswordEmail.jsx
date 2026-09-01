import { useState } from "react";
import { useNavigate } from "react-router-dom";
import HeaderLogo from "../../components/HeaderLogo";
import BackButton from "../../components/BackButton";
import { useAuth } from "../../context/AuthContext";

export default function ResetPasswordEmail() {
    const navigate = useNavigate();
    const { requestOtp } = useAuth();
    const [email, setEmail] = useState("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setIsSubmitting(true);
        const result = await requestOtp(email);
        setIsSubmitting(false);
        if (result.success) {
            navigate("/reset-password/otp");
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
                        <BackButton to="/login" />
                    </div>

                    <form
                        onSubmit={handleSubmit}
                        className="w-full flex flex-col justify-start items-center mt-24"
                    >
                        <h1 className="w-full text-h2 font-semibold text-text-black text-left mb-4">
                            Reset Password
                        </h1>

                        <div className="w-full flex flex-col justify-start items-center">
                            <input
                                type="email"
                                placeholder="Email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full h-11 px-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands"
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
                            {isSubmitting ? "Sending..." : "Send OTP"}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}

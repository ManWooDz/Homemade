import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AuthHeader from "../../components/AuthHeader";
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
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                <AuthHeader onBack={() => navigate(-1)} />
                <div className="flex-1 overflow-y-auto px-6 pb-10">
                    <h2 className="text-xl font-bold text-gray-900 text-center mb-2">
                        Reset your password
                    </h2>
                    <p className="text-sm text-gray-500 text-center mb-8">
                        Enter your email and we'll send you a verification code.
                    </p>

                    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                        <div>
                            <label className="text-sm font-bold text-gray-700 mb-2 block">
                                Email
                            </label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@example.com"
                                className="w-full bg-gray-50 border border-gray-300 rounded-2xl px-4 py-3 outline-none text-base focus:border-[#EF5A3A] transition"
                                required
                            />
                        </div>

                        {error && <p className="text-sm text-red-500">{error}</p>}

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full mt-4 bg-[#EF5A3A] text-white py-4 rounded-full text-lg font-bold shadow-md hover:bg-orange-600 disabled:opacity-50 transition"
                        >
                            {isSubmitting ? "Sending..." : "Send Code"}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}

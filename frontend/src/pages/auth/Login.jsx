import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import HeaderLogo from "../../components/HeaderLogo";
import PasswordInput from "../../components/PasswordInput";
import { useAuth } from "../../context/AuthContext";

export default function Login() {
    const navigate = useNavigate();
    const location = useLocation();
    const { login } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const successMessage = location.state?.message;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setIsSubmitting(true);
        const result = await login(email, password);
        setIsSubmitting(false);
        if (result.success) {
            navigate("/home", { replace: true });
        } else {
            setError(result.error);
        }
    };

    return (
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative shadow-2xl overflow-y-auto">
                <div className="w-full min-h-full px-6 py-10 bg-background-primary flex flex-col justify-center items-center">
                    <div className="w-full h-auto flex flex-col justify-start items-center gap-8">
                        <HeaderLogo />

                        {successMessage && (
                            <p className="w-full text-body-medium text-green-600 bg-green-50 border border-green-200 rounded-2xl px-4 py-3 text-center">
                                {successMessage}
                            </p>
                        )}

                        <form
                            onSubmit={handleSubmit}
                            className="w-full h-auto flex flex-col justify-start items-center gap-4"
                        >
                            <div className="w-full h-auto flex flex-col justify-start items-center gap-3">
                                <input
                                    type="email"
                                    placeholder="Email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="w-full h-11 px-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands"
                                    required
                                />
                                <PasswordInput
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Password"
                                    required
                                />
                            </div>

                            {error && <p className="text-body-medium text-red-500">{error}</p>}

                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="w-full h-11 mt-2 bg-button-primary hover:opacity-95 text-button-neutral text-body-medium font-semibold rounded-full flex justify-center items-center transition-all cursor-pointer disabled:opacity-50"
                            >
                                {isSubmitting ? "กำลังเข้าสู่ระบบ..." : "Login"}
                            </button>

                            <div className="w-full flex justify-center items-center gap-2 text-caption mt-1">
                                <Link
                                    to="/register"
                                    className="text-text-brands font-normal hover:underline"
                                >
                                    Sign in
                                </Link>
                                <div className="w-px h-3 bg-text-black"></div>
                                <Link
                                    to="/reset-password"
                                    className="text-text-black font-normal hover:underline"
                                >
                                    Forgot password?
                                </Link>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
}

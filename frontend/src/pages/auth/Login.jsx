import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import logo from "../../assets/HomeMade_Logo.png";
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
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                <div className="flex-1 overflow-y-auto px-6 pt-16 pb-10 flex flex-col">
                    <div className="flex justify-center mb-10">
                        <img src={logo} alt="HomeMade" className="h-20 object-contain" />
                    </div>

                    {successMessage && (
                        <p className="text-sm text-green-600 bg-green-50 border border-green-200 rounded-2xl px-4 py-3 text-center mb-4">
                            {successMessage}
                        </p>
                    )}

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
                        <div>
                            <label className="text-sm font-bold text-gray-700 mb-2 block">
                                Password
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                className="w-full bg-gray-50 border border-gray-300 rounded-2xl px-4 py-3 outline-none text-base focus:border-[#EF5A3A] transition"
                                required
                            />
                        </div>

                        {error && <p className="text-sm text-red-500">{error}</p>}

                        <div className="text-right -mt-1">
                            <Link to="/reset-password" className="text-sm font-medium text-[#EF5A3A]">
                                Forgot password?
                            </Link>
                        </div>

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full mt-4 bg-[#EF5A3A] text-white py-4 rounded-full text-lg font-bold shadow-md hover:bg-orange-600 disabled:opacity-50 transition"
                        >
                            {isSubmitting ? "Logging in..." : "Log In"}
                        </button>
                    </form>

                    <p className="text-center text-sm text-gray-500 mt-6">
                        No account?{" "}
                        <Link to="/register" className="text-[#EF5A3A] font-bold">
                            Register
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}

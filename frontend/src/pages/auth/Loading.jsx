import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../../assets/HomeMade_Logo.png";
import { useAuth } from "../../context/AuthContext";

const SPLASH_DURATION_MS = 1200;

export default function Loading() {
    const navigate = useNavigate();
    const { isAuthenticated } = useAuth();

    useEffect(() => {
        const timer = setTimeout(() => {
            navigate(isAuthenticated ? "/home" : "/login", { replace: true });
        }, SPLASH_DURATION_MS);
        return () => clearTimeout(timer);
    }, [isAuthenticated, navigate]);

    return (
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                <div className="w-full flex-1 flex flex-col justify-center items-center bg-background-primary overflow-hidden">
                    <img
                        src={logo}
                        alt="HomeMade Logo"
                        className="w-56 h-auto object-contain animate-pulse"
                    />
                </div>
            </div>
        </div>
    );
}

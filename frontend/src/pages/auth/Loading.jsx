import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../../assets/HomeMade_Logo.png";
import { useAuth } from "../../context/AuthContext";

const SPLASH_DURATION_MS = 1200;

export default function Loading() {
    const navigate = useNavigate();
    const { isAuthenticated, authLoading } = useAuth();
    const [minDurationElapsed, setMinDurationElapsed] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => setMinDurationElapsed(true), SPLASH_DURATION_MS);
        return () => clearTimeout(timer);
    }, []);

    useEffect(() => {
        // Don't navigate until BOTH the minimum splash duration has
        // elapsed AND the /me bootstrap has resolved — otherwise a slow
        // refresh-and-retry could send a still-valid session to /login.
        if (minDurationElapsed && !authLoading) {
            navigate(isAuthenticated ? "/home" : "/login", { replace: true });
        }
    }, [minDurationElapsed, authLoading, isAuthenticated, navigate]);

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

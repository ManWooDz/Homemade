import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
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
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col items-center justify-center shadow-2xl">
                <motion.img
                    src={logo}
                    alt="HomeMade"
                    className="h-24 object-contain"
                    animate={{ scale: [1, 1.05, 1], opacity: [0.85, 1, 0.85] }}
                    transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
                />
            </div>
        </div>
    );
}

import { ChevronLeft } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";

export default function AuthHeader({ onBack }) {
    return (
        <div className="pt-8 px-6 flex items-center justify-center relative z-20 mb-8">
            {onBack && (
                <button
                    onClick={onBack}
                    className="absolute left-6 w-10 h-10 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md"
                >
                    <ChevronLeft className="w-6 h-6" />
                </button>
            )}
            <img src={logo} alt="HomeMade" className="h-18 object-contain" />
        </div>
    );
}

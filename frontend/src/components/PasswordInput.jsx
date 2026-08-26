import { useState } from "react";
import { FaRegEye, FaRegEyeSlash } from "react-icons/fa6";

export default function PasswordInput({ value, onChange, placeholder, required }) {
    const [visible, setVisible] = useState(false);

    return (
        <div className="relative">
            <input
                type={visible ? "text" : "password"}
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                required={required}
                className="w-full bg-gray-50 border border-gray-300 rounded-2xl pl-4 pr-11 py-3 outline-none text-base focus:border-[#EF5A3A] transition"
            />
            <button
                type="button"
                onClick={() => setVisible((v) => !v)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition"
                aria-label={visible ? "Hide password" : "Show password"}
            >
                {visible ? <FaRegEye className="w-5 h-5" /> : <FaRegEyeSlash className="w-5 h-5" />}
            </button>
        </div>
    );
}

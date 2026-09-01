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
                className="w-full h-11 bg-background-primary border border-stroke-text-field rounded-full pl-4 pr-11 text-body-large text-text-black placeholder:text-text-neutral outline-none focus:border-stroke-brands transition"
            />
            <button
                type="button"
                onClick={() => setVisible((v) => !v)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-text-neutral hover:text-text-black transition"
                aria-label={visible ? "Hide password" : "Show password"}
            >
                {visible ? <FaRegEye className="w-5 h-5" /> : <FaRegEyeSlash className="w-5 h-5" />}
            </button>
        </div>
    );
}

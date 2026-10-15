import { useLocale } from "../context/LocaleContext";
import { useState } from "react";
import { FaRegEye, FaRegEyeSlash } from "react-icons/fa6";

export default function PasswordInput({ value, onChange, placeholder, required, ...inputProps }) {
    const { t } = useLocale();
    const [visible, setVisible] = useState(false);

    return (
        <div className="relative w-full">
            <input
                aria-label={placeholder}
                {...inputProps}
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
                className="absolute right-1 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full flex items-center justify-center text-text-neutral hover:text-text-black transition-colors"
                aria-label={visible ? t("Hide password") : t("Show password")}
                aria-pressed={visible}
            >
                {visible ? <FaRegEye className="w-5 h-5" /> : <FaRegEyeSlash className="w-5 h-5" />}
            </button>
        </div>
    );
}

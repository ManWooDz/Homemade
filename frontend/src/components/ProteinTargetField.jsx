import { useId } from "react";
import { useLocale } from "../context/LocaleContext";

export default function ProteinTargetField({ value, onChange, invalid }) {
    const id = useId();
    const { t } = useLocale();
    return <div>
        <label htmlFor={id} className="block text-lg font-semibold text-gray-900">
            {t("เป้าโปรตีน (กรัมต่อเสิร์ฟ ถ้ามี)")}
        </label>
        <input id={id} type="text" inputMode="decimal" value={value} onChange={(event) => onChange(event.target.value)}
            aria-invalid={invalid} aria-describedby={invalid ? `${id}-error` : undefined}
            className="mt-3 w-full min-h-12 rounded-xl border border-gray-400 px-4 text-base text-gray-900" />
        {invalid && <p id={`${id}-error`} className="mt-2 text-sm text-red-700">
            {t("กรอกตัวเลขมากกว่า 0 และใช้ทศนิยมได้ 1 ตำแหน่ง")}
        </p>}
    </div>;
}

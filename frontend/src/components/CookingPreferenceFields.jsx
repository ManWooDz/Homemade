import { useId } from "react";
import { useLocale } from "../context/LocaleContext";
import { OptionChips } from "./OptionPicker";
import { ALLERGY_OPTIONS, ALLERGY_NONE, DIETARY_OPTIONS, DIETARY_NONE, EQUIPMENT_OPTIONS, EQUIPMENT_NONE, OTHER_OPTION } from "../constants/preferenceOptions.js";
import { classifyRestriction, toggleCookingChoice } from "../utils/cookingPreferences.js";

export default function CookingPreferenceFields({ value, onChange, equipmentOnly = false, restrictionsOnly = false, allergyError, allergyInput, onAllergyEdit, onBlur }) {
    const { t } = useLocale();
    const id = useId();
    const inputClass = "w-full min-h-12 border border-gray-400 rounded-xl px-4 py-3 text-base text-gray-900 placeholder:text-gray-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]";
    const groups = [
        ...(!equipmentOnly ? [
            { key: "allergies", other: "allergyOther", title: "อาการแพ้อาหาร", options: ALLERGY_OPTIONS, none: ALLERGY_NONE, placeholder: "ระบุอาการแพ้อาหาร" },
            { key: "dietary", other: "dietaryOther", title: "ข้อจำกัดในการกิน", options: DIETARY_OPTIONS, none: DIETARY_NONE, placeholder: "ระบุข้อจำกัดในการกิน" },
        ] : []),
        ...(!restrictionsOnly ? [{ key: "equipment", other: "equipmentOther", title: "อุปกรณ์ที่มี", options: EQUIPMENT_OPTIONS, none: EQUIPMENT_NONE, placeholder: "ระบุอุปกรณ์ที่มี" }] : []),
    ];
    const change = (next, draft = false) => { onChange(next, { draft }); onAllergyEdit?.(); };
    return <div className="w-full min-w-0 space-y-8 text-gray-900 selection:bg-[#FDECE5] selection:text-[#9F351F] caret-[#B93E25] [&_button:focus-visible]:outline-2 [&_button:focus-visible]:outline-offset-2 [&_button:focus-visible]:outline-[#B93E25]">
        {!equipmentOnly && value.unclassified.length > 0 && <fieldset className="min-w-0 rounded-2xl border border-gray-300 p-4">
            <legend className="px-1 text-base font-semibold">{t("จัดหมวดข้อความเดิม")}</legend>
            <p className="mb-4 text-sm text-gray-600">{t("ข้อความเหล่านี้ยังไม่ระบุหมวด กรุณาเลือกหมวดก่อนสร้างสูตร")}</p>
            <div className="space-y-4">{value.unclassified.map((text, index) => <div key={index} className="space-y-2">
                <label htmlFor={`${id}-legacy-${index}`} className="block break-words text-base">{text}</label>
                <select id={`${id}-legacy-${index}`} className={inputClass} value="" onChange={event => change(classifyRestriction(value, index, event.target.value))}>
                    <option value="" disabled>{t("เลือกหมวด")}</option>
                    <option value="allergy">{t("อาการแพ้อาหาร")}</option>
                    <option value="dietary">{t("ข้อจำกัดในการกิน")}</option>
                </select>
            </div>)}</div>
        </fieldset>}
        {groups.map(group => <fieldset key={group.key} className="min-w-0">
            <legend className="text-lg font-semibold text-gray-900">{t(group.title)}</legend>
            <p className="mt-1 mb-3 text-sm text-gray-600">{t("เลือกได้มากกว่า 1 ข้อ")}</p>
            <OptionChips options={group.options} selected={value[group.key]} multiple onToggle={option => change(toggleCookingChoice(value, group.key, option, group.none, group.other))} />
            {value[group.key].includes(OTHER_OPTION) && <div className="mt-4 space-y-3">
                {value[group.other].map((text, index) => <label key={index} className="block space-y-2">
                    <span className="block text-sm font-medium">{t(group.placeholder)}{value[group.other].length > 1 ? ` ${index + 1}` : ""}</span>
                    <textarea rows={2} value={text} ref={group.key === "allergies" && index === 0 ? allergyInput : undefined}
                        aria-label={`${t(group.placeholder)}${value[group.other].length > 1 ? ` ${index + 1}` : ""}`}
                        aria-invalid={group.key === "allergies" && Boolean(allergyError)} aria-describedby={group.key === "allergies" && allergyError ? "allergy-error" : undefined}
                        maxLength={group.key === "allergies" ? 1000 : undefined} className={`${inputClass} resize-y`}
                        onBlur={() => onBlur?.(value)} onChange={event => change({ ...value, [group.other]: value[group.other].map((item, i) => i === index ? event.target.value : item) }, true)} />
                </label>)}
            </div>}
        </fieldset>)}
    </div>;
}

export function PreferenceLoadStatus({ status, retry }) {
    const { t } = useLocale();
    if (status === "ready") return null;
    return <div className="mb-3 text-sm text-gray-700" role={status === "error" ? "alert" : "status"}>
        <p>{t(status === "loading" ? "กำลังโหลดค่าจากโปรไฟล์…" : "โหลดค่าจากโปรไฟล์ไม่สำเร็จ กรุณาลองใหม่ก่อนสร้างสูตร")}</p>
        {status === "error" && <button type="button" onClick={retry} className="mt-2 min-h-11 rounded-full border border-[#B93E25] px-4 font-semibold text-[#9F351F] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]">{t("ลองโหลดใหม่")}</button>}
    </div>;
}

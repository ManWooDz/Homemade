import { useLocale } from "../context/LocaleContext";
import NotificationBell from "../components/NotificationBell";
import { useState, useRef } from "react";
import { Check, ChefHat, ChevronLeft, Refrigerator } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import { OptionChips } from "../components/OptionPicker";
import { OTHER_OPTION, TASTE_OPTIONS } from "../constants/preferenceOptions";
import CookingPreferenceFields, { PreferenceLoadStatus } from "../components/CookingPreferenceFields";
import useSavedCookingPreferences from "../hooks/useSavedCookingPreferences";
import { cookingPreferenceError, generationPreferences } from "../utils/cookingPreferences.js";
import { expiryBadgeLabel } from "../utils/expiry";

export default function CustomCookingPage({
    userIngredients,
    onBack,
    activeTab,
    setActiveTab,
    onGenerate,
    notificationCount, onNotifications,
}) {
    const { t, locale } = useLocale();
    const [taste, setTaste] = useState("");
    const [tasteOther, setTasteOther] = useState("");
    const [allergyError, setAllergyError] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const submitting = useRef(false);
    const allergyInput = useRef(null);
    const [extra, setExtra] = useState("");
  const preferences = useSavedCookingPreferences();
  const preferenceIssue = cookingPreferenceError(preferences.value);
    const [selectedIngredients, setSelectedIngredients] = useState([]);

    const toggleIngredient = (id) => {
        setSelectedIngredients((prev) =>
            prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
        );
    };

    const handleGenerateClick = async () => {
        if (submitting.current || selectedIngredients.length === 0 || preferences.status !== "ready" || preferenceIssue) return;
        submitting.current = true;
        setIsSubmitting(true);
        const selectedObjs = userIngredients.filter((ing) =>
            selectedIngredients.includes(ing.id),
        );
        try {
            const error = await onGenerate(
                generationPreferences(preferences.value, taste === OTHER_OPTION ? tasteOther.trim() || OTHER_OPTION : taste, extra),
                selectedObjs,
            );
            setAllergyError(error || null);
            if (error) allergyInput.current?.focus();
        } finally {
            submitting.current = false;
            setIsSubmitting(false);
        }
    };

    return (
        <div className="custom-cooking-screen h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                <header className="pt-8 px-6 flex items-center justify-center relative z-20 mb-6">
                    <button type="button" onClick={onBack} aria-label={t("กลับ")}
                        className="absolute left-6 w-11 h-11 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md">
                        <ChevronLeft className="w-6 h-6" />
                    </button>
                    <img src={logo} alt="HomeMade" className="h-18 object-contain" />
                    <div className="absolute right-6 top-1/2 translate-y-4"><NotificationBell count={notificationCount} onClick={onNotifications} /></div>
                </header>

                <main className="flex-1 min-h-0 overflow-y-auto px-6 pb-8">
                    <div className="mb-8">
                        <h1 className="text-2xl font-bold text-gray-900 leading-snug">{t("Custom Cooking")}</h1>
                        <p className="mt-2 text-sm text-gray-600 leading-relaxed">{t("เลือกวัตถุดิบ แล้วปรับสูตรให้เข้ากับคุณ")}</p>
                    </div>

                    <section aria-labelledby="cooking-ingredients" className="mb-8">
                        <h2 id="cooking-ingredients" className="text-lg font-semibold text-gray-900">{t("วัตถุดิบที่ต้องการใช้")}</h2>
                        <p className="mt-1 mb-4 text-sm text-gray-600">{t("เลือกอย่างน้อย 1 อย่าง")}</p>
                        {userIngredients && userIngredients.length > 0 ? (
                            <div className="grid grid-cols-1 min-[380px]:grid-cols-2 gap-3">
                                {userIngredients.map((ing) => {
                                    const isSelected = selectedIngredients.includes(ing.id);
                                    const expiry = expiryBadgeLabel(ing.expiry_date, locale);
                                    return (
                                        <button key={ing.id} type="button" aria-pressed={isSelected}
                                            onClick={() => toggleIngredient(ing.id)}
                                            className={"min-h-20 w-full min-w-0 grid grid-cols-[2rem_minmax(0,1fr)_1.25rem] items-center gap-x-2 gap-y-1 p-3 rounded-2xl border text-left transition-colors " + (isSelected ? "bg-[#FDECE5] border-[#B93E25]" : "bg-white border-gray-300 hover:border-gray-400 hover:bg-gray-50")}>
                                            {ing.image ? <img src={ing.image} alt="" className="w-8 h-8 rounded-full object-cover shrink-0"
                                                onError={(event) => { if (event.currentTarget.getAttribute("src") !== logo) event.currentTarget.src = logo; }} />
                                                : <Refrigerator aria-hidden="true" className="w-8 h-8 text-gray-500 shrink-0" />}
                                            <span className="min-w-0 text-sm font-semibold text-gray-900 break-words">{ing.name}</span>
                                            <span aria-hidden="true" className={"w-5 h-5 rounded-full border shrink-0 flex items-center justify-center " + (isSelected ? "bg-[#B93E25] border-[#B93E25] text-white" : "border-gray-400")}>
                                                {isSelected && <Check className="w-3.5 h-3.5" />}
                                            </span>
                                            {expiry && <span className="col-span-3 text-xs text-red-700 leading-relaxed">{expiry}</span>}
                                        </button>
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="rounded-2xl bg-gray-50 p-5">
                                <Refrigerator aria-hidden="true" className="w-7 h-7 text-gray-500 mb-3" />
                                <p className="text-sm text-gray-600 leading-relaxed">{t("ตู้เย็นของคุณว่างเปล่า คุณสามารถไปเพิ่มวัตถุดิบได้ที่ My Fridge")}</p>
                                <button type="button" onClick={() => setActiveTab("fridge")} className="mt-3 min-h-11 text-sm font-semibold text-[#B93E25] underline underline-offset-4">{t("ไปที่ตู้เย็นของฉัน")}</button>
                            </div>
                        )}
                    </section>

                    <div className="space-y-8 border-t border-gray-200 pt-8">
                        <fieldset className="min-w-0">
                            <legend className="text-lg font-semibold text-gray-900">{t("รสชาติ")}</legend>
                            <p className="mt-1 mb-3 text-sm text-gray-600">{t("เลือกได้ 1 รสชาติ หรือไม่ระบุ")}</p>
                            <OptionChips options={TASTE_OPTIONS} selected={taste} onToggle={setTaste} />
                            {taste === OTHER_OPTION && (
                                <input type="text" value={tasteOther} onChange={(event) => setTasteOther(event.target.value)}
                                    aria-label={t("ระบุรสชาติที่ต้องการ")} placeholder={t("ระบุรสชาติที่ต้องการ")}
                                    className="mt-4 w-full min-h-12 border border-gray-400 rounded-xl px-4 py-3 text-base text-gray-900 placeholder:text-gray-500" />
                            )}
                        </fieldset>

                        <CookingPreferenceFields value={preferences.value} onChange={preferences.edit}
              allergyError={allergyError} allergyInput={allergyInput} onAllergyEdit={() => setAllergyError(null)} />

                        <div>
                            <label htmlFor="cooking-extra" className="block text-lg font-semibold text-gray-900">{t("ความต้องการอื่นๆ (ถ้ามี)")}</label>
                            <textarea id="cooking-extra" rows={4} value={extra} onChange={(event) => setExtra(event.target.value)}
                                placeholder={t("เช่น สิ่งที่ต้องระวัง หรือ ลักษณะของเมนูที่อยากได้")}
                                className="mt-3 w-full border border-gray-400 rounded-2xl p-4 text-base text-gray-900 placeholder:text-gray-500 resize-y" />
                        </div>
                    </div>
                </main>

                <div className="shrink-0 mb-24 border-t border-gray-200 bg-white px-6 pt-3 pb-4">
                    <p role="status" className="mb-2 text-xs text-gray-600 tabular-nums">
                        {selectedIngredients.length > 0 ? t("เลือกวัตถุดิบแล้ว {count} รายการ", { count: selectedIngredients.length }) : t("เลือกวัตถุดิบอย่างน้อย {count} อย่าง", { count: 1 })}
                    </p>
          <PreferenceLoadStatus status={preferences.status} retry={preferences.retry} />
          {preferences.status === "ready" && preferenceIssue && <p role="status" className="mb-3 text-sm text-gray-700">{t(preferenceIssue)}</p>}
          {allergyError && <p id="allergy-error" role="alert" className="mb-3 text-sm text-red-700 break-words">{t(allergyError)}</p>}
                    <button type="button" onClick={handleGenerateClick} disabled={selectedIngredients.length === 0 || isSubmitting || preferences.status !== "ready" || Boolean(preferenceIssue)}
                        aria-busy={isSubmitting}
                        className="w-full min-h-12 px-4 py-3 bg-[#B93E25] text-white rounded-full text-base font-semibold flex items-center justify-center gap-2 hover:bg-[#9D341F] disabled:bg-gray-200 disabled:text-gray-500 disabled:cursor-not-allowed transition-colors">
                        <ChefHat aria-hidden="true" className="w-5 h-5 shrink-0" />
                        {isSubmitting ? t("กำลังตรวจสอบอาการแพ้…") : t("สร้างเมนูอาหารกันเลย")}
                    </button>
                </div>
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

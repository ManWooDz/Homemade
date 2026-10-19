import { useLocale } from "../context/LocaleContext";
import { ChevronLeft, Plus, Refrigerator, X, ChefHat } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import { OptionChips } from "../components/OptionPicker";
import { useState, useEffect, useRef } from "react";
import { expiryBadgeLabel } from "../utils/expiry";
import { OTHER_OPTION, TASTE_OPTIONS } from "../constants/preferenceOptions";
import CookingPreferenceFields, { PreferenceLoadStatus } from "../components/CookingPreferenceFields";
import useSavedCookingPreferences from "../hooks/useSavedCookingPreferences";
import { cookingPreferenceError, generationPreferences } from "../utils/cookingPreferences.js";

export default function CreateRecipe({
  recipe,
  selectedIngredients,
  userIngredients,
  onBack,
  activeTab,
  setActiveTab,
  onGenerate,
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

  // local state for ingredients including those added from fridge
  const [currentIngredients, setCurrentIngredients] = useState([]);
  const [showFridge, setShowFridge] = useState(false);

  useEffect(() => {
    setCurrentIngredients(selectedIngredients || []);
  }, [selectedIngredients]);

  const handleGenerateClick = async () => {
    if (submitting.current || preferences.status !== "ready" || preferenceIssue) return;
    submitting.current = true;
    setIsSubmitting(true);
    try {
      const error = await onGenerate(
        generationPreferences(preferences.value, taste === OTHER_OPTION ? tasteOther.trim() || OTHER_OPTION : taste, extra),
        currentIngredients,
      );
      setAllergyError(error || null);
      if (error) allergyInput.current?.focus();
    } finally {
      submitting.current = false;
      setIsSubmitting(false);
    }
  };

  const addFromFridge = (ing) => {
    // check if already added
    if (!currentIngredients.find((cur) => cur.name === ing.name)) {
      setCurrentIngredients([
        ...currentIngredients,
        { ...ing, id: Date.now() },
      ]);
    }
  };

  const removeIngredient = (idToRemove) => {
    setCurrentIngredients(
      currentIngredients.filter((ing) => ing.id !== idToRemove),
    );
  };

  return (
    <div className="create-recipe-screen h-dvh bg-gray-100 flex justify-center font-sans overflow-hidden">
      <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
        <div className="shrink-0 pt-5 pb-6 px-6 flex items-center justify-center relative z-20">
          <button onClick={onBack} aria-label={t("กลับ")}
            className="absolute left-5 w-11 h-11 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center">
            <ChevronLeft className="w-6 h-6" />
          </button>
          <img src={logo} alt="HomeMade" className="h-14 object-contain" />
        </div>

        <main className="flex-1 min-h-0 overflow-y-auto scrollbar-hide px-5 pb-6">
          <section className="flex items-start gap-4 pb-6 border-b border-gray-200" aria-labelledby="create-recipe-title">
            <div className="w-20 h-20 rounded-2xl overflow-hidden shrink-0 bg-gray-50">
              <img src={recipe?.image || "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80"}
                alt={recipe?.name || t("Food Menu")} className="w-full h-full object-cover" />
            </div>
            <div className="flex-1 min-w-0">
              <h2 id="create-recipe-title" className="text-xl leading-snug font-bold text-gray-900 wrap-anywhere">{recipe?.name || t("Food Menu's name")}</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">{recipe?.short_description || t("short-description")}</p>
              <div className="flex flex-wrap gap-2 mt-3">
                {recipe?.tags?.slice(0, 2).map((tag, idx) => (
                  <span key={idx} className={`text-xs leading-relaxed font-medium px-2 py-0.5 rounded-full wrap-anywhere ${idx === 0 ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"}`}>{tag}</span>
                ))}
              </div>
            </div>
          </section>

          <section className="py-6 border-b border-gray-200" aria-labelledby="create-ingredients-heading">
            <div className="flex flex-wrap justify-between items-center gap-2 mb-3">
              <h3 id="create-ingredients-heading" className="text-lg font-bold text-gray-900">{t("วัตถุดิบที่เลือก")}</h3>
              <button type="button" onClick={() => setShowFridge(!showFridge)} aria-expanded={showFridge} aria-controls="create-recipe-fridge"
                className={`min-h-11 flex items-center gap-2 text-sm font-medium px-3 py-2 rounded-full transition-colors ${showFridge ? "bg-[#FDECE5] text-[#9F351F]" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}>
                <Refrigerator aria-hidden="true" className="w-4 h-4 shrink-0" />
                {showFridge ? t("ปิดตู้เย็น") : t("+ จากตู้เย็น")}
              </button>
            </div>
            {currentIngredients && currentIngredients.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {currentIngredients.map(ing => (
                  <div key={ing.id} className="max-w-full min-h-11 bg-[#FDECE5] border border-[#B93E25] pl-3 rounded-full flex items-center gap-2">
                    <img src={ing.image} alt="" className="w-6 h-6 rounded-full object-cover shrink-0" />
                    <span className="block min-w-0 text-sm font-medium text-[#9F351F] wrap-anywhere first-letter:uppercase">{ing.name}</span>
                    <button type="button" onClick={() => removeIngredient(ing.id)} aria-label={t("นำ {name} ออกจากสูตร", { name: ing.name })}
                      className="group w-11 h-11 shrink-0 rounded-full text-[#9F351F] flex items-center justify-center">
                      <span className="w-7 h-7 rounded-full flex items-center justify-center transition-colors group-hover:bg-[#B93E25] group-hover:text-white group-active:bg-[#9F351F] group-active:text-white">
                        <X aria-hidden="true" className="w-4 h-4" />
                      </span>
                    </button>
                  </div>
                ))}
              </div>
            )}
            {showFridge && (
              <div id="create-recipe-fridge" className="bg-gray-50 rounded-2xl p-4 mt-4">
                <h4 className="text-sm font-semibold text-gray-900 mb-3">{t("วัตถุดิบใน My Fridge")}</h4>
                {userIngredients && userIngredients.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {userIngredients.map(ing => {
                      const isSelected = currentIngredients.some(c => c.name === ing.name);
                      return <button key={ing.id} type="button" onClick={() => !isSelected && addFromFridge(ing)} disabled={isSelected}
                        className={`max-w-full min-h-11 px-3 py-2 rounded-xl flex items-center gap-2 text-left text-sm transition-colors ${isSelected ? "bg-gray-200 text-gray-600 cursor-not-allowed" : "bg-white border border-gray-300 text-gray-700 hover:border-[#B93E25] hover:text-[#B93E25]"}`}>
                        <img src={ing.image} alt="" className="w-6 h-6 rounded-full object-cover shrink-0"
                          onError={e => (e.target.src = "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=150")} />
                        <span className="block min-w-0 wrap-anywhere first-letter:uppercase">{ing.name}
                          {expiryBadgeLabel(ing.expiry_date, locale) && <span className="block text-xs font-medium text-red-700">{expiryBadgeLabel(ing.expiry_date, locale)}</span>}
                        </span>
                        {!isSelected && <Plus aria-hidden="true" className="w-4 h-4 shrink-0" />}
                      </button>;
                    })}
                  </div>
                ) : <p className="text-sm leading-relaxed text-gray-600">{t("ไม่มีวัตถุดิบในตู้เย็น (คุณสามารถกดเพิ่มได้ที่แถบ My Fridge ด้านล่าง)")}</p>}
              </div>
            )}
          </section>

          <div className="create-recipe-preferences space-y-8 pt-6">
            <fieldset className="min-w-0">
              <legend className="text-lg font-semibold text-gray-900">{t("รสชาติ")}</legend>
              <p className="mt-1 mb-3 text-sm text-gray-600">{t("เลือกได้ 1 รสชาติ หรือไม่ระบุ")}</p>
              <OptionChips options={TASTE_OPTIONS} selected={taste} onToggle={setTaste} />
              {taste === OTHER_OPTION && <input type="text" value={tasteOther} onChange={e => setTasteOther(e.target.value)}
                aria-label={t("ระบุรสชาติที่ต้องการ")} placeholder={t("ระบุรสชาติที่ต้องการ")}
                className="mt-4 w-full min-h-12 border border-gray-400 rounded-xl px-4 py-3 text-base text-gray-900 placeholder:text-gray-500" />}
            </fieldset>

            <CookingPreferenceFields value={preferences.value} onChange={preferences.edit}
              allergyError={allergyError} allergyInput={allergyInput} onAllergyEdit={() => setAllergyError(null)} />

            <div>
              <label htmlFor="create-recipe-extra" className="block text-lg font-bold text-gray-900 mb-3">{t("ความต้องการอื่นๆ (ถ้ามี)")}</label>
              <textarea id="create-recipe-extra" rows={4} placeholder={t("เช่น สิ่งที่ต้องระวัง")} value={extra} onChange={e => setExtra(e.target.value)}
                className="w-full min-w-0 border border-gray-300 bg-white rounded-2xl p-4 text-gray-900 placeholder:text-gray-500 text-base resize-y" />
            </div>
          </div>
        </main>

        <div className="create-recipe-actions shrink-0 border-t border-gray-200 bg-white px-5 pt-3 pb-4">
          <PreferenceLoadStatus status={preferences.status} retry={preferences.retry} />
          {preferences.status === "ready" && preferenceIssue && <p role="status" className="mb-3 text-sm text-gray-700">{t(preferenceIssue)}</p>}
          {allergyError && <p id="allergy-error" role="alert" className="text-sm leading-relaxed text-red-700 mb-3 break-words">{t(allergyError)}</p>}
          <button type="button" onClick={handleGenerateClick} disabled={isSubmitting || preferences.status !== "ready" || Boolean(preferenceIssue)} aria-busy={isSubmitting}
            className="w-full min-h-12 px-4 py-3 bg-[#B93E25] text-white rounded-full text-base font-semibold flex items-center justify-center gap-2 hover:bg-[#9F351F] disabled:opacity-50 transition-colors">
            <ChefHat aria-hidden="true" className="w-5 h-5 shrink-0" />
            {isSubmitting ? t("กำลังตรวจสอบอาการแพ้…") : t("สร้างเมนูอาหารกันเลย")}
          </button>
        </div>
        <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
    </div>
  );
}

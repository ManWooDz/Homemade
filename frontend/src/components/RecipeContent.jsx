import RecipeNutrition from "./RecipeNutrition";
import { useLocale } from "../context/LocaleContext";
import { Flame, AlertTriangle, Clock } from "lucide-react";
import { getTagColor } from "../utils/tagColors";

export default function RecipeContent({ recipe, onDone }) {
    const { t } = useLocale();
  return (
    <>
      <h2 className="text-[26px] font-bold text-black mb-2 leading-tight">
        {recipe.recipe_name}
      </h2>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-500">{t("สำหรับ")} {recipe.servings} {t("ที่")}</p>
        <div className="flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-gray-400" />
          <span className="text-gray-500 text-sm">
            {recipe.usage_time || t("error")}
          </span>
        </div>
      </div>

      {/* Diet Tags */}
      {recipe.diet_tags && recipe.diet_tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6 mt-3">
          {recipe.diet_tags.map((tag, idx) => (
            <span
              key={idx}
              className={`${getTagColor(tag)} px-3 py-1 rounded-full text-[12px] font-medium`}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Safety Warning */}
      {recipe.safety_warning &&
        recipe.safety_warning !== "ระวังความร้อนขณะประกอบอาหาร" && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-2xl p-4 flex gap-3 text-red-700 shadow-sm items-start">
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
            <span className="text-sm font-medium leading-relaxed">
              {recipe.safety_warning}
            </span>
          </div>
        )}

            <RecipeNutrition recipe={recipe} />

      {/* Ingredients */}
      <div className="mb-6">
        <h3 className="text-xl font-medium text-black mb-4">{t("วัตถุดิบที่ปรับแก้แล้ว")}</h3>
        <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{t("ตรวจสอบวัตถุดิบและปริมาณจริงก่อนเริ่มทำอาหาร")}</div>
        <ul className="flex flex-col gap-2">
          {recipe.adjusted_ingredients?.map((ing, idx) => (
            <li
              key={idx}
              className="bg-gray-50 flex items-center gap-3 p-3 rounded-xl border border-gray-100 shadow-[0_2px_4px_rgba(0,0,0,0.02)]"
            >
              <div className="w-2 h-2 rounded-full bg-[#EF5A3A]"></div>
              <span className="text-gray-700 text-[15px]">{ing}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Instructions */}
      <div className="mb-6">
        <h3 className="text-xl font-medium text-black mb-4 flex items-center gap-2">
          <Flame className="w-5 h-5 text-[#EF5A3A]" />{t("วิธีทำ")}</h3>
        <div className="flex flex-col gap-4">
          {recipe.instructions?.map((step, idx) => {
            const cleanedStep = step.replace(/^\d+\.\s*/, "");
            return (
              <div key={idx} className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-orange-100 text-[#EF5A3A] font-bold flex items-center justify-center shrink-0">
                  {idx + 1}
                </div>
                <p className="text-gray-700 leading-relaxed pt-1 flex-1">
                  {cleanedStep}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Done Button (hidden when read-only, e.g. viewing from history) */}
      {onDone && (
        <button
          onClick={onDone}
          className="bg-[#EF5A3A] text-white px-5 py-4.5 rounded-full text-lg font-bold shadow-md mt-6 w-full mb-8 hover:bg-orange-600 transition"
        >{t("เสร็จสิ้น")}</button>
      )}
    </>
  );
}

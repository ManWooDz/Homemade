import RecipeNutrition from "./RecipeNutrition";
import RecipeInstructions from "./RecipeInstructions";
import { useLocale } from "../context/LocaleContext";
import { AlertTriangle, Clock } from "lucide-react";
import { getTagColor } from "../utils/tagColors";

export default function RecipeContent({ recipe, onDone, compact = false }) {
    const { t } = useLocale();
  return (
    <>
      <h2 className="recipe-title text-2xl font-bold text-black mb-2 leading-normal">
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
        <section className="recipe-tags mb-6 mt-3">
          {compact && <h3>{t("Tag")}</h3>}
          <div className="flex flex-wrap gap-2">
          {recipe.diet_tags.map((tag, idx) => (
            <span
              key={idx}
              className={`${getTagColor(tag)} px-3 py-1 rounded-full text-xs font-medium max-w-full break-words`}
            >
              {tag}
            </span>
          ))}
          </div>
        </section>
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

      <RecipeNutrition recipe={recipe} compact={compact} />

      {/* Ingredients */}
      <div className="mb-6">
        <h3 className="text-xl font-medium text-black mb-4">{t("วัตถุดิบที่ปรับแก้แล้ว")}</h3>
        <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{t("ตรวจสอบวัตถุดิบและปริมาณจริงก่อนเริ่มทำอาหาร")}</div>
        <ul className="flex flex-col gap-2">
          {recipe.adjusted_ingredients?.map((ing, idx) => (
            <li
              key={idx}
              className="recipe-ingredient-line bg-gray-50 flex items-center gap-3 p-3 rounded-xl border border-gray-100 shadow-[0_2px_4px_rgba(0,0,0,0.02)]"
            >
              <div className="w-2 h-2 rounded-full bg-[#EF5A3A]"></div>
              <span className="text-gray-700 text-base">{ing}</span>
            </li>
          ))}
        </ul>
      </div>

      <RecipeInstructions instructions={recipe.instructions} compact={compact} />

      {/* Done Button (hidden when read-only, e.g. viewing from history) */}
      {onDone && (
        <button
          onClick={onDone}
          className="recipe-primary-action bg-[#EF5A3A] text-white px-5 py-4.5 rounded-full text-lg font-bold shadow-md mt-6 w-full mb-8 hover:bg-orange-600 transition"
        >{t("เสร็จสิ้น")}</button>
      )}
    </>
  );
}

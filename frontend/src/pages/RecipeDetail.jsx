import RecipeNutrition from "../components/RecipeNutrition";
import RecipeSheet from "../components/RecipeSheet";
import RecipeInstructions from "../components/RecipeInstructions";
import { useLocale } from "../context/LocaleContext";
import { useState } from "react";
import { ChevronLeft, Heart, Star, Clock } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";

import BottomMenu from "../components/bottomMenu";
import { getTagColor } from "../utils/tagColors";

export default function RecipeDetail({
  recipe,
  onBack,
  onConfirm,
  activeTab,
  setActiveTab,
  isFavorite,
  onToggleFavorite,
}) {
    const { t } = useLocale();
  const time = recipe?.estimated_total_time;
  const hasTime = Number.isSafeInteger(time?.min_minutes) && Number.isSafeInteger(time?.max_minutes)
    && time.min_minutes > 0 && time.max_minutes >= time.min_minutes;
  const [ingredients, setIngredients] = useState(() => {
    if (recipe && recipe.ingredients) {
      return recipe.ingredients.map((ing, index) => ({
        id: index + 1,
        name: ing.name || ing,
        image:
          ing.image ||
          "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=150",
        selected: true,
      }));
    }
    return [
      {
        id: 1,
        name: "Green Oak",
        image:
          "https://images.unsplash.com/photo-1622206151226-18ca2c9ab4a1?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80",
        selected: true,
      },
      {
        id: 2,
        name: "Tomatoes",
        image:
          "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80",
        selected: true,
      },
      {
        id: 3,
        name: "Purple cabbage",
        image:
          "https://images.unsplash.com/photo-1596484552834-6a58f8510a76?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80",
        selected: true,
      },
    ];
  });

  const toggleIngredient = (id) => {
    setIngredients(
      ingredients.map((ing) =>
        ing.id === id ? { ...ing, selected: !ing.selected } : ing,
      ),
    );
  };

  return (
    <div className="recipe-detail-screen h-dvh bg-gray-100 flex justify-center font-sans overflow-hidden">
      <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
        {/* Header Actions */}
        <div className="absolute top-8 left-0 right-0 px-6 flex justify-between items-center z-20">
          <button
            onClick={onBack}
            aria-label={t("Back")}
            className="w-10 h-10 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
          <button
            onClick={() => onToggleFavorite?.(recipe?.id)}
            disabled={recipe?.id == null}
            aria-label={
              isFavorite ? t("เอาออกจากรายการโปรด") : t("เพิ่มในรายการโปรด")
            }
            aria-pressed={!!isFavorite}
            className={
              isFavorite ? "text-red-500" : "text-gray-400 hover:text-red-500"
            }
          >
            <Heart className={`w-8 h-8 ${isFavorite ? "fill-current" : ""}`} />
          </button>
        </div>

        {/* Logo & Top Image Area */}
        <div className="pt-8 pb-32 flex flex-col items-center bg-white relative z-10">
          <div className="mb-6">
            <img
              src={logo}
              alt="HomeMade"
              className="h-[72px] object-contain"
            />
          </div>
          {/* Image */}
          <div className="w-64 h-64 rounded-full overflow-hidden shadow-sm">
            <img
              src={recipe?.image || "backend/images/No-image-available.png"}
              alt={recipe?.name || t("Error Recipe Name")}
              className="w-full h-full object-cover"
            />
          </div>
        </div>

        <RecipeSheet>
            <h2 className="recipe-title">
              {recipe?.name || t("Dishes Name")}
            </h2>
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 mb-2">
              <div className="flex items-center gap-2">
                <Star className="w-5 h-5 text-orange-400 fill-orange-400" />
                <span className="font-bold text-black text-sm">
                  {recipe?.ratings || t("error")}
                </span>
                <span className="text-gray-500 text-sm mb-0">
                  ({recipe?.review || t("error")} {t("Reviews)")}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-gray-400" />
                <span className="text-gray-500 text-sm">
                  {hasTime ? t("ประมาณ {min}–{max} นาที", { min: time.min_minutes, max: time.max_minutes }) : t("ยังไม่มีข้อมูลเวลา")}
                </span>
              </div>
            </div>

            {hasTime && (
              <p className="text-gray-500 text-xs leading-relaxed mb-4">
                {t("รวมเตรียม ปรุง และรอตามสูตร โดยวัตถุดิบสำเร็จรูปที่ระบุถือว่าเตรียมแล้ว")}
              </p>
            )}

            {recipe?.tags && recipe.tags.length > 0 && (
              <section className="recipe-tags">
                <h3>{t("Tag")}</h3>
                <div className="flex flex-wrap gap-2">
                {recipe.tags.map((tag, i) => (
                  <span
                    key={i}
                    className={`${getTagColor(tag)} text-xs font-medium px-3 py-1 rounded-full`}
                  >
                    {tag}
                  </span>
                ))}
                </div>
              </section>
            )}

            <h3 className="text-xl font-medium text-black mb-2">{t("Description")}</h3>
            <p className="text-black text-sm mb-6 leading-relaxed">
              {recipe?.short_description || t("error")}
            </p>

            <RecipeNutrition recipe={recipe} compact />

            <h3 className="text-xl font-medium text-black mb-4">{t("Ingredient")}</h3>
            <p id="recipe-ingredient-help" className="text-sm text-gray-600 leading-relaxed mb-3">
              {t("เลือกวัตถุดิบที่ต้องการใช้ในสูตร")}
            </p>
            <div className="flex flex-col gap-3">
              {ingredients.map((ing) => (
                <label
                  key={ing.id}
                  className="recipe-ingredient-choice"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-white rounded-full overflow-hidden p-1 shadow-sm">
                      <img
                        src={ing.image}
                        alt={ing.name}
                        className="w-full h-full object-cover rounded-full"
                      />
                    </div>
                    <div className="flex flex-col justify-center">
                      <span className="font-medium text-black text-base capitalize">
                        {ing.name}
                      </span>
                    </div>
                  </div>
                  <input type="checkbox" checked={ing.selected} onChange={() => toggleIngredient(ing.id)} aria-label={ing.name} aria-describedby="recipe-ingredient-help" className="h-5 w-5 shrink-0 accent-[#B93E25]" />
                </label>
              ))}
            </div>
              <RecipeInstructions instructions={recipe?.instructions} compact />
              <button
                onClick={() =>
                  onConfirm(ingredients.filter((ing) => ing.selected))
                }
                className="recipe-primary-action"
              >{t("ดำเนินการต่อ")}</button>
        </RecipeSheet>

        {/* === 🔘 Bottom Navigation === */}
        <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
    </div>
  );
}

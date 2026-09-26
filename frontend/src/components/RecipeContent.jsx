import { Flame, AlertTriangle, Clock } from "lucide-react";
import { getTagColor } from "../utils/tagColors";

export default function RecipeContent({ recipe, onDone }) {
  return (
    <>
      <h2 className="text-[26px] font-bold text-black mb-2 leading-tight">
        {recipe.recipe_name}
      </h2>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-500">สำหรับ {recipe.servings} ที่</p>
        <div className="flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-gray-400" />
          <span className="text-gray-500 text-sm">
            {recipe.usage_time || "error"}
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

      {/* Nutrition Section */}
      {recipe.nutrition && (
        <div className="mb-6">
          <h3 className="text-xl font-medium text-black mb-4">
            {recipe.nutrition.basis === "per_serving"
              ? "โภชนาการต่อ 1 ที่ (คาดการณ์)"
              : "โภชนาการที่คาดการณ์"}
          </h3>
          <div className="flex flex-col gap-3">
            <div className="bg-[#FFF6F2] rounded-3xl p-5 flex justify-between items-center shadow-sm">
              <div className="flex flex-col gap-1">
                <span className="text-4xl font-semibold text-[#EF5A3A] leading-none">
                  {recipe.nutrition.calories}
                </span>
                <span className="text-lg text-gray-500 font-medium">
                  {recipe.nutrition.basis === "per_serving"
                    ? "แคลอรี่ต่อ 1 ที่"
                    : "แคลอรี่"}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-[#e4fbec] rounded-3xl p-4 flex flex-col justify-center items-center shadow-sm h-25">
                <span className="text-2xl font-bold text-black leading-none mb-1">
                  {recipe.nutrition.carbs_g}g
                </span>
                <span className="text-[12px] font-medium text-[#767676]">
                  คาร์บ
                </span>
              </div>
              <div className="bg-[#eaf3ff] rounded-3xl p-4 flex flex-col justify-center items-center shadow-sm h-25">
                <span className="text-2xl font-bold text-black leading-none mb-1">
                  {recipe.nutrition.protein_g}g
                </span>
                <span className="text-[12px] font-medium text-[#767676]">
                  โปรตีน
                </span>
              </div>
              <div className="bg-[#fffad8] rounded-3xl p-4 flex flex-col justify-center items-center shadow-sm h-25">
                <span className="text-2xl font-bold text-black leading-none mb-1">
                  {recipe.nutrition.fat_g}g
                </span>
                <span className="text-[12px] font-medium text-[#767676]">
                  ไขมัน
                </span>
              </div>
            </div>

            {/* Extra nutrients */}
            <div className="bg-white rounded-3xl p-5 shadow-sm flex flex-col gap-4">
              {[
                {
                  label: "น้ำตาล",
                  key: "sugar_g",
                  unit: "g",
                  max: 50,
                  color: "#FF5C8A",
                },
                {
                  label: "โซเดียม",
                  key: "sodium_mg",
                  unit: "mg",
                  max: 2300,
                  color: "#8B5CF6",
                },
                {
                  label: "ใยอาหาร",
                  key: "fiber_g",
                  unit: "g",
                  max: 30,
                  color: "#22C55E",
                },
                {
                  label: "วิตามินซี",
                  key: "vitamin_c_mg",
                  unit: "mg",
                  max: 90,
                  color: "#F59E0B",
                },
              ]
                .filter(
                  (n) =>
                    recipe.nutrition[n.key] !== undefined &&
                    recipe.nutrition[n.key] !== null,
                )
                .map((n) => {
                  const value = recipe.nutrition[n.key];
                  const pct = Math.max(0, Math.min(100, (value / n.max) * 100));
                  return (
                    <div key={n.key} className="flex items-center gap-3">
                      <span className="text-sm font-medium text-[#767676] w-20 shrink-0">
                        {n.label}
                      </span>
                      <div className="flex-1 h-2 bg-black/10 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${pct}%`, backgroundColor: n.color }}
                        ></div>
                      </div>
                      <span className="text-sm font-semibold text-black w-16 text-right shrink-0">
                        {value}
                        {n.unit}
                      </span>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      )}

      {/* Ingredients */}
      <div className="mb-6">
        <h3 className="text-xl font-medium text-black mb-4">
          วัตถุดิบที่ปรับแก้แล้ว
        </h3>
        <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          ตรวจสอบวัตถุดิบและปริมาณจริงก่อนเริ่มทำอาหาร
        </div>
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
          <Flame className="w-5 h-5 text-[#EF5A3A]" />
          วิธีทำ
        </h3>
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
        >
          เสร็จสิ้น
        </button>
      )}
    </>
  );
}

import { useRef, useState } from "react";
import { ChevronLeft, Flame, AlertTriangle, ChefHat, Clock, Star, X } from "lucide-react";
import { motion, useMotionValue, animate } from "framer-motion";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import { getTagColor } from "../utils/tagColors";

export default function CookingPage({
  recipe,
  generatedRecipe,
  isGenerating,
  onBack,
  activeTab,
  setActiveTab,
  isCustom,
}) {
  console.log("CookingPage");

  const [showRatingModal, setShowRatingModal] = useState(false);
  const [selectedRating, setSelectedRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);

  const finishCooking = () => {
    setShowRatingModal(true);
  };

  const submitRating = () => {
    // TODO: send { recipe_name: generatedRecipe.recipe_name, stars: selectedRating }
    // to backend once a rating-storage endpoint exists.
    console.log("[RATING]", {
      recipe_name: generatedRecipe?.recipe_name,
      stars: selectedRating,
    });
    setShowRatingModal(false);
    setActiveTab("home");
  };

  const skipRating = () => {
    setShowRatingModal(false);
    setActiveTab("home");
  };

  const sheetY = useMotionValue(0);
  const contentRef = useRef(null);
  const lastTouchY = useRef(null);

  const expandSheet = () => {
    animate(sheetY, -200, { type: "spring", stiffness: 300, damping: 30 });
  };

  const collapseSheet = () => {
    animate(sheetY, 0, { type: "spring", stiffness: 300, damping: 30 });
  };

  const isScrollAtBottom = (el) =>
    el.scrollHeight - el.scrollTop - el.clientHeight <= 1;

  const isScrollAtTop = (el) => el.scrollTop <= 0;

  const handleWheel = (e) => {
    const el = contentRef.current;
    if (!el) return;
    if (isScrollAtBottom(el) && e.deltaY > 0) {
      expandSheet();
    } else if (sheetY.get() <= -200 && isScrollAtTop(el) && e.deltaY < 0) {
      collapseSheet();
    }
  };

  const handleTouchStart = (e) => {
    lastTouchY.current = e.touches[0].clientY;
  };

  const handleTouchMove = (e) => {
    const el = contentRef.current;
    if (!el || lastTouchY.current === null) return;
    const currentY = e.touches[0].clientY;
    const deltaY = lastTouchY.current - currentY; // finger moving up = scrolling down
    lastTouchY.current = currentY;
    if (isScrollAtBottom(el) && deltaY > 0) {
      expandSheet();
    } else if (sheetY.get() <= -200 && isScrollAtTop(el) && deltaY < 0) {
      collapseSheet();
    }
  };

  // Loading Screen
  if (isGenerating) {
    return (
      <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
        <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl items-center justify-center space-y-6">
          <motion.div
            initial={{ opacity: 0.5, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1.1 }}
            transition={{
              repeat: Infinity,
              duration: 1,
              repeatType: "reverse",
            }}
          >
            <ChefHat className="w-24 h-24 text-[#EF5A3A] drop-shadow-lg" />
          </motion.div>
          <h2 className="text-2xl font-bold text-gray-800 tracking-wide">
            กำลังคิดค้นเมนู...
          </h2>
          <p className="text-gray-500 text-center px-8">
            เชฟ AI กำลังนำวัตถุดิบและเงื่อนไขของคุณมาปรุงเป็นสูตรพิเศษ
          </p>
        </div>
      </div>
    );
  }

  // Fallback if no recipe generated successfully yet
  if (!generatedRecipe) {
    return (
      <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
        <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl items-center justify-center space-y-4">
          <p className="text-gray-500">เกิดข้อผิดพลาดในการสร้างสูตรอาหาร</p>
          <button
            onClick={onBack}
            className="bg-[#EF5A3A] text-white px-6 py-2 rounded-full font-medium shadow-sm"
          >
            กลับไปแก้ไข
          </button>
          <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>
      </div>
    );
  }

  // Success Screen
  const renderRecipeContent = () => (
    <>
      <h2 className="text-[26px] font-bold text-black mb-2 leading-tight">
        {generatedRecipe.recipe_name}
      </h2>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-500">
          สำหรับ {generatedRecipe.servings} ที่
        </p>
        <div className="flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-gray-400" />
          <span className="text-gray-500 text-sm">
            {generatedRecipe.usage_time || "error"}
          </span>
        </div>
      </div>

      {/* Diet Tags */}
      {generatedRecipe.diet_tags && generatedRecipe.diet_tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6 mt-3">
          {generatedRecipe.diet_tags.map((tag, idx) => (
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
      {generatedRecipe.safety_warning &&
        generatedRecipe.safety_warning !== "ระวังความร้อนขณะประกอบอาหาร" && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-2xl p-4 flex gap-3 text-red-700 shadow-sm items-start">
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
            <span className="text-sm font-medium leading-relaxed">
              {generatedRecipe.safety_warning}
            </span>
          </div>
        )}

      {/* Nutrition Section */}
      {generatedRecipe.nutrition && (
        <div className="mb-6">
          <h3 className="text-xl font-medium text-black mb-4">
            {generatedRecipe.nutrition.basis === "per_serving"
              ? "โภชนาการต่อ 1 ที่ (คาดการณ์)"
              : "โภชนาการที่คาดการณ์"}
          </h3>
          <div className="flex flex-col gap-3">
            <div className="bg-[#FFF6F2] rounded-3xl p-5 flex justify-between items-center shadow-sm">
              <div className="flex flex-col gap-1">
                <span className="text-4xl font-semibold text-[#EF5A3A] leading-none">
                  {generatedRecipe.nutrition.calories}
                </span>
                <span className="text-lg text-gray-500 font-medium">
                  {generatedRecipe.nutrition.basis === "per_serving"
                    ? "แคลอรี่ต่อ 1 ที่"
                    : "แคลอรี่"}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-[#e4fbec] rounded-3xl p-4 flex flex-col justify-center items-center shadow-sm h-25">
                <span className="text-2xl font-bold text-black leading-none mb-1">
                  {generatedRecipe.nutrition.carbs_g}g
                </span>
                <span className="text-[12px] font-medium text-[#767676]">
                  คาร์บ
                </span>
              </div>
              <div className="bg-[#eaf3ff] rounded-3xl p-4 flex flex-col justify-center items-center shadow-sm h-25">
                <span className="text-2xl font-bold text-black leading-none mb-1">
                  {generatedRecipe.nutrition.protein_g}g
                </span>
                <span className="text-[12px] font-medium text-[#767676]">
                  โปรตีน
                </span>
              </div>
              <div className="bg-[#fffad8] rounded-3xl p-4 flex flex-col justify-center items-center shadow-sm h-25">
                <span className="text-2xl font-bold text-black leading-none mb-1">
                  {generatedRecipe.nutrition.fat_g}g
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
                    generatedRecipe.nutrition[n.key] !== undefined &&
                    generatedRecipe.nutrition[n.key] !== null,
                )
                .map((n) => {
                  const value = generatedRecipe.nutrition[n.key];
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
          {generatedRecipe.adjusted_ingredients?.map((ing, idx) => (
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
          {generatedRecipe.instructions?.map((step, idx) => {
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

      {/* Done Button */}
      <button
        onClick={finishCooking}
        className="bg-[#EF5A3A] text-white px-5 py-4.5 rounded-full text-lg font-bold shadow-md mt-6 w-full mb-8 hover:bg-orange-600 transition"
      >
        เสร็จสิ้น
      </button>
    </>
  );

  const renderRatingModal = () =>
    showRatingModal && (
      <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/40 px-6">
        <div className="w-full max-w-sm bg-white rounded-3xl shadow-2xl p-6 relative">
          <button
            onClick={skipRating}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>

          <h3 className="text-xl font-bold text-black text-center mb-2">
            ให้คะแนนเมนูนี้
          </h3>
          <p className="text-sm text-gray-500 text-center mb-6">
            {generatedRecipe?.recipe_name}
          </p>

          <div className="flex items-center justify-center gap-2 mb-8">
            {[1, 2, 3, 4, 5].map((n) => {
              const filled = n <= (hoverRating || selectedRating);
              return (
                <button
                  key={n}
                  onClick={() => setSelectedRating(n)}
                  onMouseEnter={() => setHoverRating(n)}
                  onMouseLeave={() => setHoverRating(0)}
                  className="p-1"
                >
                  <Star
                    className={`w-9 h-9 transition-colors ${
                      filled
                        ? "text-orange-400 fill-orange-400"
                        : "text-gray-300"
                    }`}
                  />
                </button>
              );
            })}
          </div>

          <button
            onClick={submitRating}
            disabled={selectedRating === 0}
            className="bg-[#EF5A3A] text-white px-5 py-3 rounded-full text-base font-bold shadow-md w-full disabled:opacity-40 disabled:cursor-not-allowed hover:bg-orange-600 transition"
          >
            ส่งคะแนน
          </button>
          <button
            onClick={skipRating}
            className="text-gray-400 text-sm font-medium w-full text-center mt-3"
          >
            ข้าม
          </button>
        </div>
      </div>
    );

  return (
    <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
      <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
        {/* Header & Logo Area for Both Flows */}
        <div className="pt-8 px-6 flex items-center justify-center relative z-20 shrink-0 mb-4 bg-white">
          <button
            onClick={onBack}
            className="absolute left-6 w-10 h-10 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
          <img src={logo} alt="HomeMade" className="h-18 object-contain" />
        </div>

        {isCustom ? (
          // Custom Flow layout (no image, normal div)
          <div className="flex-1 overflow-y-auto px-6 pb-24 scrollbar-hide">
            {renderRecipeContent()}
          </div>
        ) : (
          // Normal Flow layout (image + draggable bottom sheet)
          <>
            {/* Image Area */}
            <div className="pb-32 flex flex-col items-center bg-white relative z-10 pt-2">
              {/* Image (Fallback to base recipe since LLM doesn't generate images easily) */}
              <div className="w-64 h-64 rounded-full overflow-hidden shadow-sm">
                <img
                  src={recipe?.image || "backend/images/No-image-available.png"}
                  alt={generatedRecipe.recipe_name}
                  className="w-full h-full object-cover"
                />
              </div>
            </div>

            {/* Draggable Bottom Sheet overlay */}
            <motion.div
              className="absolute left-0 right-0 mx-auto w-full max-w-[430px] bg-white rounded-t-[40px] shadow-[0_-10px_40px_rgba(0,0,0,0.1)] z-30 pb-10"
              drag="y"
              dragConstraints={{ top: -200, bottom: 0 }}
              style={{ top: "45%", height: "90%", y: sheetY }}
            >
              <div className="w-full flex justify-center pt-4 pb-2">
                <div className="w-12 h-1.5 bg-gray-200 rounded-full"></div>
              </div>

              <div
                ref={contentRef}
                onWheel={handleWheel}
                onTouchStart={handleTouchStart}
                onTouchMove={handleTouchMove}
                className="px-6 h-full overflow-y-auto pb-50 scrollbar-hide"
              >
                {renderRecipeContent()}
              </div>
            </motion.div>
          </>
        )}

        {/* Bottom Navigation */}
        <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />

        {renderRatingModal()}
      </div>
    </div>
  );
}

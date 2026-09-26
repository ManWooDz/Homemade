import { useRef, useState } from "react";
import { ChevronLeft, ChefHat, Star } from "lucide-react";
import { motion, useMotionValue, animate } from "framer-motion";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import RecipeContent from "../components/RecipeContent";

export default function CookingPage({
  recipe,
  generatedRecipe,
  isGenerating,
  onBack,
  activeTab,
  setActiveTab,
  isCustom,
  onRateRecipe,
}) {
  console.log("CookingPage");

  const [showRatingModal, setShowRatingModal] = useState(false);
  const [selectedRating, setSelectedRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [selectedTag, setSelectedTag] = useState(null);
  const [feedbackText, setFeedbackText] = useState("");

  const FEEDBACK_TAGS = ["Delicious", "Great", "Tasty", "Not Bad", "Meh"];
  const FEEDBACK_MAX_LEN = 240;
  const RATING_MESSAGES = {
    1: "Not good at all",
    2: "Could be better",
    3: "It's okay",
    4: "Really good, I like it!",
    5: "Amazing, love it!",
  };

  const ratingSheetY = useMotionValue(0);

  const expandRatingSheet = () => {
    animate(ratingSheetY, -200, { type: "spring", stiffness: 300, damping: 30 });
  };

  const collapseRatingSheet = () => {
    animate(ratingSheetY, 0, { type: "spring", stiffness: 300, damping: 30 });
  };

  const finishCooking = () => {
    setSelectedRating(0);
    setHoverRating(0);
    setSelectedTag(null);
    setFeedbackText("");
    ratingSheetY.set(0);
    setShowRatingModal(true);
  };

  const submitRating = () => {
    // TODO: also send { recipe_name, stars, tag, feedback } to backend once a
    // rating-storage endpoint exists. For now it's merged into cookingHistory
    // (client-side only, lost on refresh) via onRateRecipe.
    const rating = {
      stars: selectedRating,
      tag: selectedTag,
      feedback: feedbackText,
    };
    console.log("[RATING]", {
      recipe_name: generatedRecipe?.recipe_name,
      ...rating,
    });
    onRateRecipe?.(generatedRecipe?._historyId, rating);
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

  const renderRatingModal = () =>
    showRatingModal && (
      <motion.div
        className="absolute left-0 right-0 mx-auto w-full max-w-107.5 bg-white rounded-t-[40px] shadow-[0_-10px_40px_rgba(0,0,0,0.15)] z-50"
        drag="y"
        dragConstraints={{ top: -200, bottom: 0 }}
        dragElastic={0.05}
        onDragEnd={() => {
          if (ratingSheetY.get() < -100) {
            expandRatingSheet();
          } else {
            collapseRatingSheet();
          }
        }}
        style={{ top: "45%", height: "90%", y: ratingSheetY }}
      >
        <div className="w-full flex justify-center pt-4 pb-2">
          <div className="w-12 h-1.5 bg-gray-200 rounded-full"></div>
        </div>

        <div className="px-6 h-full overflow-y-auto pb-6 scrollbar-hide">
          <div className="w-24 h-24 rounded-full overflow-hidden shadow-sm mx-auto mb-4">
            <img
              src={recipe?.image || "backend/images/No-image-available.png"}
              alt={generatedRecipe?.recipe_name}
              className="w-full h-full object-cover"
            />
          </div>

          {selectedRating === 0 ? (
            <>
              <h3 className="text-xl font-bold text-[#EF5A3A] text-center mb-1">
                How do you like it?
              </h3>
              <p className="text-sm text-gray-500 text-center mb-6">
                Rate your meal with this recipe?
              </p>
            </>
          ) : (
            <>
              <p className="text-sm text-gray-500 text-center mb-1">
                How do you like it?
              </p>
              <h3 className="text-xl font-bold text-[#EF5A3A] text-center mb-6">
                {RATING_MESSAGES[selectedRating]}
              </h3>
            </>
          )}

          <div className="flex items-center justify-center gap-2 mb-6">
            {[1, 2, 3, 4, 5].map((n) => {
              const filled = n <= (hoverRating || selectedRating);
              return (
                <button
                  key={n}
                  onClick={() => {
                    setSelectedRating(n);
                    expandRatingSheet();
                  }}
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

          {selectedRating > 0 && (
            <>
              <div className="flex flex-wrap justify-center gap-2 mb-6">
                {FEEDBACK_TAGS.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => setSelectedTag(tag)}
                    className={`px-4 py-2 rounded-full text-sm font-medium border transition ${
                      selectedTag === tag
                        ? "bg-[#EF5A3A] text-white border-[#EF5A3A]"
                        : "bg-white text-gray-700 border-gray-300"
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>

              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-[#EF5A3A] font-medium">
                  Tell us more about your meals ...
                </span>
                <span className="text-xs text-gray-400">
                  {FEEDBACK_MAX_LEN - feedbackText.length}/{FEEDBACK_MAX_LEN}
                </span>
              </div>
              <textarea
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                maxLength={FEEDBACK_MAX_LEN}
                placeholder="เช่น เผ็ด"
                className="w-full h-24 border border-gray-300 rounded-2xl p-3 text-sm text-gray-700 resize-none mb-6 focus:outline-none focus:border-[#EF5A3A]"
              />
            </>
          )}

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
      </motion.div>
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
            <RecipeContent recipe={generatedRecipe} onDone={finishCooking} />
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
                <RecipeContent recipe={generatedRecipe} onDone={finishCooking} />
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

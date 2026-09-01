import { useState } from "react";
import HeaderLogo from "../components/HeaderLogo";
import BackButton from "../components/BackButton";
import NextButton from "../components/NextButton";

export default function QuizStep6() {
  const goalCategories = [
    { id: "save_money", label: "💸 ประหยัดค่าอาหาร" },
    { id: "use_ingredients", label: "🥬 ใช้วัตถุดิบที่มีให้คุ้มค่า" },
    { id: "learn_cooking", label: "🍳 อยากฝึกทำอาหาร" },
    { id: "health", label: "❤️ ทำอาหารเพื่อสุขภาพ" },
    { id: "new_menu", label: "😋 อยากลองเมนูใหม่ ๆ" },
    { id: "save_time", label: "⏱️ ประหยัดเวลา" },
  ];

  // Multi-select State (Default เลือกตัวแรกตาม Figma)
  const [selectedGoals, setSelectedGoals] = useState(["save_money"]);

  const toggleSelect = (id) => {
    setSelectedGoals((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  return (
    <div className="w-full h-full px-4 pt-6 pb-10 bg-background-primary flex flex-col items-center overflow-hidden">
      {/* Top Header & Navigation */}
      <div className="w-full flex flex-col items-center">
        <HeaderLogo />
        <div className="w-full flex justify-between items-center mt-6">
          <BackButton to="/quiz-step-5" />
          <div className="text-body-medium font-semibold">
            <span className="text-text-brands">6</span>
            <span className="text-text-neutral">/6</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="w-full flex flex-col justify-start items-center mt-4">
        <h1 className="text-h2 font-semibold text-text-black text-center">
          คุณทำอาหารเพื่ออะไร?
        </h1>
        <p className="text-body-medium text-text-brands text-center mt-1 mb-6">
          เลือกได้มากกว่า 1 ข้อ
        </p>

        {/* Full-width Vertical List Container */}
        <div className="w-full flex flex-col gap-2.5 max-w-[358px]">
          {goalCategories.map((item) => {
            const isSelected = selectedGoals.includes(item.id);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => toggleSelect(item.id)}
                className={`w-full h-14 pl-3.5 pr-7 py-2 rounded-2xl flex items-center transition-all cursor-pointer ${
                  isSelected
                    ? "bg-button-secondary border border-border-stroke-brands shadow-[0px_0px_4px_0px_rgba(0,0,0,0.25)] text-text-black font-normal"
                    : "bg-background-primary border border-border-stroke-btn-tertiary text-text-tertiary font-normal hover:bg-background-tertiary"
                }`}
              >
                <span className="text-body-medium truncate">{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Bottom Next Button Container - นำทางไปหน้า /home */}
      <div className="w-full flex justify-end mt-auto">
        <NextButton to="/home" />
      </div>
    </div>
  );
}

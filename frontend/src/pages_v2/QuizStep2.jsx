import { useState } from "react";
import HeaderLogo from "../components/HeaderLogo";
import BackButton from "../components/BackButton";
import NextButton from "../components/NextButton";

export default function QuizStep2() {
  const foodCategories = [
    { id: "thai", label: "🍚 อาหารไทย" },
    { id: "asian", label: "🍜 อาหารเอเชีย" },
    { id: "western", label: "🍝 อาหารตะวันตก" },
    { id: "spicy", label: "🌶️ อาหารรสจัด" },
    { id: "healthy", label: "🥗 อาหารเพื่อสุขภาพ" },
    { id: "fastfood", label: "🍔 อาหาร Fast Food" },
    { id: "dessert", label: "🍰 ของหวาน" },
    { id: "easy", label: "🥘 อาหารทำง่าย ๆ" },
  ];

  const [selectedFoods, setSelectedFoods] = useState([]);

  const toggleSelect = (id) => {
    setSelectedFoods((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  return (
    <div className="w-full h-full px-4 pt-6 pb-10 bg-background-primary flex flex-col items-center overflow-hidden">
      {/* Top Header & Navigation */}
      <div className="w-full flex flex-col items-center">
        <HeaderLogo />
        <div className="w-full flex justify-between items-center">
          <BackButton to="/quiz-step-1" />
          <div className="text-body-medium font-semibold">
            <span className="text-text-brands">2</span>
            <span className="text-text-neutral">/6</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="w-full flex flex-col justify-start items-center mt-4">
        <h1 className="text-h2 font-semibold text-text-black text-center">
          คุณชอบอาหารแบบไหน?
        </h1>
        <p className="text-body-medium text-text-brands text-center mt-1 mb-6">
          เลือกได้มากกว่า 1 ข้อ
        </p>

        {/* Options Chips Container */}
        <div className="w-full flex justify-center items-center gap-2 flex-wrap max-w-[358px]">
          {foodCategories.map((item) => {
            const isSelected = selectedFoods.includes(item.id);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => toggleSelect(item.id)}
                className={`h-11 px-5 rounded-full flex justify-center items-center text-body-large transition-all cursor-pointer ${
                  isSelected
                    ? "bg-button-primary text-text-white font-normal"
                    : "bg-button-neutral text-text-tertiary border border-border-stroke-btn-tertiary font-normal hover:bg-background-tertiary"
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="w-full flex justify-end mt-auto">
        <NextButton to="/quiz-step-3" />
      </div>
    </div>
  );
}

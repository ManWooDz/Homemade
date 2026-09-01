import { useState } from "react";
import HeaderLogo from "../components/HeaderLogo";
import BackButton from "../components/BackButton";
import NextButton from "../components/NextButton";

export default function QuizStep4() {
  const equipmentCategories = [
    { id: "pan", label: "🍳 กระทะ" },
    { id: "pot", label: "🍲 หม้อ" },
    { id: "rice_cooker", label: "🍚 หม้อหุงข้าว" },
    { id: "electric_stove", label: "♨️ เตาไฟฟ้า" },
    { id: "gas_stove", label: "🔥 เตาแก๊ส" },
    { id: "oven", label: "🔥 เตาอบ" },
    { id: "air_fryer", label: "🫕 หม้อทอดไร้น้ำมัน" },
    { id: "microwave", label: "⚡ ไมโครเวฟ" },
    { id: "blender", label: "🥣 เครื่องปั่น" },
    { id: "other", label: "🧰 อื่น ๆ" },
  ];

  // State สำหรับเก็บรายการอุปกรณ์ที่เลือก (Default เป็น หม้อหุงข้าว ตาม Figma)
  const [selectedEquipments, setSelectedEquipments] = useState(["rice_cooker"]);

  const toggleSelect = (id) => {
    setSelectedEquipments((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  return (
    <div className="w-full h-full px-4 pt-6 pb-10 bg-background-primary flex flex-col items-center overflow-hidden">
      {/* Top Header & Navigation */}
      <div className="w-full flex flex-col items-center">
        <HeaderLogo />
        <div className="w-full flex justify-between items-center mt-6">
          <BackButton to="/quiz-step-3" />
          <div className="text-body-medium font-semibold">
            <span className="text-text-brands">4</span>
            <span className="text-text-neutral">/6</span>
          </div>
        </div>
      </div>

      {/* Main Content (Spacing เดียวกับ Step 2 และ 3) */}
      <div className="w-full flex flex-col justify-start items-center mt-4">
        <h1 className="text-h2 font-semibold text-text-black text-center">
          คุณมีอุปกรณ์อะไรบ้าง?
        </h1>
        <p className="text-body-medium text-text-brands text-center mt-1 mb-6">
          เลือกได้มากกว่า 1 ข้อ
        </p>

        {/* Options Chips Container */}
        <div className="w-full flex justify-center items-center gap-2 flex-wrap max-w-[358px]">
          {equipmentCategories.map((item) => {
            const isSelected = selectedEquipments.includes(item.id);
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

      {/* Bottom Next Button Container - ใช้ mt-auto ดันชิดล่างตำแหน่งเดิมทุกหน้า */}
      <div className="w-full flex justify-end mt-auto">
        <NextButton to="/quiz-step-5" />
      </div>
    </div>
  );
}

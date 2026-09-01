import { useState } from "react";
import HeaderLogo from "../components/HeaderLogo";
import BackButton from "../components/BackButton";
import NextButton from "../components/NextButton";

export default function QuizStep3() {
  const allergyCategories = [
    { id: "none", label: "✅ ไม่มีข้อจำกัด" },
    { id: "peanuts", label: "🥜 แพ้ถั่ว" },
    { id: "milk", label: "🥛 แพ้นม / ผลิตภัณฑ์จากนม" },
    { id: "seafood", label: "🦐 แพ้อาหารทะเล" },
    { id: "egg", label: "🥚 แพ้ไข่" },
    { id: "gluten", label: "🌾 แพ้แป้งสาลี / Gluten" },
    { id: "fish", label: "🐟 แพ้ปลา" },
    { id: "vegan", label: "🌿 ทาน Vegan" },
    { id: "vegetarian", label: "🌱 ทานมังสวิรัติ" },
    { id: "halal", label: "🕌 Halal" },
    { id: "other", label: "✏️ อื่น ๆ" },
  ];

  const [selectedAllergies, setSelectedAllergies] = useState([]);

  const toggleSelect = (id) => {
    if (id === "none") {
      // ถ้าเลือก "ไม่มีข้อจำกัด" ให้ล้างค่าตัวเลือกอื่นทั้งหมด
      setSelectedAllergies(["none"]);
      return;
    }

    setSelectedAllergies((prev) => {
      // เอา "ไม่มีข้อจำกัด" ออกถ้ามีการเลือกตัวเลือกอื่นเพิ่ม
      const filtered = prev.filter((item) => item !== "none");

      if (filtered.includes(id)) {
        const nextState = filtered.filter((item) => item !== id);
        // ถ้าไม่เหลือตัวเลือกอะไรเลย ให้กลับไปเลือก "ไม่มีข้อจำกัด"
        return nextState.length === 0 ? ["none"] : nextState;
      } else {
        return [...filtered, id];
      }
    });
  };

  return (
    <div className="w-full h-full px-4 pt-6 pb-10 bg-background-primary flex flex-col items-center overflow-hidden">
      {/* Top Header & Navigation */}
      <div className="w-full flex flex-col items-center">
        <HeaderLogo />
        <div className="w-full flex justify-between items-center ">
          <BackButton to="/quiz-step-2" />
          <div className="text-body-medium font-semibold">
            <span className="text-text-brands">3</span>
            <span className="text-text-neutral">/6</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="w-full flex flex-col justify-start items-center mt-4">
        <h1 className="text-h2 font-semibold text-text-black text-center">
          อาการแพ้ หรือข้อจำกัดของคุณ
        </h1>
        <p className="text-body-medium text-text-brands text-center mt-1 mb-6">
          เลือกได้มากกว่า 1 ข้อ
        </p>

        {/* Options Chips Container */}
        <div className="w-full flex justify-center items-center gap-2 flex-wrap max-w-[358px]">
          {allergyCategories.map((item) => {
            const isSelected = selectedAllergies.includes(item.id);
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
        <NextButton to="/quiz-step-4" />
      </div>
    </div>
  );
}

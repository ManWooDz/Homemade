import { useState } from "react";
import HeaderLogo from "../components/HeaderLogo";
import BackButton from "../components/BackButton";
import NextButton from "../components/NextButton";

export default function QuizStep5() {
  const frequencyOptions = [
    { id: "never", label: "🌱 แทบไม่เคย — 0 ครั้ง/สัปดาห์" },
    { id: "rarely", label: "🥄 นาน ๆ ทำที — 1–2 ครั้ง/สัปดาห์" },
    { id: "sometimes", label: "🍳 ทำเป็นบางครั้ง — 3–4 ครั้ง/สัปดาห์" },
    { id: "often", label: "👨‍🍳 ทำเป็นประจำ — 5–6 ครั้ง/สัปดาห์" },
    { id: "daily", label: "🔥 ทำอาหารทุกวัน — 7 ครั้งขึ้นไป/สัปดาห์" },
  ];

  // เลือกได้ข้อเดียว (Single Select) Default ตัวแรกตาม Figma
  const [selectedFrequency, setSelectedFrequency] = useState("never");

  return (
    <div className="w-full h-full px-4 pt-6 pb-10 bg-background-primary flex flex-col items-center overflow-hidden">
      {/* Top Header & Navigation */}
      <div className="w-full flex flex-col items-center">
        <HeaderLogo />
        <div className="w-full flex justify-between items-center mt-6">
          <BackButton to="/quiz-step-4" />
          <div className="text-body-medium font-semibold">
            <span className="text-text-brands">5</span>
            <span className="text-text-neutral">/6</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="w-full flex flex-col justify-start items-center mt-4">
        <h1 className="text-h2 font-semibold text-text-black text-center mb-6">
          คุณทำอาหารบ่อยแค่ไหน?
        </h1>

        {/* Full-width Vertical List Container */}
        <div className="w-full flex flex-col gap-2.5 max-w-[358px]">
          {frequencyOptions.map((item) => {
            const isSelected = selectedFrequency === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelectedFrequency(item.id)}
                className={`w-full h-14 pl-3.5 pr-7 py-2 rounded-2xl flex items-center transition-all cursor-pointer ${
                  isSelected
                    ? "bg-button-secondary border border-border-stroke-brands shadow-[0px_0px_4px_0px_rgba(0,0,0,0.25)] text-text-black"
                    : "bg-background-primary border border-border-stroke-btn-tertiary text-text-tertiary hover:bg-background-tertiary"
                }`}
              >
                <span className="text-body-medium font-normal truncate">
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Bottom Next Button Container - ใช้ mt-auto ดันชิดล่างตำแหน่งเดิมทุกหน้า */}
      <div className="w-full flex justify-end mt-auto">
        <NextButton to="/quiz-step-6" />
      </div>
    </div>
  );
}

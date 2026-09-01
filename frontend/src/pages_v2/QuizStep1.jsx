import { useState } from "react";
import Picker from "react-mobile-picker";
import HeaderLogo from "../components/HeaderLogo";
import BackButton from "../components/BackButton";
import NextButton from "../components/NextButton";

// สร้างตัวเลือกอายุตั้งแต่ 15 ถึง 80
const ages = Array.from({ length: 66 }, (_, i) => String(15 + i));
export default function QuizStep1() {
  const [pickerValue, setPickerValue] = useState({
    age: "25", // ค่าเริ่มต้น
  });

  return (
    <div className="w-full h-full px-4 pt-6 pb-10 bg-background-primary flex flex-col items-center overflow-hidden">
      {/* Top Header & Navigation */}
      <div className="w-full flex flex-col items-center">
        <HeaderLogo />
        <div className="w-full flex justify-between items-center mt-6">
          <BackButton to="/register" />
          <div className="text-body-medium font-semibold">
            <span className="text-text-brands">1</span>
            <span className="text-text-neutral">/6</span>
          </div>
        </div>
      </div>

      {/* Main Content & Single Wheel Picker */}
      <div className="w-full flex flex-col justify-start items-center mt-4">
        <h1 className="text-h2 font-semibold text-text-black text-center mb-8">
          คุณอายุเท่าไหร่?
        </h1>

        {/* Picker Wheel Container - ปรับให้ตรงกลางและมี 1 Wheel */}
        <div className="w-full max-w-[200px] custom-picker-container">
          <Picker
            value={pickerValue}
            onChange={setPickerValue}
            wheelMode="normal"
          >
            <Picker.Column name="age" className="w-full">
              {ages.map((age) => (
                <Picker.Item key={age} value={age}>
                  {({ selected }) => (
                    <div
                      className={`h-11 px-8 flex justify-center items-center rounded-xl text-body-large font-semibold transition-all ${
                        selected
                          ? "bg-button-primary text-text-white shadow-[0_0_30px_0_rgba(239,88,44,0.25)]"
                          : "text-text-black opacity-30"
                      }`}
                    >
                      {age} ปี
                    </div>
                  )}
                </Picker.Item>
              ))}
            </Picker.Column>
          </Picker>
        </div>
      </div>

      {/* Bottom Next Button Container - ใช้ mt-auto เหมือนกับทุกหน้า */}
      <div className="w-full flex justify-end mt-auto">
        <NextButton to="/quiz-step-2" />
      </div>
    </div>
  );
}

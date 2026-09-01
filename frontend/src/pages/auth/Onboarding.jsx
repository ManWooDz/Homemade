import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Picker from "react-mobile-picker";
import HeaderLogo from "../../components/HeaderLogo";
import BackButton from "../../components/BackButton";
import NextButton from "../../components/NextButton";

const OTHER_OPTION = "อื่น ๆ";
const NO_RESTRICTION = "ไม่มีข้อจำกัด";

const AGES = Array.from({ length: 66 }, (_, i) => String(15 + i));

const CUISINE_OPTIONS = [
  "อาหารไทย",
  "อาหารเอเชีย",
  "อาหารตะวันตก",
  "อาหารรสจัด",
  "อาหารเพื่อสุขภาพ",
  "อาหาร Fast Food",
  "ของหวาน",
  "อาหารทำง่าย ๆ",
];

const RESTRICTION_OPTIONS = [
  NO_RESTRICTION,
  "แพ้ถั่ว",
  "แพ้นม / ผลิตภัณฑ์จากนม",
  "แพ้ไข่",
  "แพ้อาหารทะเล",
  "แพ้แป้งสาลี / Gluten",
  "แพ้ปลา",
  "ทาน Vegan",
  "ทานมังสวิรัติ",
  "Halal",
  OTHER_OPTION,
];

const EQUIPMENT_OPTIONS = [
  "กระทะ",
  "หม้อ",
  "หม้อหุงข้าว",
  "เตาไฟฟ้า",
  "เตาแก๊ส",
  "เตาอบ",
  "หม้อทอดไร้น้ำมัน",
  "ไมโครเวฟ",
  "เครื่องปั่น",
  OTHER_OPTION,
];

const FREQUENCY_OPTIONS = [
  "แทบไม่เคย — 0 ครั้ง/สัปดาห์",
  "เมนู + ทำ — 1–2 ครั้ง/สัปดาห์",
  "ทำเป็นบางครั้ง — 3–4 ครั้ง/สัปดาห์",
  "ทำเป็นประจำ — 5–6 ครั้ง/สัปดาห์",
  "ทำอาหารทุกวัน — 7 ครั้งขึ้นไป/สัปดาห์",
];

const GOAL_OPTIONS = [
  "ประหยัดค่าอาหาร",
  "ใช้วัตถุดิบที่มีได้คุ้มค่า",
  "อยากฝึกทำอาหาร",
  "ทำอาหารเพื่อสุขภาพ",
  "อยากลองเมนูใหม่ ๆ",
  "ประหยัดเวลา",
];

const toggleInList = (list, option, noneValue) => {
  if (option === noneValue) {
    return list.includes(noneValue) ? [] : [noneValue];
  }
  if (list.includes(option)) {
    return list.filter((item) => item !== option);
  }
  return [...list.filter((item) => item !== noneValue), option];
};

// TODO(backend): POST /api/user-preferences once SQLite -> PostgreSQL migration lands.
// formData is already shaped for that payload.
function submitProfile(formData) {
  console.log("[onboarding] collected profile:", formData);
}

function StepCounter({ step, total }) {
  return (
    <div className="text-body-medium font-semibold">
      <span className="text-text-brands">{step}</span>
      <span className="text-text-neutral">/{total}</span>
    </div>
  );
}

function OptionChips({ options, selected, multiple, onToggle }) {
  return (
    <div className="w-full flex justify-center items-center gap-2 flex-wrap max-w-[358px]">
      {options.map((option) => {
        const isSelected = multiple
          ? selected.includes(option)
          : selected === option;
        return (
          <button
            key={option}
            type="button"
            onClick={() => onToggle(option)}
            className={`h-11 px-5 rounded-full flex justify-center items-center text-body-large transition-all cursor-pointer ${
              isSelected
                ? "bg-button-primary text-text-white font-normal"
                : "bg-button-neutral text-text-tertiary border border-border-stroke-btn-tertiary font-normal hover:bg-background-tertiary"
            }`}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}

function OptionList({ options, selected, multiple, onToggle }) {
  return (
    <div className="w-full flex flex-col gap-2.5 max-w-[358px]">
      {options.map((option) => {
        const isSelected = multiple
          ? selected.includes(option)
          : selected === option;
        return (
          <button
            key={option}
            type="button"
            onClick={() => onToggle(option)}
            className={`w-full h-14 pl-3.5 pr-7 py-2 rounded-2xl flex items-center transition-all cursor-pointer ${
              isSelected
                ? "bg-button-secondary border border-border-stroke-brands shadow-[0px_0px_4px_0px_rgba(0,0,0,0.25)] text-text-black"
                : "bg-background-primary border border-border-stroke-btn-tertiary text-text-tertiary hover:bg-background-tertiary"
            }`}
          >
            <span className="text-body-medium font-normal truncate">{option}</span>
          </button>
        );
      })}
    </div>
  );
}

function StepShell({ title, hint, children }) {
  return (
    <div className="w-full flex flex-col justify-start items-center mt-4">
      <h1 className="text-h2 font-semibold text-text-black text-center">
        {title}
      </h1>
      {hint && (
        <p className="text-body-medium text-text-brands text-center mt-1 mb-6">
          {hint}
        </p>
      )}
      {!hint && <div className="mb-8" />}
      {children}
    </div>
  );
}

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);

  const [pickerValue, setPickerValue] = useState({ age: "25" });

  const [cuisinePreferences, setCuisinePreferences] = useState([]);
  const [dietaryRestrictions, setDietaryRestrictions] = useState([]);
  const [restrictionOther, setRestrictionOther] = useState("");
  const [equipment, setEquipment] = useState([]);
  const [equipmentOther, setEquipmentOther] = useState("");
  const [cookingFrequency, setCookingFrequency] = useState("");
  const [cookingGoals, setCookingGoals] = useState([]);

  const handleBack = () => {
    if (step === 1) {
      if (window.history.state?.idx > 0) {
        navigate(-1);
      } else {
        navigate("/login");
      }
      return;
    }
    setStep((s) => s - 1);
  };

  const handleNext = () => {
    if (step === 6) {
      submitProfile({
        age: Number(pickerValue.age),
        cuisine_preferences: cuisinePreferences,
        dietary_restrictions: dietaryRestrictions.includes(OTHER_OPTION)
          ? [...dietaryRestrictions.filter((r) => r !== OTHER_OPTION), restrictionOther || OTHER_OPTION]
          : dietaryRestrictions,
        equipment: equipment.includes(OTHER_OPTION)
          ? [...equipment.filter((e) => e !== OTHER_OPTION), equipmentOther || OTHER_OPTION]
          : equipment,
        cooking_frequency: cookingFrequency,
        cooking_goals: cookingGoals,
      });
      navigate("/login", { state: { message: "Account created — please log in." } });
      return;
    }
    setStep((s) => s + 1);
  };

  return (
    <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
      <div className="w-full max-w-107.5 bg-white h-full relative shadow-2xl overflow-hidden flex flex-col">
        <div className="w-full flex-1 min-h-0 px-4 pt-6 pb-6 bg-background-primary flex flex-col items-center overflow-y-auto">
          <div className="w-full flex flex-col items-center">
            <HeaderLogo />
            <div className="w-full flex justify-between items-center mt-6">
              <BackButton onClick={handleBack} to="/login" />
              <StepCounter step={step} total={6} />
            </div>
          </div>

          {step === 1 && (
            <StepShell title="คุณอายุเท่าไหร่?">
              <div className="w-full max-w-[200px] custom-picker-container">
                <Picker
                  value={pickerValue}
                  onChange={setPickerValue}
                  wheelMode="normal"
                >
                  <Picker.Column name="age" className="w-full">
                    {AGES.map((age) => (
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
            </StepShell>
          )}

          {step === 2 && (
            <StepShell title="คุณชอบอาหารแบบไหน?" hint="เลือกได้มากกว่า 1 ข้อ">
              <OptionChips
                options={CUISINE_OPTIONS}
                selected={cuisinePreferences}
                multiple
                onToggle={(option) =>
                  setCuisinePreferences((prev) => toggleInList(prev, option))
                }
              />
            </StepShell>
          )}

          {step === 3 && (
            <StepShell title="อาการแพ้ หรือข้อจำกัดของคุณ" hint="เลือกได้มากกว่า 1 ข้อ">
              <OptionChips
                options={RESTRICTION_OPTIONS}
                selected={dietaryRestrictions}
                multiple
                onToggle={(option) =>
                  setDietaryRestrictions((prev) => toggleInList(prev, option, NO_RESTRICTION))
                }
              />
              {dietaryRestrictions.includes(OTHER_OPTION) && (
                <input
                  type="text"
                  value={restrictionOther}
                  onChange={(e) => setRestrictionOther(e.target.value)}
                  placeholder="ระบุข้อจำกัดของคุณ"
                  className="w-full max-w-[358px] h-11 px-4 mt-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands"
                />
              )}
            </StepShell>
          )}

          {step === 4 && (
            <StepShell title="คุณมีอุปกรณ์อะไรบ้าง?" hint="เลือกได้มากกว่า 1 ข้อ">
              <OptionChips
                options={EQUIPMENT_OPTIONS}
                selected={equipment}
                multiple
                onToggle={(option) => setEquipment((prev) => toggleInList(prev, option))}
              />
              {equipment.includes(OTHER_OPTION) && (
                <input
                  type="text"
                  value={equipmentOther}
                  onChange={(e) => setEquipmentOther(e.target.value)}
                  placeholder="ระบุอุปกรณ์ที่มี"
                  className="w-full max-w-[358px] h-11 px-4 mt-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands"
                />
              )}
            </StepShell>
          )}

          {step === 5 && (
            <StepShell title="คุณทำอาหารบ่อยแค่ไหน?">
              <OptionList
                options={FREQUENCY_OPTIONS}
                selected={cookingFrequency}
                multiple={false}
                onToggle={setCookingFrequency}
              />
            </StepShell>
          )}

          {step === 6 && (
            <StepShell title="คุณทำอาหารเพื่ออะไร?" hint="เลือกได้มากกว่า 1 ข้อ">
              <OptionList
                options={GOAL_OPTIONS}
                selected={cookingGoals}
                multiple
                onToggle={(option) =>
                  setCookingGoals((prev) => toggleInList(prev, option))
                }
              />
            </StepShell>
          )}
        </div>

        <div className="w-full px-4 pb-6 flex justify-end bg-background-primary">
          <NextButton onClick={handleNext} />
        </div>
      </div>
    </div>
  );
}

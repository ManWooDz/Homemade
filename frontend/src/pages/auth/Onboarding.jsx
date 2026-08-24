import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import AuthHeader from "../../components/AuthHeader";

const OTHER_OPTION = "อื่น ๆ";
const NO_RESTRICTION = "ไม่มีข้อจำกัด";

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

const MONTHS_TH = [
  "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
  "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
];

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: CURRENT_YEAR - 1940 + 1 }, (_, i) => 1940 + i);

const DEFAULT_YEAR_INDEX = YEARS.indexOf(2000);

const pad2 = (n) => String(n).padStart(2, "0");

const daysInMonth = (year, monthIndex) => new Date(year, monthIndex + 1, 0).getDate();

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

function ProgressDots({ step, total }) {
  return (
    <div className="flex items-center justify-center gap-2 mb-6">
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={`h-2 rounded-full transition-all ${
            i === step - 1
              ? "w-6 bg-[#EF5A3A]"
              : i < step - 1
                ? "w-2 bg-[#EF5A3A]"
                : "w-2 bg-gray-200"
          }`}
        />
      ))}
    </div>
  );
}

function OptionBadges({ options, selected, multiple, onToggle }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const isSelected = multiple
          ? selected.includes(option)
          : selected === option;
        return (
          <button
            key={option}
            type="button"
            onClick={() => onToggle(option)}
            className={`px-4 py-2 rounded-full text-sm font-medium border transition ${
              isSelected
                ? "bg-[#EF5A3A] border-[#EF5A3A] text-white shadow-sm"
                : "bg-white border-gray-400 text-gray-700 hover:border-[#EF5A3A] hover:text-[#EF5A3A]"
            }`}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}

const WHEEL_ITEM_HEIGHT = 40;
const WHEEL_VISIBLE_COUNT = 3;

function WheelColumn({ items, selectedIndex, onChangeIndex }) {
  const containerRef = useRef(null);
  const scrollTimeout = useRef(null);
  const isFirstRender = useRef(true);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const target = selectedIndex * WHEEL_ITEM_HEIGHT;
    if (isFirstRender.current || Math.abs(el.scrollTop - target) > 1) {
      el.scrollTop = target;
    }
    isFirstRender.current = false;
  }, [selectedIndex, items.length]);

  const handleScroll = (e) => {
    const el = e.target;
    clearTimeout(scrollTimeout.current);
    scrollTimeout.current = setTimeout(() => {
      const idx = Math.round(el.scrollTop / WHEEL_ITEM_HEIGHT);
      const clamped = Math.max(0, Math.min(items.length - 1, idx));
      if (clamped !== selectedIndex) onChangeIndex(clamped);
    }, 120);
  };

  const dragState = useRef({ dragging: false, startY: 0, startScroll: 0 });

  const handlePointerDown = (e) => {
    if (e.pointerType !== "mouse") return;
    const el = containerRef.current;
    dragState.current = { dragging: true, startY: e.clientY, startScroll: el.scrollTop };
    el.setPointerCapture(e.pointerId);
    e.preventDefault();
  };

  const handlePointerMove = (e) => {
    if (!dragState.current.dragging) return;
    const el = containerRef.current;
    el.scrollTop = dragState.current.startScroll - (e.clientY - dragState.current.startY);
  };

  const handlePointerUp = (e) => {
    if (!dragState.current.dragging) return;
    dragState.current.dragging = false;
    containerRef.current?.releasePointerCapture(e.pointerId);
    handleScroll({ target: containerRef.current });
  };

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      className="relative z-10 flex-1 overflow-y-scroll snap-y snap-mandatory scrollbar-hide select-none cursor-grab active:cursor-grabbing"
      style={{
        height: WHEEL_ITEM_HEIGHT * WHEEL_VISIBLE_COUNT,
        paddingTop: WHEEL_ITEM_HEIGHT,
        paddingBottom: WHEEL_ITEM_HEIGHT,
      }}
    >
      {items.map((label, i) => (
        <div
          key={i}
          className={`flex items-center justify-center snap-center transition ${
            i === selectedIndex
              ? "text-black font-bold text-lg"
              : "text-gray-400 text-base"
          }`}
          style={{ height: WHEEL_ITEM_HEIGHT }}
        >
          {label}
        </div>
      ))}
    </div>
  );
}

function DateWheel({ dayIndex, monthIndex, yearIndex, onChangeDay, onChangeMonth, onChangeYear }) {
  const days = useMemo(
    () => Array.from({ length: daysInMonth(YEARS[yearIndex], monthIndex) }, (_, i) => i + 1),
    [monthIndex, yearIndex],
  );
  const clampedDayIndex = Math.min(dayIndex, days.length - 1);

  return (
    <div className="relative bg-gray-50 rounded-2xl px-4 flex gap-2">
      <div className="pointer-events-none absolute inset-x-4 top-1/2 -translate-y-1/2 h-10 bg-orange-50 border border-[#EF5A3A]/40 rounded-xl z-0" />
      <WheelColumn items={days} selectedIndex={clampedDayIndex} onChangeIndex={onChangeDay} />
      <WheelColumn items={MONTHS_TH} selectedIndex={monthIndex} onChangeIndex={onChangeMonth} />
      <WheelColumn items={YEARS} selectedIndex={yearIndex} onChangeIndex={onChangeYear} />
    </div>
  );
}

function StepShell({ title, hint, children }) {
  return (
    <div>
      <h2 className="text-xl font-bold text-black text-center mb-1">{title}</h2>
      {hint && <p className="text-sm text-[#EF5A3A] text-center mb-6">{hint}</p>}
      {!hint && <div className="mb-6" />}
      {children}
    </div>
  );
}

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);

  const [dayIndex, setDayIndex] = useState(0);
  const [monthIndex, setMonthIndex] = useState(0);
  const [yearIndex, setYearIndex] = useState(DEFAULT_YEAR_INDEX);

  const [cuisinePreferences, setCuisinePreferences] = useState([]);
  const [dietaryRestrictions, setDietaryRestrictions] = useState([]);
  const [restrictionOther, setRestrictionOther] = useState("");
  const [equipment, setEquipment] = useState([]);
  const [equipmentOther, setEquipmentOther] = useState("");
  const [cookingFrequency, setCookingFrequency] = useState("");
  const [cookingGoals, setCookingGoals] = useState([]);

  const days = useMemo(
    () => Array.from({ length: daysInMonth(YEARS[yearIndex], monthIndex) }, (_, i) => i + 1),
    [monthIndex, yearIndex],
  );

  const birthDate = `${YEARS[yearIndex]}-${pad2(monthIndex + 1)}-${pad2(days[Math.min(dayIndex, days.length - 1)])}`;

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
        birth_date: birthDate,
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
      <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
        <AuthHeader onBack={handleBack} />
        <ProgressDots step={step} total={6} />

        <div className="flex-1 overflow-y-auto px-6 pb-6">
          {step === 1 && (
            <StepShell title="คุณเกิดวันที่เท่าไหร่?">
              <DateWheel
                dayIndex={dayIndex}
                monthIndex={monthIndex}
                yearIndex={yearIndex}
                onChangeDay={setDayIndex}
                onChangeMonth={setMonthIndex}
                onChangeYear={setYearIndex}
              />
            </StepShell>
          )}

          {step === 2 && (
            <StepShell title="คุณชอบอาหารแบบไหน?" hint="(เลือกได้มากกว่า 1 ข้อ)">
              <OptionBadges
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
            <StepShell title="อาหารแพ้ หรือข้อจำกัดของคุณ" hint="(เลือกได้มากกว่า 1 ข้อ)">
              <OptionBadges
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
                  className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm transition-shadow mt-4 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
                />
              )}
            </StepShell>
          )}

          {step === 4 && (
            <StepShell title="คุณมีอุปกรณ์อะไรบ้าง?" hint="(เลือกได้มากกว่า 1 ข้อ)">
              <OptionBadges
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
                  className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm transition-shadow mt-4 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
                />
              )}
            </StepShell>
          )}

          {step === 5 && (
            <StepShell title="คุณทำอาหารบ่อยแค่ไหน?">
              <div className="flex flex-col gap-2">
                {FREQUENCY_OPTIONS.map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setCookingFrequency(option)}
                    className={`w-full text-left px-4 py-3.5 rounded-2xl border transition ${
                      cookingFrequency === option
                        ? "bg-[#EF5A3A] border-[#EF5A3A] text-white font-bold shadow-sm"
                        : "bg-white border-gray-400 text-gray-700 hover:border-[#EF5A3A] hover:text-[#EF5A3A]"
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </StepShell>
          )}

          {step === 6 && (
            <StepShell title="คุณทำอาหารเพื่ออะไร?" hint="(เลือกได้มากกว่า 1 ข้อ)">
              <div className="flex flex-col gap-2">
                {GOAL_OPTIONS.map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setCookingGoals((prev) => toggleInList(prev, option))}
                    className={`w-full text-left px-4 py-3.5 rounded-2xl border transition ${
                      cookingGoals.includes(option)
                        ? "bg-[#EF5A3A] border-[#EF5A3A] text-white font-bold shadow-sm"
                        : "bg-white border-gray-400 text-gray-700 hover:border-[#EF5A3A] hover:text-[#EF5A3A]"
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </StepShell>
          )}
        </div>

        <div className="px-6 pb-8 pt-2 flex gap-3">
          <button
            type="button"
            onClick={handleBack}
            className="flex-1 bg-gray-100 text-gray-700 py-3.5 rounded-full text-base font-bold shadow-sm hover:bg-gray-200 transition"
          >
            ย้อนกลับ
          </button>
          <button
            type="button"
            onClick={handleNext}
            className="flex-1 bg-[#EF5A3A] text-white py-3.5 rounded-full text-base font-bold shadow-md hover:bg-orange-600 transition"
          >
            {step === 6 ? "เสร็จสิ้น" : "ถัดไป"}
          </button>
        </div>
      </div>
    </div>
  );
}

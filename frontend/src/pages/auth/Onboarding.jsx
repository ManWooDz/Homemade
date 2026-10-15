import { useLocale } from "../../context/LocaleContext";
import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import Picker from "react-mobile-picker";
import HeaderLogo from "../../components/HeaderLogo";
import BackButton from "../../components/BackButton";
import { ChevronRight } from "lucide-react";
import { OptionChips, OptionList } from "../../components/OptionPicker";
import {
  OTHER_OPTION,
  NO_RESTRICTION,
  EQUIPMENT_NONE,
  CUISINE_OPTIONS,
  CUISINE_EMOJI,
  RESTRICTION_OPTIONS,
  RESTRICTION_EMOJI,
  EQUIPMENT_OPTIONS,
  EQUIPMENT_EMOJI,
  FREQUENCY_OPTIONS,
  FREQUENCY_EMOJI,
  GOAL_OPTIONS,
  GOAL_EMOJI,
  toggleInList,
} from "../../constants/preferenceOptions";

const AGES = Array.from({ length: 66 }, (_, i) => String(15 + i));
const AGE_ITEM_HEIGHT = 44; // matches the h-11 row rendered for each Picker.Item

function StepCounter({ step, total }) {
  const { t } = useLocale();
  return (
    <div className="text-body-medium text-text-neutral tabular-nums">
      {t("ขั้นตอน {step} จาก {total}", { step, total })}
    </div>
  );
}

function StepShell({ title, hint, error, children }) {
    const { t } = useLocale();
  return (
    <div className="w-full flex flex-col items-center mt-8">
      <h1 id="quiz-title" tabIndex={-1} className="text-h2 font-semibold text-text-black text-center outline-none">
        {title}
      </h1>
      {hint && (
        <p className="text-body-medium text-text-neutral text-center mt-2 mb-6">
          {t(hint)}
        </p>
      )}
      {!hint && <div className="mb-8" />}
      {children}
      {error && <p id="quiz-error" role="alert" className="w-full max-w-[358px] text-body-medium text-red-700 mt-4">{t(error)}</p>}
    </div>
  );
}

export default function Onboarding() {
    const { t } = useLocale();
  const navigate = useNavigate();
  const { apiFetch } = useAuth();
  const [step, setStep] = useState(1);
  const [isSaving, setIsSaving] = useState(false);
  const savePending = useRef(false);
  const contentRef = useRef(null);

  useEffect(() => {
    contentRef.current.scrollTop = 0;
    contentRef.current.querySelector("h1")?.focus({ preventScroll: true });
  }, [step]);

  const [pickerValue, setPickerValue] = useState({ age: "25" });

  const [cuisinePreferences, setCuisinePreferences] = useState([]);
  const [dietaryRestrictions, setDietaryRestrictions] = useState([]);
  const [restrictionOther, setRestrictionOther] = useState("");
  const [equipment, setEquipment] = useState([]);
  const [equipmentOther, setEquipmentOther] = useState("");
  const [cookingFrequency, setCookingFrequency] = useState("");
  const [cookingGoals, setCookingGoals] = useState([]);
  const [stepError, setStepError] = useState("");
  const [restrictionShakeKey, setRestrictionShakeKey] = useState(0);
  const [equipmentShakeKey, setEquipmentShakeKey] = useState(0);

  useEffect(() => {
    if (stepError) contentRef.current.querySelector("#quiz-error")?.scrollIntoView({ block: "nearest" });
  }, [stepError]);

  const SELECT_ONE_ERROR = "กรุณาเลือกอย่างน้อย 1 ตัวเลือก";

  const handleBack = () => {
    if (savePending.current) return;
    setStepError("");
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

  const handleNext = async () => {
    if (savePending.current) return;
    setStepError("");
    if (step === 2 && cuisinePreferences.length === 0) {
      setStepError(SELECT_ONE_ERROR);
      return;
    }
    if (step === 3) {
      if (dietaryRestrictions.length === 0) {
        setStepError(SELECT_ONE_ERROR);
        return;
      }
      if (dietaryRestrictions.includes(OTHER_OPTION) && !restrictionOther.trim()) {
        setStepError("กรุณาระบุข้อจำกัดของคุณ");
        setRestrictionShakeKey((k) => k + 1);
        return;
      }
    }
    if (step === 4) {
      if (equipment.length === 0) {
        setStepError(SELECT_ONE_ERROR);
        return;
      }
      if (equipment.includes(OTHER_OPTION) && !equipmentOther.trim()) {
        setStepError("กรุณาระบุอุปกรณ์ที่มีก่อนไปต่อ");
        setEquipmentShakeKey((k) => k + 1);
        return;
      }
    }
    if (step === 5 && !cookingFrequency) {
      setStepError(SELECT_ONE_ERROR);
      return;
    }
    if (step === 6 && cookingGoals.length === 0) {
      setStepError(SELECT_ONE_ERROR);
      return;
    }

    if (step === 6) {
      savePending.current = true;
      setIsSaving(true);
      const payload = {
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
      };
      try {
        const res = await apiFetch("/api/user-preferences", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          setStepError("บันทึกคำตอบไม่สำเร็จ คำตอบยังอยู่ กรุณาลองอีกครั้ง");
          return;
        }
        navigate("/home", { replace: true });
      } catch (err) {
        console.error("[onboarding] failed to save preferences:", err);
        setStepError("บันทึกคำตอบไม่สำเร็จ คำตอบยังอยู่ กรุณาลองอีกครั้ง");
      } finally {
        savePending.current = false;
        setIsSaving(false);
      }
      return;
    }
    setStep((s) => s + 1);
  };

  // react-mobile-picker only handles touch drags and desktop wheel scroll (wheelMode),
  // it has no mouse click-drag support — add a minimal mouse-drag layer on top of it.
  const ageDrag = useRef({ dragging: false, startY: 0, startIndex: 0 });

  const handleAgePointerDown = (e) => {
    if (e.pointerType !== "mouse") return;
    ageDrag.current = {
      dragging: true,
      startY: e.clientY,
      startIndex: AGES.indexOf(pickerValue.age),
    };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handleAgePointerMove = (e) => {
    if (!ageDrag.current.dragging) return;
    const deltaY = e.clientY - ageDrag.current.startY;
    const stepsMoved = Math.round(-deltaY / AGE_ITEM_HEIGHT);
    const newIndex = Math.min(
      AGES.length - 1,
      Math.max(0, ageDrag.current.startIndex + stepsMoved),
    );
    const newAge = AGES[newIndex];
    if (newAge !== pickerValue.age) setPickerValue({ age: newAge });
  };

  const handleAgePointerUp = () => {
    ageDrag.current.dragging = false;
  };

  return (
    <div className="auth-screen h-dvh bg-gray-100 flex justify-center font-sans overflow-hidden">
      <div className="w-full max-w-107.5 bg-white h-full relative shadow-2xl overflow-hidden flex flex-col">
        <main ref={contentRef} className="w-full flex-1 min-h-0 px-6 pt-6 pb-6 bg-background-primary flex flex-col items-center overflow-y-auto">
          <div className="w-full flex flex-col items-center">
            <HeaderLogo />
            <div className="w-full flex justify-between items-center mt-4">
              <BackButton onClick={handleBack} disabled={isSaving} to="/login" size="w-11 h-11" />
              <StepCounter step={step} total={6} />
            </div>
            <div role="progressbar" aria-label={t("ความคืบหน้า")} aria-valuemin={1} aria-valuemax={6} aria-valuenow={step} className="w-full flex gap-2 mt-4">
              {Array.from({ length: 6 }, (_, index) => <span key={index} className={`h-1 flex-1 rounded-full ${index < step ? "bg-button-primary" : "bg-gray-200"}`} />)}
            </div>
          </div>
          <fieldset disabled={isSaving} aria-labelledby="quiz-title" aria-describedby={stepError ? "quiz-error" : undefined} className="w-full min-w-0">

          {step === 1 && (
            <StepShell title={t("คุณอายุเท่าไหร่?")} hint="เลื่อนเพื่อเลือกอายุ หรือใช้ปุ่มลูกศรขึ้นและลง">
              <div
                role="spinbutton"
                tabIndex={0}
                aria-label={t("อายุ")}
                aria-valuemin={15}
                aria-valuemax={80}
                aria-valuenow={Number(pickerValue.age)}
                aria-valuetext={`${pickerValue.age} ${t("ปี")}`}
                onKeyDown={(event) => {
                  if (!["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
                  event.preventDefault();
                  const age = Number(pickerValue.age);
                  setPickerValue({ age: String(event.key === "Home" ? 15 : event.key === "End" ? 80 : Math.min(80, Math.max(15, age + (event.key === "ArrowUp" ? 1 : -1)))) });
                }}
                className="w-full max-w-[200px] custom-picker-container cursor-grab active:cursor-grabbing select-none"
                onPointerDown={handleAgePointerDown}
                onPointerMove={handleAgePointerMove}
                onPointerUp={handleAgePointerUp}
                onPointerCancel={handleAgePointerUp}
              >
                <Picker
                  value={pickerValue}
                  onChange={setPickerValue}
                  wheelMode="normal"
                  itemHeight={AGE_ITEM_HEIGHT}
                >
                  <Picker.Column name="age" className="w-full">
                    {AGES.map((age) => (
                      <Picker.Item key={age} value={age}>
                        {({ selected }) => (
                          <div
                            className={`h-11 px-8 flex justify-center items-center rounded-xl text-body-large font-semibold transition-all ${
                              selected
                                ? "bg-button-primary text-text-white"
                                : "text-text-neutral"
                            }`}
                          >
                            {age} {t("ปี")}</div>
                        )}
                      </Picker.Item>
                    ))}
                  </Picker.Column>
                </Picker>
              </div>
            </StepShell>
          )}

          {step === 2 && (
            <StepShell title={t("คุณชอบอาหารแบบไหน?")} hint="เลือกได้มากกว่า 1 ข้อ" error={stepError}>
              <OptionChips
                options={CUISINE_OPTIONS}
                selected={cuisinePreferences}
                multiple
                emojiMap={CUISINE_EMOJI}
                onToggle={(option) =>
                  setCuisinePreferences((prev) => {
                    const next = toggleInList(prev, option);
                    if (next.length > 0) setStepError("");
                    return next;
                  })
                }
              />
            </StepShell>
          )}

          {step === 3 && (
            <StepShell title={t("อาการแพ้ หรือข้อจำกัดของคุณ")} hint="เลือกได้มากกว่า 1 ข้อ" error={stepError}>
              <OptionChips
                options={RESTRICTION_OPTIONS}
                selected={dietaryRestrictions}
                multiple
                emojiMap={RESTRICTION_EMOJI}
                onToggle={(option) =>
                  setDietaryRestrictions((prev) => {
                    const next = toggleInList(prev, option, NO_RESTRICTION);
                    if (next.length > 0 && (!next.includes(OTHER_OPTION) || restrictionOther.trim())) {
                      setStepError("");
                    }
                    return next;
                  })
                }
              />
              {dietaryRestrictions.includes(OTHER_OPTION) && (
                <input
                  aria-label={t("ระบุข้อจำกัดของคุณ")}
                  aria-invalid={!restrictionOther.trim() && Boolean(stepError)}
                  aria-describedby={stepError ? "quiz-error" : undefined}
                  key={`restriction-other-${restrictionShakeKey}`}
                  type="text"
                  value={restrictionOther}
                  onChange={(e) => {
                    setRestrictionOther(e.target.value);
                    if (e.target.value.trim()) setStepError("");
                  }}
                  placeholder={t("ระบุข้อจำกัดของคุณ")}
                  className={`w-full max-w-[358px] h-11 px-4 mt-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands ${
                    !restrictionOther.trim() && stepError ? "animate-shake border-red-400" : ""
                  }`}
                />
              )}
            </StepShell>
          )}

          {step === 4 && (
            <StepShell title={t("คุณมีอุปกรณ์อะไรบ้าง?")} hint="เลือกได้มากกว่า 1 ข้อ" error={stepError}>
              <OptionChips
                options={EQUIPMENT_OPTIONS}
                selected={equipment}
                multiple
                emojiMap={EQUIPMENT_EMOJI}
                onToggle={(option) =>
                  setEquipment((prev) => {
                    const next = toggleInList(prev, option, EQUIPMENT_NONE);
                    if (next.length > 0 && (!next.includes(OTHER_OPTION) || equipmentOther.trim())) {
                      setStepError("");
                    }
                    return next;
                  })
                }
              />
              {equipment.includes(OTHER_OPTION) && (
                <input
                  aria-label={t("ระบุอุปกรณ์ที่มี")}
                  aria-invalid={!equipmentOther.trim() && Boolean(stepError)}
                  aria-describedby={stepError ? "quiz-error" : undefined}
                  key={`equipment-other-${equipmentShakeKey}`}
                  type="text"
                  value={equipmentOther}
                  onChange={(e) => {
                    setEquipmentOther(e.target.value);
                    if (e.target.value.trim()) setStepError("");
                  }}
                  placeholder={t("ระบุอุปกรณ์ที่มี")}
                  className={`w-full max-w-[358px] h-11 px-4 mt-4 bg-background-primary rounded-full border border-stroke-text-field text-body-large text-text-black placeholder:text-text-neutral focus:outline-none focus:border-stroke-brands ${
                    !equipmentOther.trim() && stepError ? "animate-shake border-red-400" : ""
                  }`}
                />
              )}
            </StepShell>
          )}

          {step === 5 && (
            <StepShell title={t("คุณทำอาหารบ่อยแค่ไหน?")} hint="เลือก 1 ข้อ" error={stepError}>
              <OptionList
                options={FREQUENCY_OPTIONS}
                selected={cookingFrequency}
                multiple={false}
                emojiMap={FREQUENCY_EMOJI}
                onToggle={(option) => {
                  setCookingFrequency(option);
                  setStepError("");
                }}
              />
            </StepShell>
          )}

          {step === 6 && (
            <StepShell title={t("คุณทำอาหารเพื่ออะไร?")} hint="เลือกได้มากกว่า 1 ข้อ" error={stepError}>
              <OptionList
                options={GOAL_OPTIONS}
                selected={cookingGoals}
                multiple
                emojiMap={GOAL_EMOJI}
                onToggle={(option) =>
                  setCookingGoals((prev) => {
                    const next = toggleInList(prev, option);
                    if (next.length > 0) setStepError("");
                    return next;
                  })
                }
              />
            </StepShell>
          )}
          </fieldset>
        </main>

        <div className="auth-footer w-full shrink-0 px-6 pt-4 border-t border-gray-100 bg-background-primary">
          <button type="button" onClick={handleNext} disabled={isSaving} aria-busy={isSaving} className="w-full min-h-11 px-5 py-2 bg-button-primary text-text-white rounded-full flex items-center justify-center gap-2 text-body-medium font-semibold hover:opacity-95 disabled:opacity-50 transition-colors cursor-pointer">
            {isSaving ? t("กำลังบันทึก...") : step === 6 ? t("บันทึกและเริ่มใช้งาน") : t("Next")}
            {!isSaving && <ChevronRight aria-hidden="true" className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </div>
  );
}

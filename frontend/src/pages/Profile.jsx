import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  History,
  Globe,
  SlidersHorizontal,
  HelpCircle,
  LogOut,
  Mail,
  ChefHat,
} from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import { OptionChips, OptionList } from "../components/OptionPicker";
import { getTagColor } from "../utils/tagColors";
import { useAuth } from "../context/AuthContext";
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
} from "../constants/preferenceOptions";

const LANGUAGE_OPTIONS = [
  { code: "th", label: "ไทย" },
  { code: "en", label: "English" },
];

const PLACEHOLDER_USER = {
  username: "ผู้ใช้ HomeMade",
  email: "user@example.com",
  avatar:
    "https://images.unsplash.com/photo-1633332755192-727a05c4013d?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80",
};

function Header({ title, onBack }) {
  return (
    <div className="pt-8 px-6 h-18 flex items-center justify-center relative z-20 mb-6">
      <button
        onClick={onBack}
        className="absolute left-6 w-10 h-10 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md"
      >
        <ChevronLeft className="w-6 h-6" />
      </button>
      {title ? (
        <h2 className="text-lg font-bold text-black">{title}</h2>
      ) : (
        <img src={logo} alt="HomeMade" className="h-18 object-contain" />
      )}
    </div>
  );
}

function FlagIcon({ code }) {
  if (code === "th") {
    return (
      <svg viewBox="0 0 30 20" className="w-5 h-3.5 rounded-sm overflow-hidden shrink-0">
        <rect width="30" height="20" fill="#A51931" />
        <rect y="3.33" width="30" height="13.33" fill="#F4F5F8" />
        <rect y="6.67" width="30" height="6.67" fill="#2D2A4A" />
      </svg>
    );
  }
  if (code === "en") {
    const stripeHeight = 20 / 13;
    return (
      <svg viewBox="0 0 30 20" className="w-5 h-3.5 rounded-sm overflow-hidden shrink-0">
        <rect width="30" height="20" fill="#B22234" />
        {Array.from({ length: 6 }).map((_, i) => (
          <rect
            key={i}
            y={(i * 2 + 1) * stripeHeight}
            width="30"
            height={stripeHeight}
            fill="#fff"
          />
        ))}
        <rect width="12" height={(7 * 20) / 13} fill="#3C3B6E" />
      </svg>
    );
  }
  return null;
}

function MenuRow({ icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full bg-gray-50 hover:bg-gray-100 rounded-2xl px-4 py-3.5 flex items-center gap-3 transition"
    >
      <div className="w-9 h-9 rounded-full bg-white shadow-sm flex items-center justify-center text-[#EF5A3A] shrink-0">
        {icon}
      </div>
      <span className="flex-1 text-left text-[15px] font-medium text-gray-800">
        {label}
      </span>
      <ChevronRight className="w-5 h-5 text-gray-300" />
    </button>
  );
}

export default function Profile({
  cookingHistory,
  activeTab,
  setActiveTab,
  onBack,
}) {
  const [view, setView] = useState("main"); // main | history | language | preferences | helps

  const [language, setLanguage] = useState("th");

  const goMain = () => setView("main");

  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { apiFetch } = useAuth();

  const [prefsLoaded, setPrefsLoaded] = useState(false);
  const [age, setAge] = useState("");
  const [cuisinePreferences, setCuisinePreferences] = useState([]);
  const [dietaryRestrictions, setDietaryRestrictions] = useState([]);
  const [restrictionOther, setRestrictionOther] = useState("");
  const [equipment, setEquipment] = useState([]);
  const [equipmentOther, setEquipmentOther] = useState("");
  const [cookingFrequency, setCookingFrequency] = useState("");
  const [cookingGoals, setCookingGoals] = useState([]);
  const [prefsError, setPrefsError] = useState("");

  useEffect(() => {
    if (view !== "preferences" || prefsLoaded) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch("/api/user-preferences");
        if (cancelled || !res.ok) return;
        const payload = await res.json();
        if (payload.data) {
          setAge(payload.data.age != null ? String(payload.data.age) : "");
          setCuisinePreferences(payload.data.cuisine_preferences || []);
          setDietaryRestrictions(payload.data.dietary_restrictions || []);
          setEquipment(payload.data.equipment || []);
          setCookingFrequency(payload.data.cooking_frequency || "");
          setCookingGoals(payload.data.cooking_goals || []);
        }
      } finally {
        if (!cancelled) setPrefsLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [view, prefsLoaded, apiFetch]);

  // Auto-save on every change. `overrides` carries the field that just
  // changed — React state setters are async, so reading e.g.
  // `cuisinePreferences` here right after calling its setter would still
  // see the stale pre-toggle value; the caller passes the freshly computed
  // next value explicitly instead.
  const savePreferences = async (overrides) => {
    const body = {
      age: age === "" ? null : Number(age),
      cuisine_preferences: cuisinePreferences,
      dietary_restrictions: dietaryRestrictions,
      equipment: equipment,
      cooking_frequency: cookingFrequency || null,
      cooking_goals: cookingGoals,
      ...overrides,
    };
    try {
      const res = await apiFetch("/api/user-preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setPrefsError(res.ok ? "" : "บันทึกไม่สำเร็จ กรุณาลองอีกครั้ง");
    } catch {
      setPrefsError("บันทึกไม่สำเร็จ กรุณาลองอีกครั้ง");
    }
  };

  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  const handleLogout = async () => {
    if (isLoggingOut) return;
    setIsLoggingOut(true);
    const result = await logout();
    setIsLoggingOut(false);
    if (result.success) {
      navigate("/login", { replace: true });
    } else {
      setLogoutError(result.error);
    }
  };

  if (view === "history") {
    return (
      <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
        <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
          <Header title="Cooking History" onBack={goMain} />
          <div className="flex-1 overflow-y-auto px-5 pb-32">
            {!cookingHistory || cookingHistory.length === 0 ? (
              <div className="text-center text-gray-400 mt-10">
                <ChefHat className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                <p>ยังไม่มีเมนูที่เคยสร้าง</p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {cookingHistory.map((item) => (
                  <div
                    key={item.id}
                    className="bg-gray-50 rounded-2xl p-3 flex items-center gap-3 shadow-sm"
                  >
                    <div className="w-16 h-16 rounded-full overflow-hidden bg-white shrink-0">
                      <img
                        src={
                          item.image ||
                          "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80"
                        }
                        alt={item.recipe_name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-bold text-gray-800 truncate">
                        {item.recipe_name}
                      </h4>
                      {item.diet_tags && item.diet_tags.length > 0 && (
                        <div className="flex gap-2 mt-1">
                          {item.diet_tags.slice(0, 2).map((tag, idx) => (
                            <span
                              key={idx}
                              className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${getTagColor(tag)}`}
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>
      </div>
    );
  }

  if (view === "language") {
    return (
      <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
        <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
          <Header title="Language" onBack={goMain} />
          <div className="flex-1 overflow-y-auto px-5 pb-32">
            <div className="flex flex-col gap-2">
              {LANGUAGE_OPTIONS.map((opt) => (
                <button
                  key={opt.code}
                  onClick={() => setLanguage(opt.code)}
                  className={`w-full flex items-center justify-between px-4 py-3.5 rounded-2xl border transition ${
                    language === opt.code
                      ? "bg-orange-50 border-[#EF5A3A]"
                      : "bg-gray-50 border-transparent hover:border-gray-200"
                  }`}
                >
                  <span className="text-[15px] font-medium text-gray-800 flex items-center gap-2">
                    <FlagIcon code={opt.code} />
                    {opt.label}
                  </span>
                  <span
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition ${
                      language === opt.code
                        ? "border-[#EF5A3A]"
                        : "border-gray-300"
                    }`}
                  >
                    {language === opt.code && (
                      <span className="w-2.5 h-2.5 rounded-full bg-[#EF5A3A]" />
                    )}
                  </span>
                </button>
              ))}
            </div>
          </div>
          <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>
      </div>
    );
  }

  if (view === "preferences") {
    return (
      <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
        <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
          <Header title="Preferences" onBack={goMain} />
          <div className="flex-1 overflow-y-auto px-5 pb-32">
            <h3 className="text-base font-bold text-black mb-2">อายุ</h3>
            <input
              type="number"
              min="1"
              max="120"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              onBlur={() => savePreferences({ age: age === "" ? null : Number(age) })}
              placeholder="ระบุอายุ"
              className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm mb-6 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
            />

            <h3 className="text-base font-bold text-black mb-2">คุณชอบอาหารแบบไหน?</h3>
            <div className="mb-6">
              <OptionChips
                options={CUISINE_OPTIONS}
                selected={cuisinePreferences}
                multiple
                emojiMap={CUISINE_EMOJI}
                onToggle={(option) => {
                  const next = toggleInList(cuisinePreferences, option);
                  setCuisinePreferences(next);
                  savePreferences({ cuisine_preferences: next });
                }}
              />
            </div>

            <h3 className="text-base font-bold text-black mb-2">อาการแพ้ หรือข้อจำกัดของคุณ</h3>
            <div className="mb-2">
              <OptionChips
                options={RESTRICTION_OPTIONS}
                selected={dietaryRestrictions}
                multiple
                emojiMap={RESTRICTION_EMOJI}
                onToggle={(option) => {
                  const next = toggleInList(dietaryRestrictions, option, NO_RESTRICTION);
                  setDietaryRestrictions(next);
                  savePreferences({ dietary_restrictions: next });
                }}
              />
            </div>
            {dietaryRestrictions.includes(OTHER_OPTION) && (
              <input
                type="text"
                value={restrictionOther}
                onChange={(e) => setRestrictionOther(e.target.value)}
                onBlur={() =>
                  savePreferences({
                    dietary_restrictions: [
                      ...dietaryRestrictions.filter((r) => r !== OTHER_OPTION),
                      restrictionOther || OTHER_OPTION,
                    ],
                  })
                }
                placeholder="ระบุข้อจำกัดของคุณ"
                className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm mb-4 mt-2 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
              />
            )}
            <div className="mb-4" />

            <h3 className="text-base font-bold text-black mb-2">อุปกรณ์ที่มี</h3>
            <div className="mb-2">
              <OptionChips
                options={EQUIPMENT_OPTIONS}
                selected={equipment}
                multiple
                emojiMap={EQUIPMENT_EMOJI}
                onToggle={(option) => {
                  const next = toggleInList(equipment, option, EQUIPMENT_NONE);
                  setEquipment(next);
                  savePreferences({ equipment: next });
                }}
              />
            </div>
            {equipment.includes(OTHER_OPTION) && (
              <input
                type="text"
                value={equipmentOther}
                onChange={(e) => setEquipmentOther(e.target.value)}
                onBlur={() =>
                  savePreferences({
                    equipment: [
                      ...equipment.filter((e) => e !== OTHER_OPTION),
                      equipmentOther || OTHER_OPTION,
                    ],
                  })
                }
                placeholder="ระบุอุปกรณ์ที่มี"
                className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm mb-4 mt-2 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
              />
            )}
            <div className="mb-4" />

            <h3 className="text-base font-bold text-black mb-2">คุณทำอาหารบ่อยแค่ไหน?</h3>
            <div className="mb-6">
              <OptionList
                options={FREQUENCY_OPTIONS}
                selected={cookingFrequency}
                multiple={false}
                emojiMap={FREQUENCY_EMOJI}
                onToggle={(option) => {
                  setCookingFrequency(option);
                  savePreferences({ cooking_frequency: option });
                }}
              />
            </div>

            <h3 className="text-base font-bold text-black mb-2">คุณทำอาหารเพื่ออะไร?</h3>
            <div className="mb-2">
              <OptionList
                options={GOAL_OPTIONS}
                selected={cookingGoals}
                multiple
                emojiMap={GOAL_EMOJI}
                onToggle={(option) => {
                  const next = toggleInList(cookingGoals, option);
                  setCookingGoals(next);
                  savePreferences({ cooking_goals: next });
                }}
              />
            </div>

            {prefsError && (
              <p className="text-red-600 text-sm text-center mt-4">{prefsError}</p>
            )}
          </div>
          <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>
      </div>
    );
  }

  if (view === "helps") {
    return (
      <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
        <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
          <Header title="Helps" onBack={goMain} />
          <div className="flex-1 overflow-y-auto px-5 pb-32 flex flex-col gap-5">
            <div>
              <h3 className="text-base font-bold text-black mb-2">
                วิธีใช้งาน
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                เพิ่มวัตถุดิบใน My Fridge หรือเลือกเมนูจากหน้าแรก
                แล้วกด "สร้างเมนูอาหารกันเลย" เพื่อให้ AI คิดสูตรอาหารจากวัตถุดิบที่มี
              </p>
            </div>
            <div>
              <h3 className="text-base font-bold text-black mb-2">Tips</h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                ระบุอาการแพ้อาหารและอุปกรณ์ที่มีให้ครบ เพื่อให้สูตรอาหารที่ได้ปลอดภัยและทำได้จริง
              </p>
            </div>
            <div>
              <h3 className="text-base font-bold text-black mb-2">
                ข้อกำหนดการใช้งาน (TOS)
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                สูตรอาหารและข้อมูลโภชนาการที่สร้างโดย AI เป็นการคาดการณ์เพื่อการอ้างอิงเท่านั้น
                โปรดตรวจสอบวัตถุดิบและปริมาณจริงก่อนรับประทาน โดยเฉพาะผู้ที่มีอาการแพ้อาหาร
              </p>
            </div>
          </div>
          <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
      <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
        <Header onBack={onBack} />

        <div className="flex-1 overflow-y-auto px-5 pb-32">
          {/* Profile Card */}
          <div className="bg-gray-100 rounded-3xl p-4 flex items-center gap-4 mb-8">
            <div className="w-20 h-20 rounded-full overflow-hidden shadow-sm shrink-0 bg-white">
              <img
                src={PLACEHOLDER_USER.avatar}
                alt={PLACEHOLDER_USER.username}
                className="w-full h-full object-cover"
              />
            </div>
            <div className="flex flex-col flex-1 min-w-0">
              <h3 className="text-lg font-bold text-black truncate">
                {PLACEHOLDER_USER.username}
              </h3>
              <div className="flex items-center gap-1.5 text-gray-500 text-sm truncate">
                <Mail className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">{user?.email ?? PLACEHOLDER_USER.email}</span>
              </div>
            </div>
          </div>

          {/* Menu */}
          <div className="flex flex-col gap-2 mb-6">
            <MenuRow
              icon={<History className="w-4.5 h-4.5" />}
              label="Cooking History"
              onClick={() => setView("history")}
            />
          </div>

          <h3 className="text-sm font-bold text-gray-400 mb-2 px-1">
            Setting
          </h3>
          <div className="flex flex-col gap-2 mb-8">
            <MenuRow
              icon={<Globe className="w-4.5 h-4.5" />}
              label="Language"
              onClick={() => setView("language")}
            />
            <MenuRow
              icon={<SlidersHorizontal className="w-4.5 h-4.5" />}
              label="Preferences"
              onClick={() => setView("preferences")}
            />
            <MenuRow
              icon={<HelpCircle className="w-4.5 h-4.5" />}
              label="Helps"
              onClick={() => setView("helps")}
            />
          </div>

          {/* Logout */}
          {logoutError && (
            <p className="text-red-600 text-sm text-center mb-2">{logoutError}</p>
          )}
          <button
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="w-full bg-red-500 text-white py-3.5 rounded-full text-base font-bold shadow-md flex items-center justify-center gap-2 hover:bg-red-600 transition disabled:opacity-60"
          >
            <LogOut className="w-5 h-5" />
            {isLoggingOut ? "กำลังออกจากระบบ..." : "ออกจากระบบ"}
          </button>
        </div>

        <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
    </div>
  );
}

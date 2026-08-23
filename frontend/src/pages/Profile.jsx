import { useState } from "react";
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
import { getTagColor } from "../utils/tagColors";
import { useAuth } from "../context/AuthContext";

const OTHER_OPTION = "อื่นๆ";

const TASTE_OPTIONS = [
  "ไม่ระบุ",
  "เผ็ดน้อย",
  "เผ็ดปานกลาง",
  "เผ็ดมาก",
  "รสจัดจ้าน",
  "รสหวานนำ",
  "รสเปรี้ยวนำ",
  "รสกลมกล่อม ไม่จัดจ้าน",
  OTHER_OPTION,
];
const ALLERGY_NONE = "ไม่มี";
const ALLERGY_OPTIONS = [
  ALLERGY_NONE,
  "กุ้ง/อาหารทะเล",
  "ถั่ว",
  "นม/ผลิตภัณฑ์จากนม",
  "ไข่",
  "แป้งสาลี/กลูเตน",
  "ถั่วเหลือง",
  "งา",
  OTHER_OPTION,
];
const EQUIPMENT_NONE = "ไม่มีอุปกรณ์พิเศษ";
const EQUIPMENT_OPTIONS = [
  EQUIPMENT_NONE,
  "ไมโครเวฟ",
  "หม้อทอดไร้น้ำมัน",
  "เตาอบ",
  "หม้อหุงข้าว",
  "กระทะ/เตาแก๊สทั่วไป",
  "หม้อตุ๋น/สโลว์คุก",
  "เครื่องปั่น",
  OTHER_OPTION,
];

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

function PillGroup({ title, hint, options, selected, onToggle }) {
  return (
    <div className="mb-6">
      <h3 className="text-base font-bold text-black mb-2 flex items-baseline gap-2">
        {title}
        {hint && (
          <span className="text-xs font-normal text-gray-400">{hint}</span>
        )}
      </h3>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const isSelected = Array.isArray(selected)
            ? selected.includes(option)
            : selected === option;
          return (
            <button
              key={option}
              type="button"
              onClick={() => onToggle(option)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium border transition ${
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
    </div>
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

  const [taste, setTaste] = useState("");
  const [tasteOther, setTasteOther] = useState("");
  const [allergies, setAllergies] = useState([]);
  const [allergiesOther, setAllergiesOther] = useState("");
  const [equipment, setEquipment] = useState([]);
  const [equipmentOther, setEquipmentOther] = useState("");

  const toggleInList = (list, setList, option, noneValue) => {
    if (option === noneValue) {
      setList(list.includes(noneValue) ? [] : [noneValue]);
      return;
    }
    if (list.includes(option)) {
      setList(list.filter((item) => item !== option));
    } else {
      setList([...list.filter((item) => item !== noneValue), option]);
    }
  };

  const goMain = () => setView("main");

  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
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
            <PillGroup
              title="รสชาติ"
              options={TASTE_OPTIONS}
              selected={taste}
              onToggle={(option) => setTaste(option)}
            />
            {taste === OTHER_OPTION && (
              <input
                type="text"
                value={tasteOther}
                onChange={(e) => setTasteOther(e.target.value)}
                placeholder="ระบุรสชาติที่ต้องการ"
                className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm transition-shadow mb-4 -mt-4 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
              />
            )}

            <PillGroup
              title="อาการแพ้อาหาร"
              hint="เลือกได้มากกว่า 1 ข้อ"
              options={ALLERGY_OPTIONS}
              selected={allergies}
              onToggle={(option) =>
                toggleInList(allergies, setAllergies, option, ALLERGY_NONE)
              }
            />
            {allergies.includes(OTHER_OPTION) && (
              <input
                type="text"
                value={allergiesOther}
                onChange={(e) => setAllergiesOther(e.target.value)}
                placeholder="ระบุอาการแพ้อาหาร"
                className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm transition-shadow mb-4 -mt-4 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
              />
            )}

            <PillGroup
              title="อุปกรณ์ที่มี"
              hint="เลือกได้มากกว่า 1 ข้อ"
              options={EQUIPMENT_OPTIONS}
              selected={equipment}
              onToggle={(option) =>
                toggleInList(equipment, setEquipment, option, EQUIPMENT_NONE)
              }
            />
            {equipment.includes(OTHER_OPTION) && (
              <input
                type="text"
                value={equipmentOther}
                onChange={(e) => setEquipmentOther(e.target.value)}
                placeholder="ระบุอุปกรณ์ที่มี"
                className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm transition-shadow mb-4 -mt-4 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
              />
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
          <button
            onClick={handleLogout}
            className="w-full bg-red-500 text-white py-3.5 rounded-full text-base font-bold shadow-md flex items-center justify-center gap-2 hover:bg-red-600 transition"
          >
            <LogOut className="w-5 h-5" />
            ออกจากระบบ
          </button>
        </div>

        <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
    </div>
  );
}

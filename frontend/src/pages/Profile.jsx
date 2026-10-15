import { useEffect, useRef, useState } from "react";
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
  Star,
  Heart,
  UserRound,
} from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import NotificationBell from "../components/NotificationBell";
import BottomMenu from "../components/bottomMenu";
import { OptionChips, OptionList } from "../components/OptionPicker";
import { getTagColor } from "../utils/tagColors";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../context/LocaleContext";
import ProfileEditor from "../components/ProfileEditor";
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

function Header({ title, onBack, notificationCount, onNotifications }) {
  const { t } = useLocale();
  return (
    <div className="pt-8 px-6 h-18 flex items-center justify-center relative z-20 mb-6">
      <button
        onClick={onBack}
        aria-label={t("กลับ")}
        className="absolute left-6 w-11 h-11 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]"
      >
        <ChevronLeft className="w-6 h-6" />
      </button>
      {title ? (
        <h2 className="text-lg font-bold text-black">{title}</h2>
      ) : (
        <img src={logo} alt="HomeMade" className="h-18 object-contain" />
      )}
      {onNotifications && <div className="absolute right-6 top-1/2 translate-y-4"><NotificationBell count={notificationCount} onClick={onNotifications} /></div>}
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
    const { t } = useLocale();
  return (
    <button
      onClick={onClick}
      className="w-full bg-gray-50 hover:bg-gray-100 rounded-2xl px-4 py-3.5 flex items-center gap-3 transition"
    >
      <div className="w-9 h-9 rounded-full bg-white shadow-sm flex items-center justify-center text-[#EF5A3A] shrink-0">
        {icon}
      </div>
      <span className="flex-1 text-left text-[15px] font-medium text-gray-800">
        {t(label)}
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
  onOpenHistoryItem,
  notificationCount, onNotifications, onNotificationPause,
}) {
  const [view, setView] = useState("main"); // main | history | language | preferences | helps
  useEffect(() => { onNotificationPause?.(view !== "main"); return () => onNotificationPause?.(false); }, [view, onNotificationPause]);
  const [historyFilter, setHistoryFilter] = useState("all"); // all | favorites

  const { locale: language, t } = useLocale();
  const [languageSaving, setLanguageSaving] = useState(false);
  const [languageError, setLanguageError] = useState("");
  const languageRequest = useRef(false);
  const [notice, setNotice] = useState("");
  const [photo, setPhoto] = useState(null);
  const [photoError, setPhotoError] = useState(false);
  const [photoReload, setPhotoReload] = useState(0);

  const goMain = () => setView("main");

  const navigate = useNavigate();
  const { user, logout, updateLanguage } = useAuth();
  const { apiFetch } = useAuth();
  const avatarUrl = user?.has_avatar && photo?.owner === user.id ? photo.url : "";

  useEffect(() => {
    if (!user?.has_avatar) return;
    const controller = new AbortController();
    let createdUrl;
    (async () => {
      try {
        const response = await apiFetch("/api/user-profile/avatar", { signal: controller.signal });
        if (!response.ok) throw new Error("Avatar unavailable");
        const blob = await response.blob();
        if (controller.signal.aborted) return;
        createdUrl = URL.createObjectURL(blob);
        setPhoto({ owner: user.id, url: createdUrl });
        setPhotoError(false);
      } catch {
        if (!controller.signal.aborted) setPhotoError(true);
      }
    })();
    return () => { controller.abort(); if (createdUrl) URL.revokeObjectURL(createdUrl); };
  }, [apiFetch, user?.id, user?.has_avatar, photoReload]);

  const changeLanguage = async code => {
    if (languageRequest.current || code === language) return;
    languageRequest.current = true;
    setLanguageSaving(true);
    setLanguageError("");
    const result = await updateLanguage(code);
    setLanguageSaving(false);
    languageRequest.current = false;
    if (!result.success) setLanguageError("บันทึกภาษาไม่สำเร็จ กรุณาลองอีกครั้ง");
  };

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
        if (cancelled) return;
        if (!res.ok) {
          setPrefsError("โหลดข้อมูลไม่สำเร็จ กรุณาลองใหม่");
          return;
        }
        const payload = await res.json();
        if (payload.data) {
          setAge(payload.data.age != null ? String(payload.data.age) : "");
          setCuisinePreferences(payload.data.cuisine_preferences || []);
          const rawRestrictions = payload.data.dietary_restrictions || [];
          const customRestriction = rawRestrictions.find((r) => !RESTRICTION_OPTIONS.includes(r));
          setDietaryRestrictions(
            customRestriction
              ? [...rawRestrictions.filter((r) => RESTRICTION_OPTIONS.includes(r)), OTHER_OPTION]
              : rawRestrictions,
          );
          setRestrictionOther(customRestriction || "");
          const rawEquipment = payload.data.equipment || [];
          const customEquipment = rawEquipment.find((e) => !EQUIPMENT_OPTIONS.includes(e));
          setEquipment(
            customEquipment
              ? [...rawEquipment.filter((e) => EQUIPMENT_OPTIONS.includes(e)), OTHER_OPTION]
              : rawEquipment,
          );
          setEquipmentOther(customEquipment || "");
          setCookingFrequency(payload.data.cooking_frequency || "");
          setCookingGoals(payload.data.cooking_goals || []);
        }
        setPrefsLoaded(true);
      } catch {
        if (!cancelled) setPrefsError("โหลดข้อมูลไม่สำเร็จ กรุณาลองใหม่");
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
    if (!prefsLoaded) return;
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

  const visibleHistory =
    historyFilter === "favorites"
      ? (cookingHistory || []).filter((item) => item.is_favorite)
      : cookingHistory || [];

  if (view === "edit") {
    return (
      <div className="h-dvh bg-gray-100 flex justify-center font-sans overflow-hidden">
        <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
          <Header onBack={goMain} />
          <main className="flex-1 overflow-y-auto pb-32">
            <ProfileEditor avatarUrl={avatarUrl} onCancel={goMain} onSaved={() => { setPhotoReload(value => value + 1); setNotice("บันทึกโปรไฟล์แล้ว"); goMain(); }} />
          </main>
          <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>
      </div>
    );
  }

  if (view === "history") {
    return (
      <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
        <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
          <Header title={t("Cooking History")} onBack={goMain} />
          <div className="flex-1 overflow-y-auto px-5 pb-32">
            <div className="flex gap-2 mb-4">
              {[
                { key: "all", label: "ทั้งหมด" },
                { key: "favorites", label: "♥ รายการโปรด" },
              ].map((chip) => (
                <button
                  key={chip.key}
                  onClick={() => setHistoryFilter(chip.key)}
                  className={`px-4 py-2 rounded-full text-sm font-medium border transition ${
                    historyFilter === chip.key
                      ? "bg-[#EF5A3A] text-white border-[#EF5A3A]"
                      : "bg-white text-[#EF5A3A] border-[#EF5A3A]"
                  }`}
                >
                  {t(chip.label)}
                </button>
              ))}
            </div>
            {!cookingHistory || cookingHistory.length === 0 ? (
              <div className="text-center text-gray-400 mt-10">
                <ChefHat className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                <p>{t("ยังไม่มีเมนูที่เคยสร้าง")}</p>
              </div>
            ) : visibleHistory.length === 0 ? (
              <div className="text-center text-gray-400 mt-10">
                <Heart className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                <p>{t("ยังไม่มีสูตรที่กด ♥ ไว้")}</p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {visibleHistory.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => onOpenHistoryItem?.(item)}
                    className="bg-gray-50 rounded-2xl p-3 flex items-center gap-3 shadow-sm cursor-pointer active:bg-gray-100"
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
                      {item.stars > 0 && (
                        <div className="flex items-center gap-1 mt-1">
                          {[1, 2, 3, 4, 5].map((n) => (
                            <Star
                              key={n}
                              className={`w-3.5 h-3.5 ${
                                n <= item.stars
                                  ? "text-orange-400 fill-orange-400"
                                  : "text-gray-200"
                              }`}
                            />
                          ))}
                          {item.tag && (
                            <span className="text-[11px] text-gray-400 ml-1">
                              {item.tag}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    {item.is_favorite && (
                      <Heart className="w-4 h-4 text-red-500 fill-current shrink-0" />
                    )}
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
          <Header title={t("Language")} onBack={goMain} />
          <div className="flex-1 overflow-y-auto px-5 pb-32">
            <div role="radiogroup" aria-label={t("ภาษา")} className="flex flex-col gap-2">
              {LANGUAGE_OPTIONS.map((opt) => (
                <label
                  key={opt.code}
                  className={`w-full flex items-center justify-between px-4 py-3.5 rounded-2xl border transition focus-within:outline-2 focus-within:outline-[#B93E25] ${languageSaving ? "opacity-60" : "cursor-pointer"} ${
                    language === opt.code
                      ? "bg-orange-50 border-[#EF5A3A]"
                      : "bg-gray-50 border-transparent hover:border-gray-200"
                  }`}
                >
                  <input type="radio" name="profile-language" value={opt.code} checked={language === opt.code}
                    onChange={() => changeLanguage(opt.code)} aria-disabled={languageSaving} className="sr-only" />
                  <span className="text-[15px] font-medium text-gray-800 flex items-center gap-2">
                    <FlagIcon code={opt.code} />
                    {t(opt.label)}
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
                </label>
              ))}
            </div>
            <p role="status" className="mt-4 text-sm text-gray-600">{languageSaving ? t("กำลังบันทึกภาษา...") : ""}</p>
            {languageError && <p role="alert" className="mt-3 text-sm text-red-700">{t(languageError)}</p>}
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
          <Header title={t("Preferences")} onBack={goMain} />
          <div className="flex-1 overflow-y-auto px-5 pb-32">
            <h3 className="text-base font-bold text-black mb-2">{t("อายุ")}</h3>
            <input
              type="number"
              min="1"
              max="120"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              onBlur={() => savePreferences({ age: age === "" ? null : Number(age) })}
              placeholder={t("ระบุอายุ")}
              className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm mb-6 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
            />

            <h3 className="text-base font-bold text-black mb-2">{t("คุณชอบอาหารแบบไหน?")}</h3>
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

            <h3 className="text-base font-bold text-black mb-2">{t("อาการแพ้ หรือข้อจำกัดของคุณ")}</h3>
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
                onBlur={() => {
                  const next = [
                    ...dietaryRestrictions.filter((r) => r !== OTHER_OPTION),
                    restrictionOther || OTHER_OPTION,
                  ];
                  setDietaryRestrictions(next);
                  savePreferences({ dietary_restrictions: next });
                }}
                placeholder={t("ระบุข้อจำกัดของคุณ")}
                className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm mb-4 mt-2 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
              />
            )}
            <div className="mb-4" />

            <h3 className="text-base font-bold text-black mb-2">{t("อุปกรณ์ที่มี")}</h3>
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
                onBlur={() => {
                  const next = [
                    ...equipment.filter((e) => e !== OTHER_OPTION),
                    equipmentOther || OTHER_OPTION,
                  ];
                  setEquipment(next);
                  savePreferences({ equipment: next });
                }}
                placeholder={t("ระบุอุปกรณ์ที่มี")}
                className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm mb-4 mt-2 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
              />
            )}
            <div className="mb-4" />

            <h3 className="text-base font-bold text-black mb-2">{t("คุณทำอาหารบ่อยแค่ไหน?")}</h3>
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

            <h3 className="text-base font-bold text-black mb-2">{t("คุณทำอาหารเพื่ออะไร?")}</h3>
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
              <p className="text-red-600 text-sm text-center mt-4">{t(prefsError)}</p>
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
          <Header title={t("ช่วยเหลือ")} onBack={goMain} />
          <div className="flex-1 overflow-y-auto px-5 pb-32 flex flex-col gap-5">
            <div>
              <h3 className="text-base font-bold text-black mb-2">{t("วิธีใช้งาน")}</h3>
              <p className="text-sm text-gray-600 leading-relaxed">{t("เพิ่มวัตถุดิบใน My Fridge หรือเลือกเมนูจากหน้าแรก แล้วกด \"สร้างเมนูอาหารกันเลย\" เพื่อให้ AI คิดสูตรอาหารจากวัตถุดิบที่มี")}</p>
            </div>
            <div>
              <h3 className="text-base font-bold text-black mb-2">{t("Tips")}</h3>
              <p className="text-sm text-gray-600 leading-relaxed">{t("ระบุอาการแพ้อาหารและอุปกรณ์ที่มีให้ครบ เพื่อให้สูตรอาหารที่ได้ปลอดภัยและทำได้จริง")}</p>
            </div>
            <div>
              <h3 className="text-base font-bold text-black mb-2">{t("ข้อกำหนดการใช้งาน (TOS)")}</h3>
              <p className="text-sm text-gray-600 leading-relaxed">{t("สูตรอาหารและข้อมูลโภชนาการที่สร้างโดย AI เป็นการคาดการณ์เพื่อการอ้างอิงเท่านั้น โปรดตรวจสอบวัตถุดิบและปริมาณจริงก่อนรับประทาน โดยเฉพาะผู้ที่มีอาการแพ้อาหาร")}</p>
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
        <Header onBack={onBack} notificationCount={notificationCount} onNotifications={onNotifications} />

        <div className="flex-1 overflow-y-auto px-5 pb-32">
          {/* Profile Card */}
          {notice && <p role="status" className="text-sm text-green-700 mb-4">{t(notice)}</p>}
          <div className="bg-gray-100 rounded-3xl p-4 flex items-center gap-4 mb-8">
            <div className="w-20 h-20 rounded-full overflow-hidden shadow-sm shrink-0 bg-white flex items-center justify-center">
              {avatarUrl ? <img src={avatarUrl} alt={t("รูปโปรไฟล์")} className="w-full h-full object-cover" /> : <UserRound aria-hidden="true" className="w-10 h-10 text-gray-500" />}
            </div>
            <div className="flex flex-col flex-1 min-w-0">
              <h3 className="text-lg font-bold text-black truncate">
                {user?.display_name || t("ผู้ใช้ Homemade")}
              </h3>
              <div className="flex items-center gap-1.5 text-gray-500 text-sm truncate">
                <Mail className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">{user?.email}</span>
              </div>
            </div>
          </div>
          {photoError && user?.has_avatar && <button type="button" onClick={() => setPhotoReload(value => value + 1)} className="min-h-11 text-sm text-red-700 mb-3">{t("โหลดรูปไม่สำเร็จ ลองอีกครั้ง")}</button>}
          <button type="button" onClick={() => { setNotice(""); setView("edit"); }} className="w-full min-h-11 mb-6 rounded-full border border-[#B93E25] text-[#B93E25] font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]">{t("แก้ไขโปรไฟล์")}</button>

          {/* Menu */}
          <div className="flex flex-col gap-2 mb-6">
            <MenuRow
              icon={<History className="w-4.5 h-4.5" />}
              label={t("Cooking History")}
              onClick={() => setView("history")}
            />
          </div>

          <h3 className="text-sm font-bold text-gray-400 mb-2 px-1">{t("การตั้งค่า")}</h3>
          <div className="flex flex-col gap-2 mb-8">
            <MenuRow
              icon={<Globe className="w-4.5 h-4.5" />}
              label={t("Language")}
              onClick={() => setView("language")}
            />
            <MenuRow
              icon={<SlidersHorizontal className="w-4.5 h-4.5" />}
              label={t("Preferences")}
              onClick={() => setView("preferences")}
            />
            <MenuRow
              icon={<HelpCircle className="w-4.5 h-4.5" />}
              label={t("ช่วยเหลือ")}
              onClick={() => setView("helps")}
            />
          </div>

          {/* Logout */}
          {logoutError && (
            <p className="text-red-600 text-sm text-center mb-2">{t(logoutError)}</p>
          )}
          <button
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="w-full bg-red-500 text-white py-3.5 rounded-full text-base font-bold shadow-md flex items-center justify-center gap-2 hover:bg-red-600 transition disabled:opacity-60"
          >
            <LogOut className="w-5 h-5" />
            {isLoggingOut ? t("กำลังออกจากระบบ...") : t("ออกจากระบบ")}
          </button>
        </div>

        <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
    </div>
  );
}

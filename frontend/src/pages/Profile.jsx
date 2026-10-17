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
  Search,
  X,
  BookOpen,
  Lightbulb,
  Info,
} from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import NotificationBell from "../components/NotificationBell";
import BottomMenu from "../components/bottomMenu";
import { OptionChips, OptionList } from "../components/OptionPicker";
import { getTagColor } from "../utils/tagColors";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../context/LocaleContext";
import ProfileEditor from "../components/ProfileEditor";
import { filterHistory } from "../utils/history";
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
  { code: "th", label: "ไทย", description: "Thai", descriptionLang: "en" },
  { code: "en", label: "English", description: "ภาษาอังกฤษ", descriptionLang: "th" },
];

function Header({ title, onBack, notificationCount, onNotifications, compact = false }) {
  const { t } = useLocale();
  return (
    <div className={compact ? "shrink-0 pt-5 pb-6 px-6 flex items-center justify-center relative z-20" : "pt-8 px-6 h-18 flex items-center justify-center relative z-20 mb-6"}>
      <button
        onClick={onBack}
        aria-label={t("กลับ")}
        className={`absolute ${compact ? "left-5" : "left-6 shadow-md"} w-11 h-11 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]`}
      >
        <ChevronLeft className="w-6 h-6" />
      </button>
      {title ? (
        <h2 className="text-lg font-bold text-black">{title}</h2>
      ) : (
        <img src={logo} alt="HomeMade" className={`${compact ? "h-14" : "h-18"} object-contain`} />
      )}
      {onNotifications && <div className={compact ? "profile-main-notifications absolute right-5" : "absolute right-6 top-1/2 translate-y-4"}><NotificationBell count={notificationCount} onClick={onNotifications} /></div>}
    </div>
  );
}

function FlagIcon({ code }) {
  if (code === "th") {
    return (
      <svg aria-hidden="true" viewBox="0 0 30 20" className="w-5 h-3.5 rounded-sm overflow-hidden shrink-0">
        <rect width="30" height="20" fill="#A51931" />
        <rect y="3.33" width="30" height="13.33" fill="#F4F5F8" />
        <rect y="6.67" width="30" height="6.67" fill="#2D2A4A" />
      </svg>
    );
  }
  if (code === "en") {
    const stripeHeight = 20 / 13;
    return (
      <svg aria-hidden="true" viewBox="0 0 30 20" className="w-5 h-3.5 rounded-sm overflow-hidden shrink-0">
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
      className="w-full min-h-16 hover:bg-gray-50 px-1 py-4 flex items-center gap-3 transition-colors"
    >
      <div aria-hidden="true" className="w-8 h-8 flex items-center justify-center text-[#B93E25] shrink-0">
        {icon}
      </div>
      <span className="flex-1 min-w-0 text-left text-base font-medium text-gray-900">
        {t(label)}
      </span>
      <ChevronRight aria-hidden="true" className="w-5 h-5 text-gray-500 shrink-0" />
    </button>
  );
}

export default function Profile({
  view, setView,
  historyBrowse, setHistoryBrowse,
  cookingHistory,
  activeTab,
  setActiveTab,
  onBack,
  onOpenHistoryItem,
  notificationCount, onNotifications, onNotificationPause,
}) {
  useEffect(() => { onNotificationPause?.(view !== "main"); return () => onNotificationPause?.(false); }, [view, onNotificationPause]);

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

  const visibleHistory = filterHistory(cookingHistory || [], historyBrowse);
  const updateHistoryBrowse = patch => setHistoryBrowse(previous => ({ ...previous, ...patch }));

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
            <label htmlFor="history-search" className="block text-sm font-medium text-gray-700 mb-2">{t("ค้นหาประวัติ")}</label>
            <div className="relative mb-4">
              <Search aria-hidden="true" className="absolute left-3 top-3.5 w-5 h-5 text-gray-500" />
              <input id="history-search" type="search" value={historyBrowse.query}
                onChange={event => updateHistoryBrowse({ query: event.target.value })}
                placeholder={t("ชื่อเมนูหรือวัตถุดิบ")}
                className="w-full min-h-12 rounded-xl border border-gray-300 pl-10 pr-12 text-gray-900 placeholder:text-gray-500 focus-visible:outline-2 focus-visible:outline-[#B93E25]" />
              {historyBrowse.query && <button type="button" aria-label={t("ล้างคำค้น")}
                onClick={() => updateHistoryBrowse({ query: "" })}
                className="absolute right-0 top-0 min-w-12 min-h-12 flex items-center justify-center text-gray-600 rounded-xl focus-visible:outline-2 focus-visible:outline-[#B93E25]"><X className="w-5 h-5" /></button>}
            </div>
            <div className="flex flex-wrap gap-2 mb-4">
              {[
                { key: "all", label: "ทั้งหมด" },
                { key: "favorites", label: "♥ รายการโปรด" },
              ].map((chip) => (
                <button
                  key={chip.key}
                  onClick={() => updateHistoryBrowse({ favorite: chip.key })}
                  aria-pressed={historyBrowse.favorite === chip.key}
                  className={`px-4 py-2 rounded-full text-sm font-medium border transition ${
                    historyBrowse.favorite === chip.key
                      ? "bg-[#B93E25] text-white border-[#B93E25]"
                      : "bg-white text-[#B93E25] border-[#B93E25]"
                  } min-h-11 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]`}
                >
                  {t(chip.label)}
                </button>
              ))}
            </div>
            <label htmlFor="history-rating-filter" className="block text-sm font-medium text-gray-700 mb-2">{t("กรองตามคะแนน")}</label>
            <select id="history-rating-filter" value={historyBrowse.rating}
              onChange={event => updateHistoryBrowse({ rating: event.target.value })}
              className="w-full min-h-12 rounded-xl border border-gray-300 bg-white px-3 text-gray-900 focus-visible:outline-2 focus-visible:outline-[#B93E25]">
              <option value="all">{t("ทุกคะแนน")}</option>
              <option value="unrated">{t("ยังไม่ให้คะแนน")}</option>
              {[1, 2, 3, 4, 5].map(stars => <option key={stars} value={stars}>{t("{stars} ดาว", { stars })}</option>)}
            </select>
            <div className="flex items-center justify-between gap-3 my-3">
              <p role="status" className="text-sm text-gray-600">{t("พบ {count} รายการ", { count: visibleHistory.length })}</p>
              <button type="button" onClick={() => setHistoryBrowse({ query: "", favorite: "all", rating: "all" })}
                disabled={!historyBrowse.query && historyBrowse.favorite === "all" && historyBrowse.rating === "all"}
                className="min-h-11 px-2 text-sm font-medium text-[#B93E25] disabled:text-gray-500 disabled:opacity-60 rounded-lg focus-visible:outline-2 focus-visible:outline-[#B93E25]">{t("ล้างตัวกรอง")}</button>
            </div>
            {!cookingHistory || cookingHistory.length === 0 ? (
              <div className="text-center text-gray-400 mt-10">
                <ChefHat className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                <p>{t("ยังไม่มีเมนูที่เคยสร้าง")}</p>
              </div>
            ) : visibleHistory.length === 0 ? (
              <div className="text-center text-gray-400 mt-10">
                <Heart className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                <p>{t("ไม่พบประวัติที่ตรงกับการค้นหาหรือตัวกรอง")}</p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {visibleHistory.map((item) => (
                  <button type="button"
                    key={item.id}
                    onClick={() => onOpenHistoryItem?.(item)}
                    className="w-full text-left bg-gray-50 rounded-2xl p-3 flex items-center gap-3 shadow-sm cursor-pointer active:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]"
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
                                  ? "text-[#B93E25] fill-[#B93E25]"
                                  : "text-gray-500"
                              }`}
                            />
                          ))}
                          {item.tag && (
                            <span className="text-[11px] text-gray-400 ml-1">
                              {t(item.tag)}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    {item.is_favorite && (
                      <Heart className="w-4 h-4 text-red-500 fill-current shrink-0" />
                    )}
                  </button>
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
          <main className="flex-1 overflow-y-auto px-6 pb-32">
            <fieldset aria-busy={languageSaving} aria-describedby="language-help" className="min-w-0">
              <legend className="text-xl font-semibold text-gray-900">{t("เลือกภาษาของแอป")}</legend>
              <p id="language-help" className="mt-2 mb-6 text-sm text-gray-600 leading-relaxed">{t("เลือกแล้วบันทึกให้อัตโนมัติ")}</p>
              <div className="flex flex-col gap-3">
              {LANGUAGE_OPTIONS.map((opt) => (
                <label
                  key={opt.code}
                  className={`w-full min-h-20 flex items-center justify-between gap-3 px-4 py-4 rounded-2xl border transition-colors focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-[#B93E25] ${languageSaving ? "opacity-60 cursor-wait" : "cursor-pointer"} ${
                    language === opt.code
                      ? "bg-[#FDECE5] border-[#B93E25]"
                      : "bg-white border-gray-300 hover:bg-gray-50 hover:border-gray-400"
                  }`}
                >
                  <input type="radio" name="profile-language" value={opt.code} checked={language === opt.code}
                    onChange={() => changeLanguage(opt.code)} aria-label={opt.label} lang={opt.code} aria-disabled={languageSaving} className="sr-only" />
                  <span className="flex min-w-0 items-center gap-3">
                    <FlagIcon code={opt.code} />
                    <span className="flex flex-col gap-0.5">
                      <span lang={opt.code} className="text-base font-semibold text-gray-900">{opt.label}</span>
                      <span lang={opt.descriptionLang} className={language === opt.code ? "text-sm text-[#93402D]" : "text-sm text-gray-600"}>{opt.description}</span>
                    </span>
                  </span>
                  <span aria-hidden="true" className="flex shrink-0 items-center gap-3">
                    {language === opt.code && <span className="text-xs font-semibold text-[#B93E25]">{t("ใช้งานอยู่")}</span>}
                  <span
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition ${
                      language === opt.code
                        ? "border-[#B93E25]"
                        : "border-gray-400"
                    }`}
                  >
                    {language === opt.code && (
                      <span className="w-2.5 h-2.5 rounded-full bg-[#B93E25]" />
                    )}
                  </span>
                  </span>
                </label>
              ))}
              </div>
            </fieldset>
            <p role="status" className="mt-5 min-h-6 text-sm text-gray-600">{languageSaving ? t("กำลังบันทึกภาษา...") : ""}</p>
            {languageError && <p role="alert" className="mt-3 text-sm text-red-700">{t(languageError)}</p>}
          </main>
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
          <main className="flex-1 min-h-0 overflow-y-auto px-6 pt-2 pb-32">
            <section aria-labelledby="help-how-to" className="mb-8">
              <BookOpen aria-hidden="true" className="w-8 h-8 text-[#B93E25] mb-4" />
              <h1 id="help-how-to" className="text-2xl font-bold text-gray-900 leading-snug mb-3">{t("วิธีใช้งาน")}</h1>
              <p className="text-base text-gray-700 leading-7">{t("เพิ่มวัตถุดิบใน My Fridge หรือเลือกเมนูจากหน้าแรก แล้วกด \"สร้างเมนูอาหารกันเลย\" เพื่อให้ AI คิดสูตรอาหารจากวัตถุดิบที่มี")}</p>
            </section>
            <section aria-labelledby="help-tips" className="border-t border-gray-200 pt-6 mb-8">
              <h2 id="help-tips" className="flex items-center gap-3 text-lg font-semibold text-gray-900 mb-3">
                <Lightbulb aria-hidden="true" className="w-5 h-5 text-[#B93E25] shrink-0" />
                {t("Tips")}
              </h2>
              <p className="text-base text-gray-700 leading-7">{t("ระบุอาการแพ้อาหารและอุปกรณ์ที่มีให้ครบ เพื่อให้สูตรอาหารที่ได้ปลอดภัยและทำได้จริง")}</p>
            </section>
            <section aria-labelledby="help-terms" className="rounded-2xl bg-gray-50 p-5">
              <h2 id="help-terms" className="flex items-start gap-2 text-base font-semibold text-gray-900 mb-3">
                <Info aria-hidden="true" className="w-5 h-5 mt-0.5 text-gray-600 shrink-0" />
                {t("ข้อกำหนดการใช้งาน (TOS)")}
              </h2>
              <p className="text-sm text-gray-600 leading-6">{t("สูตรอาหารและข้อมูลโภชนาการที่สร้างโดย AI เป็นการคาดการณ์เพื่อการอ้างอิงเท่านั้น โปรดตรวจสอบวัตถุดิบและปริมาณจริงก่อนรับประทาน โดยเฉพาะผู้ที่มีอาการแพ้อาหาร")}</p>
            </section>
          </main>
          <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>
      </div>
    );
  }

  return (
    <div className="profile-main-screen h-dvh bg-gray-100 flex justify-center font-sans overflow-hidden">
      <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
        <Header compact onBack={onBack} notificationCount={notificationCount} onNotifications={onNotifications} />

        <main className="profile-main-content flex-1 min-h-0 overflow-y-auto scrollbar-hide px-5 pb-6">
          {notice && <p role="status" className="text-sm text-green-700 mb-4">{t(notice)}</p>}
          <section aria-labelledby="profile-display-name" className="pb-6 border-b border-gray-200">
            <div className="flex items-start gap-4">
              <div className="w-20 h-20 rounded-full overflow-hidden shrink-0 bg-gray-100 flex items-center justify-center">
                {avatarUrl ? <img src={avatarUrl} alt={t("รูปโปรไฟล์")} className="w-full h-full object-cover" /> : <UserRound aria-hidden="true" className="w-10 h-10 text-gray-500" />}
              </div>
              <div className="flex-1 min-w-0">
                <h2 id="profile-display-name" className="text-xl leading-snug font-bold text-gray-900 wrap-anywhere">
                  {user?.display_name || t("ผู้ใช้ Homemade")}
                </h2>
                <div className="flex items-start gap-1.5 mt-2 text-gray-600 text-sm leading-relaxed">
                  <Mail aria-hidden="true" className="w-4 h-4 mt-1 shrink-0" />
                  <span className="min-w-0 wrap-anywhere">{user?.email}</span>
                </div>
                <button type="button" onClick={() => { setNotice(""); setView("edit"); }} className="min-h-11 mt-4 px-4 rounded-full border border-[#B93E25] text-[#B93E25] text-sm font-semibold hover:bg-[#FDECE5] transition-colors">{t("แก้ไขโปรไฟล์")}</button>
              </div>
            </div>
            {photoError && user?.has_avatar && <button type="button" onClick={() => setPhotoReload(value => value + 1)} className="min-h-11 mt-3 text-left text-sm text-red-700 underline underline-offset-4">{t("โหลดรูปไม่สำเร็จ ลองอีกครั้ง")}</button>}
          </section>

          <div className="border-b border-gray-200">
            <MenuRow icon={<History className="w-5 h-5" />} label={t("Cooking History")} onClick={() => setView("history")} />
          </div>

          <section aria-labelledby="profile-settings-heading" className="mt-6">
            <h3 id="profile-settings-heading" className="text-sm font-semibold text-gray-600 mb-2">{t("การตั้งค่า")}</h3>
            <div className="divide-y divide-gray-200 border-b border-gray-200">
              <MenuRow icon={<Globe className="w-5 h-5" />} label={t("Language")} onClick={() => setView("language")} />
              <MenuRow icon={<SlidersHorizontal className="w-5 h-5" />} label={t("Preferences")} onClick={() => setView("preferences")} />
              <MenuRow icon={<HelpCircle className="w-5 h-5" />} label={t("ช่วยเหลือ")} onClick={() => setView("helps")} />
            </div>
          </section>

          {logoutError && <p role="alert" className="text-red-700 text-sm leading-relaxed mt-5">{t(logoutError)}</p>}
          <button onClick={handleLogout} disabled={isLoggingOut}
            className="w-full min-h-12 mt-6 py-3.5 rounded-full bg-red-600 text-white text-base font-bold shadow-md flex items-center justify-center gap-2 hover:bg-red-700 transition-colors disabled:opacity-60">
            <LogOut aria-hidden="true" className="w-5 h-5" />
            {isLoggingOut ? t("กำลังออกจากระบบ...") : t("ออกจากระบบ")}
          </button>
        </main>

        <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
    </div>
  );
}

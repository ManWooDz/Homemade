import { useLocale } from "../context/LocaleContext";
import { Home, Refrigerator, CookingPot, Heart, User } from "lucide-react";

export default function BottomMenu({ activeTab, setActiveTab }) {
    const { t } = useLocale();
    return (
        <nav aria-label={t("เมนูหลัก")} className="absolute bottom-0 w-full bg-white border-t border-gray-200 px-3 py-3 rounded-t-3xl shadow-[0_-10px_40px_rgba(0,0,0,0.05)] z-50 [&_button]:min-h-11 [&_button]:min-w-11 [&_button:focus-visible]:outline-2 [&_button:focus-visible]:outline-offset-2 [&_button:focus-visible]:outline-[#B93E25]">
            <div className="flex justify-between items-center relative">
                <button
                    onClick={() => setActiveTab("home")}
                    aria-current={activeTab === "home" ? "page" : undefined}
                    className={`flex flex-col items-center gap-1 cursor-pointer ${activeTab === "home" ? "text-[#B93E25]" : "text-gray-600"}`}
                >
                    <Home className="w-6 h-6" />
                    <span className="text-caption font-semibold">{t("HOME")}</span>
                </button>

                <button
                    onClick={() => setActiveTab("fridge")}
                    aria-current={activeTab === "fridge" ? "page" : undefined}
                    className={`flex flex-col items-center gap-1 cursor-pointer ${activeTab === "fridge" ? "text-[#B93E25]" : "text-gray-600"}`}
                >
                    <Refrigerator className="w-6 h-6" />
                    <span className="text-caption font-semibold">{t("MY FRIDGE")}</span>
                </button>

                {/* ปุ่มทำอาหารตรงกลาง (ลอยขึ้นมา) */}
                <div className="relative -top-5">
                    <button
                        onClick={() => setActiveTab("cooking")}
                        aria-label={t("COOKING")}
                        aria-current={activeTab === "cooking" ? "page" : undefined}
                        className={`${activeTab === "cooking" ? "bg-[#EF5A3A] shadow-md shadow-orange-500/30" : "bg-gray-200 hover:bg-gray-300"} p-4.5 rounded-full cursor-pointer flex flex-col items-center justify-center transition-all`}
                    >
                        <CookingPot className={`w-7 h-7 ${activeTab === "cooking" ? "text-white" : "text-gray-500"}`} />
                    </button>
                    <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap text-caption font-semibold text-gray-600">{t("COOKING")}</span>
                </div>

                <button
                    onClick={() => setActiveTab("favorites")}
                    aria-current={activeTab === "favorites" ? "page" : undefined}
                    className={`flex flex-col items-center gap-1 ${activeTab === "favorites" ? "text-[#B93E25]" : "text-gray-600"}`}
                >
                    <Heart className="w-6 h-6" />
                    <span className="text-caption font-semibold">{t("FAVORITES")}</span>
                </button>

                <button
                    onClick={() => setActiveTab("me")}
                    aria-current={activeTab === "me" ? "page" : undefined}
                    className={`flex flex-col items-center gap-1 ${activeTab === "me" ? "text-[#B93E25]" : "text-gray-600"}`}
                >
                    <User className="w-6 h-6" />
                    <span className="text-caption font-semibold">{t("ME")}</span>
                </button>
            </div>
        </nav>
    );
}

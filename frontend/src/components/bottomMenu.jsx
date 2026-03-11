import { Home, Refrigerator, CookingPot, Heart, User } from "lucide-react";

export default function BottomMenu({ activeTab, setActiveTab }) {
    return (
        <div className="absolute bottom-0 w-full bg-white border-t border-gray-200 px-6 py-3 rounded-t-3xl shadow-[0_-10px_40px_rgba(0,0,0,0.05)] z-50">
            <div className="flex justify-between items-center relative">
                <button
                    onClick={() => setActiveTab("home")}
                    className={`flex flex-col items-center gap-1 ${activeTab === "home" ? "text-orange-500" : "text-gray-400"}`}
                >
                    <Home className="w-6 h-6" />
                    <span className="text-[10px] font-bold">HOME</span>
                </button>

                <button
                    onClick={() => setActiveTab("fridge")}
                    className={`flex flex-col items-center gap-1 ${activeTab === "fridge" ? "text-orange-500" : "text-gray-400"}`}
                >
                    <Refrigerator className="w-6 h-6" />
                    <span className="text-[10px] font-bold">MY FRIDGE</span>
                </button>

                {/* ปุ่มทำอาหารตรงกลาง (ลอยขึ้นมา) */}
                <div className="relative -top-5">
                    <button
                        onClick={() => setActiveTab("cooking")}
                        className={`${activeTab === "cooking" ? "bg-[#EF5A3A] shadow-md shadow-orange-500/30" : "bg-gray-200 hover:bg-gray-300"} p-4.5 rounded-full flex flex-col items-center justify-center transition-all`}
                    >
                        <CookingPot className={`w-7 h-7 ${activeTab === "cooking" ? "text-white" : "text-gray-500"}`} />
                    </button>
                    <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[10px] font-bold text-gray-400">
                        COOKING
                    </span>
                </div>

                <button
                    onClick={() => setActiveTab("favorites")}
                    className={`flex flex-col items-center gap-1 ${activeTab === "favorites" ? "text-orange-500" : "text-gray-400"}`}
                >
                    <Heart className="w-6 h-6" />
                    <span className="text-[10px] font-bold">FAVORITES</span>
                </button>

                <button
                    onClick={() => setActiveTab("me")}
                    className={`flex flex-col items-center gap-1 ${activeTab === "me" ? "text-orange-500" : "text-gray-400"}`}
                >
                    <User className="w-6 h-6" />
                    <span className="text-[10px] font-bold">ME</span>
                </button>
            </div>
        </div>
    );
}

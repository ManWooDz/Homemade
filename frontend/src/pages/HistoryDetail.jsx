import { ChevronLeft, Star } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import RecipeContent from "../components/RecipeContent";

export default function HistoryDetail({ item, onBack, activeTab, setActiveTab }) {
  if (!item) {
    return null;
  }

  return (
    <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
      <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
        <div className="pt-8 px-6 flex items-center justify-center relative z-20 shrink-0 mb-4 bg-white">
          <button
            onClick={onBack}
            className="absolute left-6 w-10 h-10 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
          <img src={logo} alt="HomeMade" className="h-18 object-contain" />
        </div>

        <div className="flex-1 overflow-y-auto px-6 pb-24 scrollbar-hide">
          {item.stars > 0 && (
            <div className="bg-[#FFF6F2] rounded-2xl p-4 mb-6 flex items-center gap-3">
              <div className="flex items-center gap-0.5">
                {[1, 2, 3, 4, 5].map((n) => (
                  <Star
                    key={n}
                    className={`w-4 h-4 ${
                      n <= item.stars
                        ? "text-orange-400 fill-orange-400"
                        : "text-gray-200"
                    }`}
                  />
                ))}
              </div>
              {item.tag && (
                <span className="text-sm font-medium text-[#EF5A3A]">
                  {item.tag}
                </span>
              )}
              {item.feedback && (
                <span className="text-sm text-gray-500 truncate">
                  "{item.feedback}"
                </span>
              )}
            </div>
          )}

          <RecipeContent recipe={item} />
        </div>

        <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
    </div>
  );
}

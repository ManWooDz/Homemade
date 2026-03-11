import { useState } from "react";
import {
    Home,
    Refrigerator,
    CookingPot,
    Heart,
    User,
    Search,
    SlidersHorizontal,
    Plus,
} from "lucide-react";
import logo from "./assets/HomeMade_Logo.png";
import BottomMenu from "./components/bottomMenu";
import RecipeDetail from "./pages/RecipeDetail";
import CreateRecipe from "./pages/CreateRecipe";

function App() {
    const [activeTab, setActiveTab] = useState("home");
    const [currentView, setCurrentView] = useState("home"); // "home" | "recipe-detail" | "create-recipe"
    const [selectedIngredients, setSelectedIngredients] = useState([]);

    if (currentView === "recipe-detail") {
        return (
            <RecipeDetail 
                onBack={() => setCurrentView("home")} 
                onConfirm={(ingredients) => {
                    setSelectedIngredients(ingredients);
                    setCurrentView("create-recipe");
                    setActiveTab("cooking");
                }}
            />
        );
    }

    if (currentView === "create-recipe") {
        return (
            <CreateRecipe 
                selectedIngredients={selectedIngredients} 
                onBack={() => setCurrentView("recipe-detail")} 
            />
        );
    }

    return (
        // พื้นหลังสีเทา เพื่อให้ตัวแอปสีขาวโดดเด่นขึ้นมา (เวลาเปิดบนคอม)
        <div className="min-h-screen bg-gray-100 flex justify-center font-sans">
            {/* 📱 กล่องแอปพลิเคชัน (จำกัดความกว้างเป็นทรงมือถือ) */}
            <div className="w-full max-w-[430px] bg-white min-h-screen relative overflow-hidden flex flex-col shadow-2xl">
                {/* === เนื้อหาหลักของแอป (Content) === */}
                <div className="flex-1 overflow-y-auto pb-24 px-5 pt-8">
                    {/* Logo */}
                    <div className="flex justify-center mb-6">
                        <img
                            src={logo}
                            alt="HomeMade"
                            className="h-[72px] object-contain"
                        />
                    </div>

                    {/* Search Bar */}
                    <div className="flex items-center gap-3 mb-6">
                        <div className="flex-1 flex items-center bg-white border border-gray-400 rounded-full px-4 py-3">
                            <Search className="w-5 h-5 text-gray-500 mr-2" />
                            <input
                                type="text"
                                placeholder="Find the menu"
                                className="w-full outline-none text-gray-600 bg-transparent text-base"
                            />
                        </div>
                        <button className="bg-[#EF5A3A] p-3 rounded-full text-white shadow-sm hover:bg-orange-600 transition">
                            <SlidersHorizontal className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Banner */}
                    <div className="w-full h-48 bg-black rounded-3xl mb-6 relative overflow-hidden shadow-sm flex items-center">
                        <img
                            src="https://images.unsplash.com/photo-1555939594-58d7cb561ad1?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
                            alt="Cooking Banner"
                            className="absolute inset-0 w-full h-full object-cover opacity-60"
                        />
                        <div className="absolute inset-0 bg-gradient-to-r from-black/80 to-transparent z-0"></div>
                        <div className="relative z-10 text-white w-3/4 pl-6">
                            <h2 className="text-[34px] font-black italic text-white leading-none drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]">
                                TOP 10
                            </h2>
                            <h2 className="text-[34px] font-black italic text-yellow-400 leading-none drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]">
                                COOKING
                            </h2>
                            <h2 className="text-[34px] font-black italic text-yellow-400 leading-none drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]">
                                RECIPES
                            </h2>
                        </div>
                    </div>

                    {/* Categories */}
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-bold text-gray-900">
                            Categories
                        </h3>
                        <span className="text-[#EF5A3A] text-sm font-medium cursor-pointer">
                            See all
                        </span>
                    </div>
                    <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide mb-6 -mx-5 px-5">
                        <button className="bg-[#EF5A3A] text-white px-5 py-2 rounded-full text-sm font-medium whitespace-nowrap shadow-sm">
                            Healthy / Diet
                        </button>
                        <button className="bg-white border border-[#EF5A3A] text-[#EF5A3A] px-5 py-2 rounded-full text-sm font-medium whitespace-nowrap hover:bg-orange-50 transition">
                            Asian Food
                        </button>
                        <button className="bg-white border border-[#EF5A3A] text-[#EF5A3A] px-5 py-2 rounded-full text-sm font-medium whitespace-nowrap hover:bg-orange-50 transition">
                            Western Food
                        </button>
                        <button className="bg-white border border-[#EF5A3A] text-[#EF5A3A] px-5 py-2 rounded-full text-sm font-medium whitespace-nowrap hover:bg-orange-50 transition">
                            Quick
                        </button>
                    </div>

                    {/* Recipe Cards */}
                    <div className="grid grid-cols-2 gap-4">
                        {/* Card 1 */}
                        <div 
                            className="bg-white border border-gray-100 rounded-3xl p-3 shadow-sm relative group cursor-pointer"
                            onClick={() => setCurrentView("recipe-detail")}
                        >
                            <button className="absolute top-4 right-4 text-gray-300 hover:text-red-500 z-10">
                                <Heart className="w-6 h-6" />
                            </button>
                            <div className="w-full aspect-square bg-gray-100 rounded-full mb-3 overflow-hidden">
                                <img
                                    src="https://images.unsplash.com/photo-1512621776951-a57141f2eefd?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80"
                                    alt="Superfood Veggie"
                                    className="w-full h-full object-cover"
                                />
                            </div>
                            <h4 className="font-bold text-gray-800 mb-2 truncate">
                                Superfood Veggie
                            </h4>
                            <div className="flex flex-col gap-1 mb-4">
                                <span className="text-[10px] font-medium bg-green-100 text-green-700 px-2 py-0.5 rounded-full w-max">
                                    Healthy / Diet
                                </span>
                                <span className="text-[10px] font-medium bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full w-max">
                                    Quick & Easy
                                </span>
                            </div>
                            <button className="absolute bottom-3 right-3 bg-gray-900 text-white p-2 rounded-full shadow-md">
                                <Plus className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Card 2 */}
                        <div className="bg-white border border-gray-100 rounded-3xl p-3 shadow-sm relative group">
                            <button className="absolute top-4 right-4 text-gray-300 hover:text-red-500 z-10">
                                <Heart className="w-6 h-6" />
                            </button>
                            <div className="w-full aspect-square bg-gray-100 rounded-full mb-3 overflow-hidden">
                                <img
                                    src="https://images.unsplash.com/photo-1546069901-ba9599a7e63c?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80"
                                    alt="Fresh Power Salad"
                                    className="w-full h-full object-cover"
                                />
                            </div>
                            <h4 className="font-bold text-gray-800 mb-2 truncate">
                                Fresh Power Salad
                            </h4>
                            <div className="flex flex-col gap-1 mb-4">
                                <span className="text-[10px] font-medium bg-green-100 text-green-700 px-2 py-0.5 rounded-full w-max">
                                    Healthy / Diet
                                </span>
                                <span className="text-[10px] font-medium bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full w-max">
                                    Quick & Easy
                                </span>
                            </div>
                            <button className="absolute bottom-3 right-3 bg-gray-900 text-white p-2 rounded-full shadow-md">
                                <Plus className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </div>

                {/* === 🔘 Bottom Navigation (แถบเมนูด้านล่าง) === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

export default App;

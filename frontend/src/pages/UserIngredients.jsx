import { useState } from "react";
import { ChevronLeft, ChevronRight, Plus, PenLine, ScanLine } from "lucide-react";
import { FaUtensils } from "react-icons/fa6";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import { expiryBadgeLabel } from "../utils/expiry";

export default function UserIngredients({
    userIngredients,
    onBack,
    activeTab,
    setActiveTab,
    onAddManually,
    onScanBarcode,
    onOpenIngredient,
}) {
    const [selectedCategory, setSelectedCategory] = useState("All");
    const [showAddMenu, setShowAddMenu] = useState(false);

    const categories = [
        "All",
        "Meat & Poultry",
        "Vegetables",
        "Fruits",
        "Other",
    ];

    const filteredIngredients =
        selectedCategory === "All"
            ? userIngredients
            : userIngredients.filter(
                  (ing) => ing.category === selectedCategory,
              );

    return (
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                {/* Header Actions */}
                <div className="pt-8 px-6 flex items-center justify-center relative z-20 mb-6">
                    <button
                        onClick={onBack}
                        className="absolute left-6 w-10 h-10 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md"
                    >
                        <ChevronLeft className="w-6 h-6" />
                    </button>
                    <img
                        src={logo}
                        alt="HomeMade"
                        className="h-18 object-contain"
                    />
                </div>

                <div className="flex-1 overflow-y-auto pb-32">
                    <div className="px-5 mb-4 flex items-center justify-between">
                        <h2 className="text-2xl font-bold text-gray-900">
                            My Fridge
                        </h2>
                        <span className="text-sm font-medium text-gray-500">
                            {userIngredients.length} Items
                        </span>
                    </div>

                    {/* Categories Strip */}
                    <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide mb-4 px-5">
                        {categories.map((cat, index) => (
                            <button
                                key={index}
                                onClick={() => setSelectedCategory(cat)}
                                className={`px-5 py-2 rounded-full text-sm font-medium whitespace-nowrap shadow-sm transition ${
                                    selectedCategory === cat
                                        ? "bg-[#EF5A3A] text-white"
                                        : "bg-white border border-[#EF5A3A] text-[#EF5A3A] hover:bg-orange-50"
                                }`}
                            >
                                {cat}
                            </button>
                        ))}
                    </div>

                    {/* Ingredients List */}
                    <div className="flex flex-col gap-3 px-5">
                        {filteredIngredients.length === 0 && selectedCategory === "All" ? (
                            <div className="flex flex-col items-center text-center text-gray-400 mt-10">
                                <FaUtensils className="w-12 h-12 mb-3" />
                                <p>Add your ingredient to get started</p>
                            </div>
                        ) : filteredIngredients.length === 0 ? (
                            <div className="text-center text-gray-400 mt-10">
                                <p>No items found in '{selectedCategory}'.</p>
                            </div>
                        ) : (
                            filteredIngredients.map((ing) => (
                                <button
                                    key={ing.id}
                                    onClick={() => onOpenIngredient(ing)}
                                    className="flex items-center justify-between bg-white border border-gray-100 p-3 rounded-2xl shadow-sm text-left hover:border-[#EF5A3A] transition"
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 bg-gray-50 rounded-full overflow-hidden shrink-0 border border-gray-100">
                                            <img
                                                src={
                                                    ing.image ||
                                                    "http://localhost:8000/images/No-image-available.png"
                                                }
                                                alt={ing.name}
                                                className="w-full h-full object-cover"
                                                onError={(e) => {
                                                    e.target.src =
                                                        "http://localhost:8000/images/No-image-available.png";
                                                }}
                                            />
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="font-semibold text-gray-800 text-lg leading-tight">
                                                {ing.name}
                                            </span>
                                            {expiryBadgeLabel(ing.expiry_date) && (
                                                <span className="text-xs font-medium text-red-500 mt-0.5">
                                                    {expiryBadgeLabel(ing.expiry_date)}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <ChevronRight className="w-5 h-5 text-gray-300" />
                                </button>
                            ))
                        )}
                    </div>
                </div>

                {/* Floating Action Button */}
                <button
                    onClick={() => setShowAddMenu(true)}
                    className="absolute bottom-28 right-6 w-14 h-14 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-lg hover:scale-105 transition-transform z-40"
                    style={{ boxShadow: "0 4px 20px rgba(0,0,0,0.3)" }}
                >
                    <Plus className="w-7 h-7" />
                </button>

                {/* Add-ingredient choice sheet */}
                {showAddMenu && (
                    <>
                        <div
                            className="absolute inset-0 bg-black/30 z-40"
                            onClick={() => setShowAddMenu(false)}
                        ></div>
                        <div className="absolute left-0 right-0 bottom-0 bg-white rounded-t-3xl shadow-[0_-10px_40px_rgba(0,0,0,0.1)] z-50 p-5 pb-28 flex flex-col gap-3">
                            <p className="text-sm font-bold text-gray-700 mb-1">
                                Add Ingredient
                            </p>
                            <button
                                onClick={() => {
                                    setShowAddMenu(false);
                                    onAddManually();
                                }}
                                className="w-full flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3.5 text-left hover:border-[#EF5A3A] transition"
                            >
                                <PenLine className="w-5 h-5 text-[#EF5A3A]" />
                                <span className="font-medium text-gray-800">
                                    Add Manually
                                </span>
                            </button>
                            <button
                                onClick={() => {
                                    setShowAddMenu(false);
                                    onScanBarcode();
                                }}
                                className="w-full flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3.5 text-left hover:border-[#EF5A3A] transition"
                            >
                                <ScanLine className="w-5 h-5 text-[#EF5A3A]" />
                                <span className="font-medium text-gray-800">
                                    Scan Barcode
                                </span>
                            </button>
                        </div>
                    </>
                )}

                {/* === Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

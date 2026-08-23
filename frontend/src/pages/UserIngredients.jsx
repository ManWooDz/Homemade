import { useState } from "react";
import { ChevronLeft, Trash2, Plus } from "lucide-react";
import { FaUtensils } from "react-icons/fa6";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";

export default function UserIngredients({
    userIngredients,
    setUserIngredients,
    onBack,
    activeTab,
    setActiveTab,
    goToAddIngredient,
}) {
    const [selectedCategory, setSelectedCategory] = useState("All");

    const categories = [
        "All",
        "Meat & Poultry",
        "Vegetables",
        "Fruits",
        "Other",
    ];

    const handleDeleteIngredient = async (id) => {
        try {
            const response = await fetch(
                `http://localhost:8000/api/user-ingredients/${id}`,
                {
                    method: "DELETE",
                },
            );
            const result = await response.json();
            if (result.status === "success") {
                setUserIngredients(
                    userIngredients.filter((ing) => ing.id !== id),
                );
            } else {
                console.error("Failed to delete ingredient", result.message);
            }
        } catch (error) {
            console.error("Error deleting ingredient:", error);
        }
    };

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
                                <div
                                    key={ing.id}
                                    className="flex items-center justify-between bg-white border border-gray-100 p-3 rounded-2xl shadow-sm"
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
                                        </div>
                                    </div>
                                    <button
                                        onClick={() =>
                                            handleDeleteIngredient(ing.id)
                                        }
                                        className="w-10 h-10 flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-full transition"
                                    >
                                        <Trash2 className="w-5 h-5" />
                                    </button>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Floating Action Button */}
                <button
                    onClick={goToAddIngredient}
                    className="absolute bottom-28 right-6 w-14 h-14 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-lg hover:scale-105 transition-transform z-40"
                    style={{ boxShadow: "0 4px 20px rgba(0,0,0,0.3)" }}
                >
                    <Plus className="w-7 h-7" />
                </button>

                {/* === Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

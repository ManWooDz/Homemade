import { useState } from "react";
import { ChevronLeft, Heart, Star, CheckSquare } from "lucide-react";
import { motion } from "framer-motion";
import logo from "../assets/HomeMade_Logo.png";

import BottomMenu from "../components/bottomMenu";

export default function RecipeDetail({ recipe, onBack, onConfirm, activeTab, setActiveTab }) {
    const [ingredients, setIngredients] = useState(() => {
        if (recipe && recipe.ingredients) {
            return recipe.ingredients.map((ing, index) => ({
                id: index + 1,
                name: ing.name || ing,
                image: ing.image || "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=150",
                selected: true,
            }));
        }
        return [
            {
                id: 1,
                name: "Green Oak",
                image: "https://images.unsplash.com/photo-1622206151226-18ca2c9ab4a1?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80",
                selected: true,
            },
            {
                id: 2,
                name: "Tomatoes",
                image: "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80",
                selected: true,
            },
            {
                id: 3,
                name: "Purple cabbage",
                image: "https://images.unsplash.com/photo-1596484552834-6a58f8510a76?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80",
                selected: true,
            },
        ];
    });

    const toggleIngredient = (id) => {
        setIngredients(
            ingredients.map((ing) =>
                ing.id === id ? { ...ing, selected: !ing.selected } : ing,
            ),
        );
    };

    return (
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                {/* Header Actions */}
                <div className="absolute top-8 left-0 right-0 px-6 flex justify-between items-center z-20">
                    <button
                        onClick={onBack}
                        className="w-10 h-10 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md"
                    >
                        <ChevronLeft className="w-6 h-6" />
                    </button>
                    <button className="text-gray-400 hover:text-red-500">
                        <Heart className="w-8 h-8" />
                    </button>
                </div>

                {/* Logo & Top Image Area */}
                <div className="pt-8 pb-32 flex flex-col items-center bg-white relative z-10">
                    <div className="mb-6">
                        <img
                            src={logo}
                            alt="HomeMade"
                            className="h-[72px] object-contain"
                        />
                    </div>
                    {/* Big Salad Image */}
                    <div className="w-64 h-64 rounded-full overflow-hidden shadow-sm">
                        <img
                            src={
                                recipe?.image ||
                                "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
                            }
                            alt={recipe?.name || "Superfood Veggie Bowl"}
                            className="w-full h-full object-cover"
                        />
                    </div>
                </div>

                {/* Draggable Bottom Sheet overlay */}
                <motion.div
                    className="absolute left-0 right-0 mx-auto w-full max-w-[430px] bg-white rounded-t-[40px] shadow-[0_-10px_40px_rgba(0,0,0,0.1)] z-30 pb-10"
                    initial={{ y: "10%" }}
                    drag="y"
                    dragConstraints={{ top: -200, bottom: 0 }}
                    style={{ top: "45%", height: "90%" }}
                >
                    {/* Drag Handle Indicator */}
                    <div className="w-full flex justify-center pt-4 pb-2">
                        <div className="w-12 h-1.5 bg-gray-200 rounded-full"></div>
                    </div>

                    <div className="px-6 h-full overflow-y-auto pb-50 scrollbar-hide">
                        <h2 className="text-[28px] font-bold text-black mb-2 leading-tight">
                            {recipe?.name || "Dishes Name"}
                        </h2>
                        <div className="flex items-center gap-2 mb-6">
                            <Star className="w-5 h-5 text-orange-400 fill-orange-400" />
                            <span className="font-bold text-black text-sm">
                                {recipe?.ratings || "error"}
                            </span>
                            <span className="text-gray-500 text-sm mb-0">
                                ({recipe?.review || "error"} Reviews)
                            </span>
                        </div>

                        <h3 className="text-xl font-medium text-black mb-2">
                            Description
                        </h3>
                        <p className="text-black text-sm mb-6 leading-relaxed">
                            {recipe?.short_description ||
                                "error"}
                        </p>

                        {/* Nutrition Section */}
                        {recipe?.nutrition && (
                            <div className="mb-6">
                                <h3 className="text-[26px] font-medium text-black mb-4">
                                    Nutrition
                                </h3>

                                <div className="flex flex-col gap-3">
                                    {/* Calories Header */}
                                    <div className="bg-[#FFF6F2] rounded-3xl p-5 flex justify-between items-center shadow-sm">
                                        <div className="flex flex-col gap-1">
                                            <span className="text-4xl font-semibold text-[#EF5A3A] leading-none">
                                                {recipe.nutrition.calories}
                                            </span>
                                            <span className="text-lg text-gray-500 font-medium">
                                                แคลอรี่ทั้งหมด
                                            </span>
                                        </div>
                                        <span className="text-lg text-gray-500 font-medium items-center flex mt-6">
                                            ต่อ 1 เสิร์ฟ (400g)
                                        </span>
                                    </div>

                                    {/* Macros Grid */}
                                    <div className="grid grid-cols-3 gap-3">
                                        {/* Carbs */}
                                        <div className="bg-[#e4fbec] rounded-3xl p-4 flex flex-col justify-center items-center relative overflow-hidden h-25 shadow-sm">
                                            <span className="text-2xl font-bold text-black leading-none mb-1">
                                                {recipe.nutrition.carbs_g}g
                                            </span>
                                            <span className="text-sm font-medium text-[#767676] mb-2">
                                                คาร์โบไฮเดรต
                                            </span>
                                            <div className="absolute bottom-4 left-4 right-4 h-1.5 bg-black/10 rounded-full">
                                                <div
                                                    className="h-full bg-[#00D740] rounded-full"
                                                    style={{ width: "60%" }}
                                                ></div>
                                            </div>
                                        </div>

                                        {/* Protein */}
                                        <div className="bg-[#eaf3ff] rounded-3xl p-4 flex flex-col justify-center items-center relative overflow-hidden h-25 shadow-sm">
                                            <span className="text-2xl font-bold text-black leading-none mb-1">
                                                {recipe.nutrition.protein_g}g
                                            </span>
                                            <span className="text-sm font-medium text-[#767676] mb-2">
                                                โปรตีน
                                            </span>
                                            <div className="absolute bottom-4 left-4 right-4 h-1.5 bg-black/10 rounded-full">
                                                <div
                                                    className="h-full bg-[#1975FF] rounded-full"
                                                    style={{ width: "40%" }}
                                                ></div>
                                            </div>
                                        </div>

                                        {/* Fat */}
                                        <div className="bg-[#fffad8] rounded-3xl p-4 flex flex-col justify-center items-center relative overflow-hidden h-25 shadow-sm">
                                            <span className="text-2xl font-bold text-black leading-none mb-1">
                                                {recipe.nutrition.fat_g}g
                                            </span>
                                            <span className="text-sm font-medium text-[#767676] mb-2">
                                                ไขมัน
                                            </span>
                                            <div className="absolute bottom-4 left-4 right-4 h-1.5 bg-black/10 rounded-full">
                                                <div
                                                    className="h-full bg-[#FFB901] rounded-full"
                                                    style={{ width: "70%" }}
                                                ></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        <h3 className="text-xl font-medium text-black mb-4">
                            Ingredient
                        </h3>
                        <div className="flex flex-col gap-3">
                            {ingredients.map((ing) => (
                                <div
                                    key={ing.id}
                                    className="flex items-center justify-between bg-gray-100 p-3 rounded-2xl cursor-pointer"
                                    onClick={() => toggleIngredient(ing.id)}
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 bg-white rounded-full overflow-hidden p-1 shadow-sm">
                                            <img
                                                src={ing.image}
                                                alt={ing.name}
                                                className="w-full h-full object-cover rounded-full"
                                            />
                                        </div>
                                        <div className="flex flex-col justify-center">
                                            <span className="font-medium text-black text-[15px]">
                                                {ing.name}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="mr-2">
                                        <div
                                            className={`w-6 h-6 rounded flex items-center justify-center transition-colors ${ing.selected ? "bg-gray-800" : "bg-white border-2 border-gray-300"}`}
                                        >
                                            {ing.selected && (
                                                <svg
                                                    className="w-4 h-4 text-white"
                                                    fill="none"
                                                    stroke="currentColor"
                                                    viewBox="0 0 24 24"
                                                >
                                                    <path
                                                        strokeLinecap="round"
                                                        strokeLinejoin="round"
                                                        strokeWidth="3"
                                                        d="M5 13l4 4L19 7"
                                                    />
                                                </svg>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}

                            {/* Confirm button */}
                            <button
                                onClick={() =>
                                    onConfirm(
                                        ingredients.filter(
                                            (ing) => ing.selected,
                                        ),
                                    )
                                }
                                className="bg-[#EF5A3A] text-white px-5 py-3 rounded-full text-base font-bold shadow-md mt-4 w-full"
                            >
                                Confirm
                            </button>
                        </div>
                    </div>
                </motion.div>

                {/* === 🔘 Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

import { ChevronLeft } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import { useState } from "react";

export default function CreateRecipe({ recipe, selectedIngredients, onBack, activeTab, setActiveTab, onGenerate }) {
    const [taste, setTaste] = useState("");
    const [allergies, setAllergies] = useState("");
    const [equipment, setEquipment] = useState("");
    const [extra, setExtra] = useState("");

    const handleGenerateClick = () => {
        onGenerate({
            taste,
            allergies,
            equipment,
            extra
        });
    };

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

                <div className="flex-1 overflow-y-auto px-5 pb-32">
                    {/* Summary Card */}
                    <div className="bg-gray-100 rounded-3xl p-4 flex items-center gap-4 mb-8">
                        <div className="w-24 h-24 rounded-full overflow-hidden shadow-sm shrink-0 bg-white">
                            <img
                                src={
                                    recipe?.image ||
                                    "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80"
                                }
                                alt={recipe?.name || "Food Menu"}
                                className="w-full h-full object-cover"
                            />
                        </div>
                        <div className="flex flex-col flex-1 pl-2 overflow-hidden">
                            <h3 className="text-lg font-bold text-black mb-1 truncate">
                                {recipe?.name || "Food Menu's name"}
                            </h3>
                            <p className="text-[12px] text-gray-500 mb-2 line-clamp-2">
                                {recipe?.short_description ||
                                    "short-description"}
                            </p>
                            <div className="flex gap-2">
                                {recipe?.tags &&
                                    recipe.tags.slice(0, 2).map((tag, idx) => (
                                        <span
                                            key={idx}
                                            className={`text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${
                                                idx === 0
                                                    ? "bg-green-200 text-green-700"
                                                    : "bg-yellow-400 text-gray-900"
                                            }`}
                                        >
                                            {tag}
                                        </span>
                                    ))}
                            </div>
                        </div>
                    </div>

                    {/* Description Textarea */}
                    <div className="mb-8">
                        <h3 className="text-lg font-bold text-black mb-4">
                            วัตถุดิบที่เลือก
                        </h3>
                        {/* Display Selected Ingredients */}
                        {selectedIngredients &&
                            selectedIngredients.length > 0 && (
                                <div className="flex flex-wrap gap-2 mb-4">
                                    {selectedIngredients.map((ing) => (
                                        <div
                                            key={ing.id}
                                            className="bg-orange-50 border border-[#EF5A3A] px-3 py-1.5 rounded-full flex items-center gap-2"
                                        >
                                            <img
                                                src={ing.image}
                                                alt={ing.name}
                                                className="w-5 h-5 rounded-full object-cover"
                                            />
                                            <span className="text-sm font-medium text-[#EF5A3A]">
                                                {ing.name}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}

                        <h3 className="text-lg font-bold text-black mt-2 mb-2">
                            รสชาติ
                        </h3>
                        <textarea
                            className="w-full h-20 border border-gray-400 bg-white rounded-3xl p-5 text-gray-500 placeholder-gray-500 text-base outline-none resize-none shadow-sm"
                            placeholder="เช่น ระดับความเผ็ด เปรี้ยว หวาน เค็ม"
                            value={taste}
                            onChange={(e) => setTaste(e.target.value)}
                        ></textarea>

                        <h3 className="text-lg font-bold text-black  mt-2 mb-2">
                            อาการแพ้อาหาร
                        </h3>
                        <textarea
                            className="w-full h-20 border border-gray-400 bg-white rounded-3xl p-5 text-gray-500 placeholder-gray-500 text-base outline-none resize-none shadow-sm"
                            placeholder="เช่น แพ้กุ้ง แพ้ถั่ว"
                            value={allergies}
                            onChange={(e) => setAllergies(e.target.value)}
                        ></textarea>
                        <h3 className="text-lg font-bold text-black  mt-2 mb-2">
                            อุปกรณ์ที่มี
                        </h3>
                        <textarea
                            className="w-full h-20 border border-gray-400 bg-white rounded-3xl p-5 text-gray-500 placeholder-gray-500 text-base outline-none resize-none shadow-sm"
                            placeholder="เช่น ไมโครเวฟ, หม้อทอดไร้น้ำมัน"
                            value={equipment}
                            onChange={(e) => setEquipment(e.target.value)}
                        ></textarea>
                        <h3 className="text-lg font-bold text-black mt-2 mb-2">
                            เงื่อนไขเพิ่มเติม, สิ่งที่อยากได้
                        </h3>
                        <textarea
                            className="w-full h-40 border border-gray-400 bg-white rounded-3xl p-5 text-gray-500 placeholder-gray-500 text-base outline-none resize-none shadow-sm"
                            placeholder="เช่น สิ่งที่ต้องระวัง"
                            value={extra}
                            onChange={(e) => setExtra(e.target.value)}
                        ></textarea>
                    </div>

                    {/* Action Button */}
                    <button 
                        onClick={handleGenerateClick}
                        className="w-full bg-[#EF5A3A] text-white py-4.5 rounded-full text-lg font-medium shadow-md flex items-center justify-center gap-2 hover:bg-orange-600 transition"
                    >
                        {/* Custom minimal pan icon to match the specific reference button icon... SVG simplified from Lucide pot for precision might be rough, we'll try something similar or just a clean SVG */}
                        <svg
                            className="w-6 h-6"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth="2"
                                d="M12 4v2m-6 4v2m12-2v2M4 14a8 8 0 0016 0H4zm0 0h16v1a3 3 0 01-3 3H7a3 3 0 01-3-3v-1z"
                            />
                        </svg>
                        สร้างเมนูอาหารกันเลย
                    </button>
                </div>

                {/* === 🔘 Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

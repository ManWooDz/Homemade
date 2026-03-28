import { useState } from "react";
import { ChevronLeft } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";

export default function CustomCookingPage({ userIngredients, onBack, activeTab, setActiveTab, onGenerate }) {
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
                    {/* Page Title */}
                    <div className="mb-6">
                        <h2 className="text-2xl font-bold text-gray-900 leading-tight">
                            Custom Cooking
                        </h2>
                        <p className="text-sm text-gray-500 mt-1">
                            Generate a new menu using just the ingredients in your fridge.
                        </p>
                    </div>

                    {/* Description Textarea */}
                    <div className="mb-8">
                        <h3 className="text-lg font-bold text-black mb-4">
                            วัตถุดิบจากตู้เย็น (My Fridge)
                        </h3>
                        {/* Display Fridge Ingredients */}
                        {userIngredients && userIngredients.length > 0 ? (
                            <div className="flex flex-wrap gap-2 mb-6">
                                {userIngredients.map((ing) => (
                                    <div
                                        key={ing.id}
                                        className="bg-orange-50 border border-[#EF5A3A] px-3 py-1.5 rounded-full flex items-center gap-2"
                                    >
                                        <img
                                            src={ing.image}
                                            alt={ing.name}
                                            className="w-5 h-5 rounded-full object-cover"
                                            onError={(e) => {
                                                e.target.src = "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=150";
                                            }}
                                        />
                                        <span className="text-sm font-medium text-[#EF5A3A]">
                                            {ing.name}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="bg-gray-50 rounded-2xl p-4 text-center text-sm text-gray-500 mb-6">
                                ตู้เย็นของคุณว่างเปล่า คุณสามารถไปเพิ่มวัตถุดิบได้ที่ My Fridge
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
                        disabled={!userIngredients || userIngredients.length === 0}
                        className="w-full bg-[#EF5A3A] text-white py-4.5 rounded-full text-lg font-medium shadow-md flex items-center justify-center gap-2 hover:bg-orange-600 disabled:opacity-50 transition"
                    >
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
                        สร้างเมนูจากวัตถุดิบในตู้เย็น
                    </button>
                </div>

                {/* === Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

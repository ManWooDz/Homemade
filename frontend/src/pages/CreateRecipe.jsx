import { ChevronLeft } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import { useState } from "react";

export default function CreateRecipe({ selectedIngredients, onBack }) {
    const [activeTab, setActiveTab] = useState("cooking");

    return (
        <div className="min-h-screen bg-gray-100 flex justify-center font-sans">
            <div className="w-full max-w-[430px] bg-white min-h-screen relative overflow-hidden flex flex-col shadow-2xl">
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
                        className="h-[72px] object-contain"
                    />
                </div>

                <div className="flex-1 overflow-y-auto px-5 pb-32">
                    {/* Summary Card */}
                    <div className="bg-gray-100 rounded-3xl p-4 flex items-center gap-4 mb-8">
                        <div className="w-24 h-24 rounded-full overflow-hidden shadow-sm flex-shrink-0 bg-white">
                            <img
                                src="https://images.unsplash.com/photo-1512621776951-a57141f2eefd?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80"
                                alt="Food Menu"
                                className="w-full h-full object-cover"
                            />
                        </div>
                        <div className="flex flex-col flex-1 pl-2">
                            <h3 className="text-lg font-bold text-black mb-1">
                                Food Menu's name
                            </h3>
                            <p className="text-sm text-gray-800 mb-2">
                                short-description
                            </p>
                            <div className="flex gap-2">
                                <span className="text-[10px] font-medium bg-green-200 text-green-700 px-2 py-0.5 rounded-full whitespace-nowrap">
                                    Healthy / Diet
                                </span>
                                <span className="text-[10px] font-medium bg-yellow-400 text-gray-900 px-2 py-0.5 rounded-full whitespace-nowrap">
                                    Quick & Easy
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Description Textarea */}
                    <div className="mb-8">
                        <h3 className="text-lg font-bold text-black mb-4">
                            อธิบายสูตรอาหารที่คุณต้องการ
                        </h3>
                        <textarea 
                            className="w-full h-40 border border-gray-400 bg-white rounded-3xl p-5 text-gray-500 placeholder-gray-500 text-base outline-none resize-none shadow-sm"
                            placeholder="เงื่อนไขเพิ่มเติม (Optional)"
                        ></textarea>
                    </div>

                    {/* Action Button */}
                    <button className="w-full bg-[#EF5A3A] text-white py-[18px] rounded-full text-lg font-medium shadow-md flex items-center justify-center gap-2 hover:bg-orange-600 transition">
                        {/* Custom minimal pan icon to match the specific reference button icon... SVG simplified from Lucide pot for precision might be rough, we'll try something similar or just a clean SVG */}
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v2m-6 4v2m12-2v2M4 14a8 8 0 0016 0H4zm0 0h16v1a3 3 0 01-3 3H7a3 3 0 01-3-3v-1z" />
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

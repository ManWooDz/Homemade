import { ChevronLeft, Flame, AlertTriangle, ChefHat } from "lucide-react";
import { motion } from "framer-motion";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";

export default function CookingPage({ recipe, generatedRecipe, isGenerating, onBack, activeTab, setActiveTab }) {
    
    // Loading Screen
    if (isGenerating) {
        return (
            <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
                <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl items-center justify-center space-y-6">
                    <motion.div 
                        initial={{ opacity: 0.5, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1.1 }}
                        transition={{ repeat: Infinity, duration: 1, repeatType: "reverse" }}
                    >
                        <ChefHat className="w-24 h-24 text-[#EF5A3A] drop-shadow-lg" />
                    </motion.div>
                    <h2 className="text-2xl font-bold text-gray-800 tracking-wide">
                        กำลังคิดค้นเมนู...
                    </h2>
                    <p className="text-gray-500 text-center px-8">
                        เชฟ AI กำลังนำวัตถุดิบและเงื่อนไขของคุณมาปรุงเป็นสูตรพิเศษ
                    </p>
                </div>
            </div>
        );
    }

    // Fallback if no recipe generated successfully yet
    if (!generatedRecipe) {
        return (
            <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
                <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl items-center justify-center space-y-4">
                    <p className="text-gray-500">เกิดข้อผิดพลาดในการสร้างสูตรอาหาร</p>
                    <button onClick={onBack} className="bg-[#EF5A3A] text-white px-6 py-2 rounded-full font-medium shadow-sm">กลับไปแก้ไข</button>
                    <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
                </div>
            </div>
        );
    }

    // Success Screen
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
                </div>

                {/* Logo & Top Image Area */}
                <div className="pt-8 pb-32 flex flex-col items-center bg-white relative z-10">
                    <div className="mb-6">
                        <img src={logo} alt="HomeMade" className="h-18 object-contain" />
                    </div>
                    {/* Image (Fallback to base recipe since LLM doesn't generate images easily) */}
                    <div className="w-64 h-64 rounded-full overflow-hidden shadow-sm">
                        <img
                            src={recipe?.image || "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"}
                            alt={generatedRecipe.recipe_name}
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
                    <div className="w-full flex justify-center pt-4 pb-2">
                        <div className="w-12 h-1.5 bg-gray-200 rounded-full"></div>
                    </div>

                    <div className="px-6 h-full overflow-y-auto pb-50 scrollbar-hide">
                        <h2 className="text-[26px] font-bold text-black mb-2 leading-tight">
                            {generatedRecipe.recipe_name}
                        </h2>
                        
                        {/* Diet Tags */}
                        {generatedRecipe.diet_tags && generatedRecipe.diet_tags.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-6 mt-3">
                                {generatedRecipe.diet_tags.map((tag, idx) => (
                                    <span key={idx} className="bg-orange-100 text-[#EF5A3A] px-3 py-1 rounded-full text-[12px] font-medium border border-orange-200">
                                        {tag}
                                    </span>
                                ))}
                            </div>
                        )}

                        {/* Safety Warning */}
                        {generatedRecipe.safety_warning && generatedRecipe.safety_warning !== "ระวังความร้อนขณะประกอบอาหาร" && (
                            <div className="mb-6 bg-red-50 border border-red-200 rounded-2xl p-4 flex gap-3 text-red-700 shadow-sm items-start">
                                <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                                <span className="text-sm font-medium leading-relaxed">
                                    {generatedRecipe.safety_warning}
                                </span>
                            </div>
                        )}

                        {/* Nutrition Section */}
                        {generatedRecipe.nutrition && (
                            <div className="mb-6">
                                <h3 className="text-xl font-medium text-black mb-4">โภชนาการที่คาดการณ์</h3>
                                <div className="flex flex-col gap-3">
                                    <div className="bg-[#FFF6F2] rounded-3xl p-5 flex justify-between items-center shadow-sm">
                                        <div className="flex flex-col gap-1">
                                            <span className="text-4xl font-semibold text-[#EF5A3A] leading-none">
                                                {generatedRecipe.nutrition.calories}
                                            </span>
                                            <span className="text-lg text-gray-500 font-medium">แคลอรี่รวม</span>
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-3 gap-3">
                                        <div className="bg-[#e4fbec] rounded-3xl p-4 flex flex-col justify-center items-center shadow-sm h-25">
                                            <span className="text-2xl font-bold text-black leading-none mb-1">{generatedRecipe.nutrition.carbs_g}g</span>
                                            <span className="text-[12px] font-medium text-[#767676]">คาร์บ</span>
                                        </div>
                                        <div className="bg-[#eaf3ff] rounded-3xl p-4 flex flex-col justify-center items-center shadow-sm h-25">
                                            <span className="text-2xl font-bold text-black leading-none mb-1">{generatedRecipe.nutrition.protein_g}g</span>
                                            <span className="text-[12px] font-medium text-[#767676]">โปรตีน</span>
                                        </div>
                                        <div className="bg-[#fffad8] rounded-3xl p-4 flex flex-col justify-center items-center shadow-sm h-25">
                                            <span className="text-2xl font-bold text-black leading-none mb-1">{generatedRecipe.nutrition.fat_g}g</span>
                                            <span className="text-[12px] font-medium text-[#767676]">ไขมัน</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Ingredients */}
                        <div className="mb-6">
                            <h3 className="text-xl font-medium text-black mb-4">วัตถุดิบที่ปรับแก้แล้ว</h3>
                            <ul className="flex flex-col gap-2">
                                {generatedRecipe.adjusted_ingredients?.map((ing, idx) => (
                                    <li key={idx} className="bg-gray-50 flex items-center gap-3 p-3 rounded-xl border border-gray-100 shadow-[0_2px_4px_rgba(0,0,0,0.02)]">
                                        <div className="w-2 h-2 rounded-full bg-[#EF5A3A]"></div>
                                        <span className="text-gray-700 text-[15px]">{ing}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Instructions */}
                        <div className="mb-6">
                            <h3 className="text-xl font-medium text-black mb-4 flex items-center gap-2">
                                <Flame className="w-5 h-5 text-[#EF5A3A]" />
                                วิธีทำ
                            </h3>
                            <div className="flex flex-col gap-4">
                                {generatedRecipe.instructions?.map((step, idx) => {
                                    // Remove leading numbers since we add styled numbers
                                    const cleanedStep = step.replace(/^\d+\.\s*/, '');
                                    return (
                                        <div key={idx} className="flex gap-4">
                                            <div className="w-8 h-8 rounded-full bg-orange-100 text-[#EF5A3A] font-bold flex items-center justify-center shrink-0">
                                                {idx + 1}
                                            </div>
                                            <p className="text-gray-700 leading-relaxed pt-1 flex-1">
                                                {cleanedStep}
                                            </p>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>

                        {/* Done Button */}
                        <button
                            onClick={() => {
                                setActiveTab("home");
                            }}
                            className="bg-[#EF5A3A] text-white px-5 py-4.5 rounded-full text-lg font-bold shadow-md mt-6 w-full mb-8 hover:bg-orange-600 transition"
                        >
                            เสร็จสิ้น
                        </button>
                    </div>
                </motion.div>

                {/* Bottom Navigation */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

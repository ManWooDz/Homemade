import { useState } from "react";
import { ChevronLeft } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";

export default function CustomCookingPage({
    userIngredients,
    onBack,
    activeTab,
    setActiveTab,
    onGenerate,
}) {
    const OTHER_OPTION = "อื่นๆ";

    const TASTE_OPTIONS = [
        "ไม่ระบุ",
        "เผ็ดน้อย",
        "เผ็ดปานกลาง",
        "เผ็ดมาก",
        "รสจัดจ้าน",
        "รสหวานนำ",
        "รสเปรี้ยวนำ",
        "รสกลมกล่อม ไม่จัดจ้าน",
        OTHER_OPTION,
    ];
    const ALLERGY_NONE = "ไม่มี";
    const ALLERGY_OPTIONS = [
        ALLERGY_NONE,
        "กุ้ง/อาหารทะเล",
        "ถั่ว",
        "นม/ผลิตภัณฑ์จากนม",
        "ไข่",
        "แป้งสาลี/กลูเตน",
        "ถั่วเหลือง",
        "งา",
        OTHER_OPTION,
    ];
    const EQUIPMENT_NONE = "ไม่มีอุปกรณ์พิเศษ";
    const EQUIPMENT_OPTIONS = [
        EQUIPMENT_NONE,
        "ไมโครเวฟ",
        "หม้อทอดไร้น้ำมัน",
        "เตาอบ",
        "หม้อหุงข้าว",
        "กระทะ/เตาแก๊สทั่วไป",
        "หม้อตุ๋น/สโลว์คุก",
        "เครื่องปั่น",
        OTHER_OPTION,
    ];

    const [taste, setTaste] = useState("");
    const [tasteOther, setTasteOther] = useState("");
    const [allergies, setAllergies] = useState([]);
    const [allergiesOther, setAllergiesOther] = useState("");
    const [equipment, setEquipment] = useState([]);
    const [equipmentOther, setEquipmentOther] = useState("");
    const [extra, setExtra] = useState("");
    const [selectedIngredients, setSelectedIngredients] = useState([]);

    const toggleIngredient = (id) => {
        setSelectedIngredients((prev) =>
            prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
        );
    };

    // multi-select toggle where selecting `noneValue` clears every other
    // selection, and selecting anything else clears `noneValue`
    const toggleInList = (list, setList, option, noneValue) => {
        if (option === noneValue) {
            setList(list.includes(noneValue) ? [] : [noneValue]);
            return;
        }
        if (list.includes(option)) {
            setList(list.filter((item) => item !== option));
        } else {
            setList([...list.filter((item) => item !== noneValue), option]);
        }
    };

    const resolveOther = (value, otherText) =>
        value === OTHER_OPTION ? otherText.trim() || OTHER_OPTION : value;

    const resolveOtherInList = (list, otherText) =>
        list.map((item) => resolveOther(item, otherText));

    const handleGenerateClick = () => {
        const selectedObjs = userIngredients.filter((ing) =>
            selectedIngredients.includes(ing.id),
        );
        onGenerate(
            {
                taste: resolveOther(taste, tasteOther),
                allergies: resolveOtherInList(allergies, allergiesOther).join(", "),
                equipment: resolveOtherInList(equipment, equipmentOther).join(", "),
                extra,
            },
            selectedObjs,
        );
    };

    return (
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                {/* Header Actions */}
                <div className="pt-8 px-6 flex items-center justify-center relative z-20 mb-6">
                    <button
                        onClick={onBack}
                        className="absolute left-6 w-10 h-10 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md cursor-pointer"
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
                    <div className="mb-3 flex justify-center">
                        <h2 className="text-2xl font-bold text-gray-900 leading-tight">
                            Custom Cooking
                        </h2>
                    </div>

                    {/* Description Textarea */}
                    <div className="mb-8">
                        <div className="flex justify-between items-end mb-4">
                            <h3 className="text-lg font-bold text-black">
                                วัตถุดิบที่ต้องการใช้
                            </h3>
                            <span className="text-sm text-red-700">
                                เลือกอย่างน้อย 1 อย่าง
                            </span>
                        </div>
                        {/* Display Fridge Ingredients */}
                        {userIngredients && userIngredients.length > 0 ? (
                            <div className="flex flex-wrap gap-2 mb-6">
                                {userIngredients.map((ing) => {
                                    const isSelected =
                                        selectedIngredients.includes(ing.id);
                                    return (
                                        <div
                                            key={ing.id}
                                            onClick={() =>
                                                toggleIngredient(ing.id)
                                            }
                                            className={`px-3 py-1.5 rounded-full flex items-center gap-2 cursor-pointer transition-colors ${
                                                isSelected
                                                    ? "bg-orange-50 border border-[#EF5A3A]"
                                                    : "bg-gray-50 border border-gray-300 opacity-60 hover:bg-gray-100/80"
                                            }`}
                                        >
                                            <img
                                                src={ing.image}
                                                alt={ing.name}
                                                className="w-5 h-5 rounded-full object-cover"
                                                onError={(e) => {
                                                    e.target.src =
                                                        "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=150";
                                                }}
                                            />
                                            <span
                                                className={`text-sm font-medium ${
                                                    isSelected
                                                        ? "text-[#EF5A3A]"
                                                        : "text-gray-500"
                                                }`}
                                            >
                                                {ing.name}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="bg-gray-50 rounded-2xl p-4 text-center text-sm text-gray-500 mb-6">
                                ตู้เย็นของคุณว่างเปล่า
                                คุณสามารถไปเพิ่มวัตถุดิบได้ที่ My Fridge
                            </div>
                        )}

                        <h3 className="text-lg font-bold text-black mt-2 mb-2">
                            รสชาติ
                        </h3>
                        <div className="flex flex-wrap gap-2 mb-2">
                            {TASTE_OPTIONS.map((option) => (
                                <button
                                    key={option}
                                    type="button"
                                    onClick={() => setTaste(option)}
                                    className={`px-3 py-1.5 rounded-full text-sm font-medium border transition ${
                                        taste === option
                                            ? "bg-[#EF5A3A] border-[#EF5A3A] text-white shadow-sm"
                                            : "bg-white border-gray-400 text-gray-700 hover:border-[#EF5A3A] hover:text-[#EF5A3A]"
                                    }`}
                                >
                                    {option}
                                </button>
                            ))}
                        </div>
                        {taste === OTHER_OPTION && (
                            <input
                                type="text"
                                value={tasteOther}
                                onChange={(e) => setTasteOther(e.target.value)}
                                placeholder="ระบุรสชาติที่ต้องการ"
                                className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm transition-shadow mb-4 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
                            />
                        )}
                        {taste !== OTHER_OPTION && <div className="mb-2" />}

                        <h3 className="text-lg font-bold text-black mt-2 mb-2 flex items-baseline gap-2">
                            อาการแพ้อาหาร
                            <span className="text-xs font-normal text-gray-400">
                                เลือกได้มากกว่า 1 ข้อ
                            </span>
                        </h3>
                        <div className="flex flex-wrap gap-2 mb-2">
                            {ALLERGY_OPTIONS.map((option) => (
                                <button
                                    key={option}
                                    type="button"
                                    onClick={() =>
                                        toggleInList(allergies, setAllergies, option, ALLERGY_NONE)
                                    }
                                    className={`px-3 py-1.5 rounded-full text-sm font-medium border transition ${
                                        allergies.includes(option)
                                            ? "bg-[#EF5A3A] border-[#EF5A3A] text-white shadow-sm"
                                            : "bg-white border-gray-400 text-gray-700 hover:border-[#EF5A3A] hover:text-[#EF5A3A]"
                                    }`}
                                >
                                    {option}
                                </button>
                            ))}
                        </div>
                        {allergies.includes(OTHER_OPTION) && (
                            <input
                                type="text"
                                value={allergiesOther}
                                onChange={(e) => setAllergiesOther(e.target.value)}
                                placeholder="ระบุอาการแพ้อาหาร"
                                className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm transition-shadow mb-4 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
                            />
                        )}
                        {!allergies.includes(OTHER_OPTION) && <div className="mb-2" />}
                        <h3 className="text-lg font-bold text-black mt-2 mb-2 flex items-baseline gap-2">
                            อุปกรณ์ที่มี
                            <span className="text-xs font-normal text-gray-400">
                                เลือกได้มากกว่า 1 ข้อ
                            </span>
                        </h3>
                        <div className="flex flex-wrap gap-2 mb-2">
                            {EQUIPMENT_OPTIONS.map((option) => (
                                <button
                                    key={option}
                                    type="button"
                                    onClick={() =>
                                        toggleInList(equipment, setEquipment, option, EQUIPMENT_NONE)
                                    }
                                    className={`px-3 py-1.5 rounded-full text-sm font-medium border transition ${
                                        equipment.includes(option)
                                            ? "bg-[#EF5A3A] border-[#EF5A3A] text-white shadow-sm"
                                            : "bg-white border-gray-400 text-gray-700 hover:border-[#EF5A3A] hover:text-[#EF5A3A]"
                                    }`}
                                >
                                    {option}
                                </button>
                            ))}
                        </div>
                        {equipment.includes(OTHER_OPTION) && (
                            <input
                                type="text"
                                value={equipmentOther}
                                onChange={(e) => setEquipmentOther(e.target.value)}
                                placeholder="ระบุอุปกรณ์ที่มี"
                                className="w-full border border-gray-400 bg-white rounded-full px-5 py-2.5 text-black placeholder-gray-500 text-sm outline-none shadow-sm transition-shadow mb-4 focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40"
                            />
                        )}
                        <h3 className="text-lg font-bold text-black mt-2 mb-2">
                            ความต้องการอื่นๆ (ถ้ามี)
                        </h3>
                        <textarea
                            className="w-full h-40 border border-gray-400 bg-white rounded-3xl p-5 text-black placeholder-gray-500 text-base outline-none resize-none shadow-sm transition-shadow focus:border-[#EF5A3A] focus:ring-2 focus:ring-[#EF5A3A]/40 focus:shadow-[0_0_12px_rgba(239,90,58,0.5)]"
                            placeholder="เช่น สิ่งที่ต้องระวัง หรือ ลักษณะของเมนูที่อยากได้"
                            value={extra}
                            onChange={(e) => setExtra(e.target.value)}
                        ></textarea>
                    </div>

                    {/* Action Button */}
                    <button
                        onClick={handleGenerateClick}
                        disabled={selectedIngredients.length === 0}
                        className="w-full bg-[#EF5A3A] text-white py-4.5 rounded-full text-lg font-medium shadow-md flex items-center justify-center gap-2 hover:bg-orange-600 disabled:opacity-50 transition cursor-pointer"
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

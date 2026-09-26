import { useState } from "react";
import { ChevronLeft, Trash2 } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import NutritionBox from "../components/NutritionBox";
import { expiryBadgeLabel } from "../utils/expiry";
import { useAuth } from "../context/AuthContext";

export default function IngredientDetail({
    ingredient,
    userIngredients,
    setUserIngredients,
    onBack,
    onDeleted,
    activeTab,
    setActiveTab,
}) {
    const { apiFetch } = useAuth();
    const [isDeleting, setIsDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState("");

    if (!ingredient) {
        onBack();
        return null;
    }

    const badge = expiryBadgeLabel(ingredient.expiry_date);

    const handleDelete = async () => {
        if (!window.confirm(`ลบ "${ingredient.name}" ออกจาก My Fridge?`)) {
            return;
        }
        setIsDeleting(true);
        setDeleteError("");
        try {
            const response = await apiFetch(
                `/api/user-ingredients/${ingredient.id}`,
                { method: "DELETE" },
            );
            const result = await response.json();
            if (result.status === "success") {
                setUserIngredients(
                    userIngredients.filter((ing) => ing.id !== ingredient.id),
                );
                onDeleted();
            } else {
                setDeleteError(result.message || "ลบไม่สำเร็จ");
            }
        } catch (error) {
            setDeleteError("ลบไม่สำเร็จ ลองใหม่อีกครั้ง");
        } finally {
            setIsDeleting(false);
        }
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
                    {/* Image Preview */}
                    <div className="flex justify-center mb-6">
                        <div className="w-32 h-32 bg-gray-100 rounded-full overflow-hidden shadow-sm border-2 border-gray-200">
                            <img
                                src={
                                    ingredient.image ||
                                    "http://localhost:8000/images/No-image-available.png"
                                }
                                alt={ingredient.name}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                    e.target.src =
                                        "http://localhost:8000/images/No-image-available.png";
                                }}
                            />
                        </div>
                    </div>

                    <h2 className="text-2xl font-bold text-gray-900 text-center mb-6">
                        {ingredient.name}
                    </h2>

                    <div className="flex flex-col gap-4">
                        <div>
                            <h3 className="text-sm font-bold text-gray-700 mb-1">
                                Category
                            </h3>
                            <p className="text-base text-gray-800">
                                {ingredient.category}
                            </p>
                        </div>

                        <div>
                            <h3 className="text-sm font-bold text-gray-700 mb-1">
                                วันหมดอายุ (โดยประมาณ)
                            </h3>
                            {ingredient.expiry_date ? (
                                <p className="text-base text-gray-800">
                                    {ingredient.expiry_date}
                                    {badge && (
                                        <span className="ml-2 text-sm font-medium text-red-500">
                                            ({badge})
                                        </span>
                                    )}
                                </p>
                            ) : (
                                <p className="text-base text-gray-400">
                                    ไม่ได้ระบุ
                                </p>
                            )}
                        </div>

                        <NutritionBox nutrition={ingredient.nutrition_data} />
                    </div>

                    {deleteError && (
                        <p className="text-sm text-red-500 mt-4 text-center">
                            {deleteError}
                        </p>
                    )}

                    <button
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="w-full mt-8 flex items-center justify-center gap-2 border-2 border-red-200 text-red-500 py-4 rounded-full text-base font-bold hover:bg-red-50 transition disabled:opacity-50"
                    >
                        <Trash2 className="w-5 h-5" />
                        {isDeleting ? "กำลังลบ..." : "ลบออกจาก My Fridge"}
                    </button>
                </div>

                {/* === Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

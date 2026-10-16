import { useLocale } from "../context/LocaleContext";
import { useState, useRef } from "react";
import { ChevronLeft, Trash2, PenLine } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import NutritionBox from "../components/NutritionBox";
import IngredientEditor from "../components/IngredientEditor";
import { expiryBadgeLabel, sortByExpiry } from "../utils/expiry";
import { useAuth } from "../context/AuthContext";

export default function IngredientDetail({
    ingredient,
    userIngredients,
    setUserIngredients,
    onBack,
    onDeleted,
    onUpdated,
    activeTab,
    setActiveTab,
}) {
    const { t, locale } = useLocale();
    const { apiFetch } = useAuth();
    const [isDeleting, setIsDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState("");
    const [editing, setEditing] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const editButton = useRef(null);

    if (!ingredient) {
        onBack();
        return null;
    }

    const badge = expiryBadgeLabel(ingredient.expiry_date, locale);

    const handleDelete = async () => {
        if (!window.confirm(t('ลบ "{name}" ออกจากตู้เย็นของฉัน?', { name: ingredient.name }))) {
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
                setDeleteError("ลบไม่สำเร็จ ลองใหม่อีกครั้ง");
            }
        } catch {
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
                        disabled={isSaving}
                        aria-label={t("กลับ")}
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

                    {editing ? <IngredientEditor
                        ingredient={ingredient}
                        onBusyChange={setIsSaving}
                        onCancel={() => { setEditing(false); setDeleteError(""); requestAnimationFrame(() => editButton.current?.focus()); }}
                        onSaved={(updated) => {
                            setUserIngredients(items => sortByExpiry(items.map(item => item.id === updated.id ? { ...updated, selected: item.selected } : item)));
                            onUpdated(updated);
                            setEditing(false);
                            setSaved(true);
                            requestAnimationFrame(() => editButton.current?.focus());
                        }}
                    /> : <div className="flex flex-col gap-4">
                        <div>
                            <h3 className="text-sm font-bold text-gray-700 mb-1">{t("Category")}</h3>
                            <p className="text-base text-gray-800">
                                {t(ingredient.category)}
                            </p>
                        </div>

                        <div>
                            <h3 className="text-sm font-bold text-gray-700 mb-1">{t("วันหมดอายุ (โดยประมาณ)")}</h3>
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
                                <p className="text-base text-gray-400">{t("ไม่ได้ระบุ")}</p>
                            )}
                        </div>

                        <div>
                            <h3 className="text-sm font-bold text-gray-700 mb-1">{t("ปริมาณ")}</h3>
                            {ingredient.quantity_amount != null ? (
                                <p className="text-base text-gray-800">
                                    {ingredient.quantity_amount}
                                    {ingredient.quantity_unit
                                        ? ` ${t(ingredient.quantity_unit)}`
                                        : ""}
                                </p>
                            ) : (
                                <p className="text-base text-gray-400">{t("ไม่ได้ระบุ")}</p>
                            )}
                        </div>

                        <NutritionBox nutrition={ingredient.nutrition_data} />
                    </div>}

                    {saved && <p role="status" className="mt-4 text-sm text-gray-700">{t("บันทึกวัตถุดิบแล้ว")}</p>}
                    {!editing && <button
                        ref={editButton}
                        onClick={() => { setEditing(true); setSaved(false); setDeleteError(""); }}
                        disabled={isDeleting}
                        className="w-full mt-6 min-h-11 flex items-center justify-center gap-2 rounded-full bg-[#EF5A3A] text-white font-semibold disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-gray-900"
                    ><PenLine className="w-5 h-5" />{t("แก้ไขวัตถุดิบ")}</button>}

                    {deleteError && (
                        <p className="text-sm text-red-500 mt-4 text-center">
                            {t(deleteError)}
                        </p>
                    )}

                    {!editing && <button
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="w-full mt-8 flex items-center justify-center gap-2 border-2 border-red-200 text-red-500 py-4 rounded-full text-base font-bold hover:bg-red-50 transition disabled:opacity-50"
                    >
                        <Trash2 className="w-5 h-5" />
                        {isDeleting ? t("กำลังลบ...") : t("ลบออกจาก My Fridge")}
                    </button>}
                </div>

                {/* === Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={tab => { if (!isSaving) setActiveTab(tab); }} />
            </div>
        </div>
    );
}

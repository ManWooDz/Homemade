import PageShell from "../components/PageShell";
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
        <PageShell className="ingredient-detail-screen">

                {/* Header Actions */}
                <div className="shrink-0 pt-5 pb-6 px-6 flex items-center justify-center relative z-20">
                    <button
                        onClick={onBack}
                        disabled={isSaving}
                        aria-label={t("กลับ")}
                        className="absolute left-5 w-11 h-11 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center disabled:opacity-50"
                    >
                        <ChevronLeft className="w-6 h-6" />
                    </button>
                    <img
                        src={logo}
                        alt="HomeMade"
                        className="h-14 object-contain"
                    />
                </div>

                <main className="ingredient-detail-content flex-1 min-h-0 scrollbar-hide px-5 pb-6">
                    {/* Image Preview */}
                    <div className="flex items-center gap-5 mb-8">
                        <div className="w-24 h-24 shrink-0 bg-gray-100 rounded-full overflow-hidden">
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
                        <div className="min-w-0">
                            <h2 className="text-2xl leading-snug font-bold text-gray-900 wrap-anywhere">
                                {ingredient.name}
                            </h2>
                            <p className="mt-2 text-sm leading-relaxed text-gray-600">
                                <span className="block">{t("Category")}</span>
                                <span className="font-medium text-gray-900">{t(ingredient.category)}</span>
                            </p>
                        </div>
                    </div>

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
                    /> : <dl className="divide-y divide-gray-200 border-y border-gray-200">
                        <div className="flex items-start justify-between gap-4 py-4">
                            <dt className="text-sm leading-7 text-gray-600">{t("ปริมาณ")}</dt>
                            <dd className="min-w-0 text-right text-lg leading-7 font-semibold text-gray-900 wrap-anywhere">
                                {ingredient.quantity_amount != null ? (
                                    <span>
                                        {ingredient.quantity_amount}
                                        {ingredient.quantity_unit
                                            ? ` ${t(ingredient.quantity_unit)}`
                                            : ""}
                                    </span>
                                ) : (
                                    <span className="text-sm font-normal text-gray-600">{t("ไม่ได้ระบุ")}</span>
                                )}
                            </dd>
                        </div>
                        <div className="flex items-start justify-between gap-4 py-4">
                            <dt className="text-sm leading-7 text-gray-600">{t("วันหมดอายุ (โดยประมาณ)")}</dt>
                            <dd className="min-w-0 text-right leading-7 text-gray-900">
                                {ingredient.expiry_date ? <>
                                    <time dateTime={ingredient.expiry_date} className="font-medium tabular-nums">{ingredient.expiry_date}</time>
                                    {badge && <span className="block mt-1 text-sm leading-relaxed font-medium text-red-700">{badge}</span>}
                                </> : <span className="text-sm text-gray-600">{t("ไม่ได้ระบุ")}</span>}
                            </dd>
                        </div>
                    </dl>}

                    {saved && <p role="status" className="mt-4 text-sm text-gray-700">{t("บันทึกวัตถุดิบแล้ว")}</p>}
                    {!editing && <button
                        ref={editButton}
                        onClick={() => { setEditing(true); setSaved(false); setDeleteError(""); }}
                        disabled={isDeleting}
                        className="w-full mt-6 min-h-12 flex items-center justify-center gap-2 rounded-full bg-[#B93E25] text-white font-semibold hover:bg-[#9F351F] transition-colors disabled:opacity-50"
                    ><PenLine className="w-5 h-5" />{t("แก้ไขวัตถุดิบ")}</button>}

                    {!editing && ingredient.nutrition_data && <section className="mt-8" aria-label={t("Nutrition")}>
                        <NutritionBox nutrition={ingredient.nutrition_data} />
                    </section>}

                    {deleteError && (
                        <p role="alert" className="text-sm text-red-700 mt-4 text-center">
                            {t(deleteError)}
                        </p>
                    )}

                    {!editing && <button
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="w-full mt-6 min-h-11 flex items-center justify-center gap-2 rounded-full text-red-700 text-sm font-medium hover:bg-red-50 transition-colors disabled:opacity-50"
                    >
                        <Trash2 className="w-5 h-5" />
                        {isDeleting ? t("กำลังลบ...") : t("ลบออกจาก My Fridge")}
                    </button>}
                </main>

                {/* === Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={tab => { if (!isSaving) setActiveTab(tab); }} />

        </PageShell>
    );
}

import PageShell from "../components/PageShell";
import { useLocale } from "../context/LocaleContext";
import { useState, useEffect, useRef } from "react";
import { ChevronLeft, Search, Upload, Loader2 } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import NutritionBox from "../components/NutritionBox";
import AvatarCropper from "../components/AvatarCropper";
import { profileImageError, profileErrorKey } from "../utils/profileValidation";
import { toUserIngredientCreate } from "../utils/ingredientPayload";
import { sortByExpiry } from "../utils/expiry";
import { QUANTITY_UNITS, ENGLISH_QUANTITY_LABELS } from "../utils/quantityUnits";
import { useAuth } from "../context/AuthContext";

export default function AddIngredient({
    userIngredients,
    setUserIngredients,
    onBack,
    activeTab,
    setActiveTab,
    prefill,
}) {
    const { t, locale } = useLocale();
    const { apiFetch } = useAuth();
    const [name, setName] = useState(prefill?.name || "");
    const [category, setCategory] = useState(prefill?.category || "Meat & poultry");

    const [searchTerm, setSearchTerm] = useState("");
    const [searchResults, setSearchResults] = useState([]);
    const [isSearching, setIsSearching] = useState(false);
    const [searchError, setSearchError] = useState("");
    // Never start blank — an empty src is a real (pre-existing) latent bug:
    // saving before the fallback-image fetch below resolves would send
    // image: "" to the backend, which the browser then warns about when
    // later rendering <img src="">. Seed with the same static fallback path
    // the backend itself defaults to (UserIngredientCreate.image).
    const [selectedImage, setSelectedImage] = useState(
        prefill?.image || "http://localhost:8000/images/No-image-available.png",
    );
    const [isSaving, setIsSaving] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [expiryDate, setExpiryDate] = useState("");
    const [quantityAmount, setQuantityAmount] = useState("");
    const [quantityUnit, setQuantityUnit] = useState("");
    const [saveError, setSaveError] = useState("");
    const fileInputRef = useRef(null);
    const [cropSource, setCropSource] = useState("");
    const [uploadError, setUploadError] = useState("");
    const uploadRequest = useRef(null);
    const uploadButton = useRef(null);
    const previousCropSource = useRef("");

    useEffect(() => () => { if (cropSource) URL.revokeObjectURL(cropSource); }, [cropSource]);
    useEffect(() => () => uploadRequest.current?.abort(), []);
    useEffect(() => {
        if (cropSource) previousCropSource.current = cropSource;
        else if (!isUploading && previousCropSource.current) {
            uploadButton.current?.focus();
            previousCropSource.current = "";
        }
    }, [cropSource, isUploading]);

    const closeCrop = () => setCropSource("");

    const inputClass = "w-full min-w-0 min-h-12 bg-white border border-gray-300 rounded-xl px-4 py-3 text-base text-gray-900 placeholder:text-gray-500 focus:outline-2 focus:outline-[#B93E25]";

    const categories = ["Meat & poultry", "Vegetables", "Fruits", "Other"];

    useEffect(() => {
        const fetchFallback = async () => {
            try {
                const response = await fetch(
                    "/api/ingredient-images",
                );
                const result = await response.json();
                if (result.status === "success") {
                    // don't stomp an image already set from a barcode prefill
                    setSelectedImage((prev) => prev || result.data.fallback);
                }
            } catch (error) {
                console.error("Error fetching fallback image:", error);
            }
        };
        fetchFallback();
    }, []);

    // debounced online image search, keyed off the ingredient name
    useEffect(() => {
        const query = searchTerm.trim() || name.trim();
        if (!query) {
            setSearchResults([]);
            setSearchError("");
            return;
        }
        const timer = setTimeout(async () => {
            setIsSearching(true);
            setSearchError("");
            try {
                const response = await fetch(
                    `/api/ingredient-images/search?q=${encodeURIComponent(query)}`,
                );
                const result = await response.json();
                if (result.status === "success") {
                    setSearchResults(result.data.images);
                } else {
                    setSearchResults([]);
                    setSearchError("Search failed");
                }
            } catch {
                setSearchResults([]);
                setSearchError("Could not reach image search");
            } finally {
                setIsSearching(false);
            }
        }, 400);
        return () => clearTimeout(timer);
    }, [searchTerm, name]);

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        e.target.value = "";
        if (!file) return;
        const code = profileImageError(file);
        setUploadError(code ? profileErrorKey(code) : "");
        if (!code) setCropSource(URL.createObjectURL(file));
    };

    const uploadCrop = async (blob) => {
        if (uploadRequest.current) return;
        const controller = new AbortController();
        uploadRequest.current = controller;
        closeCrop();
        setIsUploading(true);
        setUploadError("");
        try {
            const formData = new FormData();
            formData.append("file", blob, "ingredient.jpg");
            const response = await fetch(
                "/api/ingredient-images/upload",
                { method: "POST", body: formData, signal: controller.signal },
            );
            const result = await response.json();
            if (controller.signal.aborted) return;
            if (response.ok && result.status === "success") {
                setSelectedImage(result.data.image);
            } else {
                setUploadError("Upload failed");
            }
        } catch {
            if (!controller.signal.aborted) setUploadError("Could not reach upload server");
        } finally {
            uploadRequest.current = null;
            if (!controller.signal.aborted) setIsUploading(false);
        }
    };

    const handleSave = async () => {
        if (!name.trim() || isSaving || isUploading || cropSource) return;
        setSaveError("");
        // Backend rejects amount <= 0 or > 100000 with a 422 that retrying
        // never fixes -- min="0" on the input still lets someone type 0,
        // so check before sending instead of showing a generic failure.
        const trimmedAmount = quantityAmount.trim();
        if (trimmedAmount !== "") {
            const parsed = Number(trimmedAmount);
            if (!(parsed > 0 && parsed <= 100000)) {
                setSaveError("ปริมาณต้องมากกว่า 0 และไม่เกิน 100,000");
                return;
            }
        }
        setIsSaving(true);
        try {
            const response = await apiFetch(
                "/api/user-ingredients",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(
                        toUserIngredientCreate({
                            name,
                            category,
                            image: selectedImage,
                            expiryDate,
                            nutritionData: prefill?.nutrition_data || null,
                            quantityAmount,
                            quantityUnit,
                        }),
                    ),
                },
            );
            const result = await response.json();
            if (result.status === "success") {
                // sorted here too — the list only gets re-fetched (and thus
                // re-sorted server-side) on page load, not on every append
                setUserIngredients(
                    sortByExpiry([...userIngredients, result.data]),
                );
                onBack(); // Return to previous screen (My Fridge)
            } else {
                console.error("Failed to add ingredient", result.message);
                setSaveError("บันทึกไม่สำเร็จ ลองใหม่อีกครั้ง");
            }
        } catch (error) {
            console.error("Error adding ingredient:", error);
            setSaveError("บันทึกไม่สำเร็จ ลองใหม่อีกครั้ง");
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <PageShell className="add-ingredient-screen">

                {/* Header Actions */}
                <div className="shrink-0 pt-5 pb-6 px-6 flex items-center justify-center relative z-20">
                    <button
                        onClick={cropSource ? closeCrop : onBack}
                        aria-label={t("กลับ")}
                        className="absolute left-5 w-11 h-11 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center"
                    >
                        <ChevronLeft className="w-6 h-6" />
                    </button>
                    <img
                        src={logo}
                        alt="HomeMade"
                        className="h-14 object-contain"
                    />
                </div>

                {cropSource && <AvatarCropper key={cropSource} source={cropSource} title="ครอปรูปวัตถุดิบ" imageLabel="รูปวัตถุดิบ" cropShape="rect" onCancel={closeCrop} onConfirm={uploadCrop} />}
                <main hidden={!!cropSource} className="flex-1 min-h-0 scrollbar-hide px-5 pb-6">
                    <div className="mb-6">
                        <h2 className="text-2xl font-bold text-gray-900">{t("Add Ingredient")}</h2>
                    </div>

                    <div className="flex flex-col gap-6">
                        {/* Image Picker */}
                        <section className="border-b border-gray-200 pb-6" aria-labelledby="ingredient-image-heading">
                            <div className="flex items-center gap-4 mb-4">
                                <div className="w-16 h-16 shrink-0 rounded-xl bg-gray-50 overflow-hidden">
                                    <img src={selectedImage} alt={t("Preview")} className="w-full h-full object-cover" />
                                </div>
                                <h3 id="ingredient-image-heading" className="text-lg font-bold text-gray-900">{t("Find an Image")}</h3>
                            </div>
                            <div className="relative mb-3">
                                <Search className="w-4 h-4 text-gray-400 absolute left-4 top-1/2 -translate-y-1/2" />
                                <input
                                    type="text"
                                    aria-labelledby="ingredient-image-heading"
                                    placeholder={
                                        name.trim()
                                            ? t('ค้นหารูป "{name}"...', { name: name.trim() })
                                            : t("Search online images...")
                                    }
                                    className={`${inputClass} pl-10`}
                                    value={searchTerm}
                                    onChange={(e) =>
                                        setSearchTerm(e.target.value)
                                    }
                                />
                            </div>

                            {isSearching && (
                                <div role="status" className="flex items-center gap-2 text-sm text-gray-600 py-2">
                                    <Loader2 className="w-4 h-4 animate-spin" />{t("Searching...")}</div>
                            )}

                            {!isSearching && searchError && (
                                <p role="alert" className="text-sm text-red-700 py-2">
                                    {t(searchError)}{t("— try uploading a photo instead.")}</p>
                            )}

                            {!isSearching &&
                                !searchError &&
                                searchResults.length === 0 && (
                                    <p className="text-sm leading-relaxed text-gray-600 py-2">{t("No results yet. Type an ingredient name to search, or upload your own.")}</p>
                                )}

                            {searchResults.length > 0 && (
                                <div className="grid grid-cols-4 gap-3 mb-1">
                                    {searchResults.map((img, idx) => (
                                        <button
                                            key={idx}
                                            disabled={isUploading || isSaving}
                                            aria-label={`${t("Ingredient option")} ${idx + 1}`}
                                            aria-pressed={selectedImage === img}
                                            onClick={() =>
                                                setSelectedImage(img)
                                            }
                                            className={`aspect-square min-w-0 rounded-xl overflow-hidden border-2 transition-colors ${selectedImage === img ? "border-[#B93E25] p-0.5" : "border-transparent"}`}
                                        >
                                            <div className="w-full h-full rounded-xl overflow-hidden">
                                                <img
                                                    src={img}
                                                    alt={t("Ingredient option")}
                                                    className="w-full h-full object-cover"
                                                />
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}

                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/jpeg,image/png,image/webp"
                                aria-label={t("เลือกรูป")}
                                className="hidden"
                                onChange={handleFileChange}
                            />
                            <button
                                ref={uploadButton}
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isUploading || isSaving}
                                className="w-full mt-3 min-h-12 flex items-center justify-center gap-2 border border-gray-300 text-gray-700 rounded-xl py-3 text-sm font-medium hover:border-[#B93E25] hover:text-[#B93E25] transition-colors disabled:opacity-50"
                            >
                                {isUploading ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />{t("Uploading...")}</>
                                ) : (
                                    <>
                                        <Upload className="w-4 h-4" />{t("Upload or Take Photo")}</>
                                )}
                            </button>
                            <p className="mt-2 text-sm text-gray-600">{t("JPG, PNG หรือ WebP ไม่เกิน 5 MB")}</p>
                            {uploadError && <p role="alert" className="mt-3 text-sm text-red-700">{t(uploadError)}</p>}
                        </section>

                        {/* Name Input */}
                        <div>
                            <label htmlFor="ingredient-name" className="block text-sm font-semibold text-gray-700 mb-2">{t("Ingredient Name")}</label>
                            <input
                                id="ingredient-name"
                                type="text"
                                placeholder={t("e.g. Eggs, Pork Belly...")}
                                className={inputClass}
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                            />
                        </div>

                        {/* Category Selection */}
                        <fieldset>
                            <legend className="text-sm font-semibold text-gray-700 mb-2">{t("Category")}</legend>
                            <div className="grid grid-cols-2 gap-3">
                                {categories.map((cat) => (
                                    <button
                                        key={cat}
                                        aria-pressed={category === cat}
                                        onClick={() => setCategory(cat)}
                                        className={`min-h-12 py-3 px-4 rounded-xl text-sm font-medium transition-colors ${
                                            category === cat
                                                ? "bg-[#FDECE5] text-[#9F351F] border border-[#B93E25]"
                                                : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
                                        }`}
                                    >
                                        {t(cat)}
                                    </button>
                                ))}
                            </div>
                        </fieldset>

                        {/* Quantity (optional) */}
                        <div>
                            <label htmlFor="ingredient-amount" className="block text-sm font-semibold text-gray-700 mb-2">{t("ปริมาณ (ไม่บังคับ)")}</label>
                            <div className="grid grid-cols-2 gap-3">
                                <input
                                    id="ingredient-amount"
                                    type="number"
                                    inputMode="decimal"
                                    step="any"
                                    min="0"
                                    placeholder={t("เช่น 2")}
                                    className={inputClass}
                                    value={quantityAmount}
                                    onChange={(e) => {
                                        const value = e.target.value;
                                        setQuantityAmount(value);
                                        // Backend rejects a unit with no
                                        // amount -- keep the UI from ever
                                        // reaching that state.
                                        if (!value.trim()) setQuantityUnit("");
                                    }}
                                />
                                <select
                                    aria-label={t("หน่วย")}
                                    value={quantityUnit}
                                    onChange={(e) =>
                                        setQuantityUnit(e.target.value)
                                    }
                                    className={inputClass}
                                >
                                    <option value="">{t("หน่วย")}</option>
                                    {QUANTITY_UNITS.map((unit) => (
                                        <option key={unit} value={unit}>
                                            {locale === "en" ? ENGLISH_QUANTITY_LABELS[unit] : t(unit)}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {/* Expiry Date (optional) */}
                        <div>
                            <label htmlFor="ingredient-expiry" className="block text-sm font-semibold text-gray-700 mb-2">{t("วันหมดอายุ (โดยประมาณ, ไม่บังคับ)")}</label>
                            <input
                                id="ingredient-expiry"
                                type="date"
                                className={inputClass}
                                value={expiryDate}
                                onChange={(e) => setExpiryDate(e.target.value)}
                            />
                        </div>

                        {/* Nutrition (read-only, from Open Food Facts scan) */}
                        <NutritionBox nutrition={prefill?.nutrition_data} />
                    </div>

                </main>

                <div hidden={!!cropSource} className="page-actions add-ingredient-actions shrink-0 border-t border-gray-200 bg-white px-5 pt-3 pb-4">
                    {saveError && (
                        <p role="alert" className="text-sm text-red-700 mb-3 leading-relaxed">
                            {t(saveError)}
                        </p>
                    )}

                    <button
                        onClick={handleSave}
                        disabled={!name.trim() || isSaving || isUploading}
                        className="w-full min-h-12 bg-[#B93E25] text-white py-3 px-4 rounded-full text-base font-semibold hover:bg-[#9F351F] disabled:opacity-50 transition-colors flex justify-center items-center"
                    >
                        {isSaving ? t("Saving...") : t("Add to My Fridge")}
                    </button>
                </div>

                {/* === Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />

        </PageShell>
    );
}

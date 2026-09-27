import { useState, useLayoutEffect, useRef } from "react";
import {
    ChevronLeft,
    ChevronRight,
    Plus,
    PenLine,
    ScanLine,
    Search,
    SlidersHorizontal,
    CalendarClock,
    TrendingUp,
    Type,
    Tag,
} from "lucide-react";
import { FaUtensils } from "react-icons/fa6";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import { expiryBadgeLabel, sortByExpiry } from "../utils/expiry";
import { normalizeForSearch } from "../utils/thaiText";

// value must match what AddIngredient.jsx / backend actually store
// ("Meat & poultry", lowercase p) -- label is just the mockup's display
// text. This chip previously compared against "Meat & Poultry" (capital
// P), so meat items never matched it; fixed here since this file already
// rewrites this exact filter.
const CATEGORY_CHIPS = [
    { label: "All Food", value: "All" },
    { label: "Meat & Poultry", value: "Meat & poultry" },
    { label: "Vegetables", value: "Vegetables" },
    { label: "Fruits", value: "Fruits" },
    { label: "Other", value: "Other" },
];

const SORT_OPTIONS = [
    { key: "expiry", label: "เรียงตามวันหมดอายุ", icon: CalendarClock },
    { key: "quantity", label: "ปริมาณ", icon: TrendingUp },
    { key: "alphabetical", label: "ตามตัวอักษร", icon: Type },
    { key: "category", label: "ประเภท", icon: Tag },
];
const DEFAULT_SORT = "expiry";

function applySort(items, sortBy) {
    switch (sortBy) {
        case "alphabetical":
            return [...items].sort(
                (a, b) => a.name.localeCompare(b.name, "th") || a.id - b.id,
            );
        case "category":
            // Stable sort (spec-guaranteed since ES2019) on top of the
            // expiry-ordered base keeps expiry order within each category
            // group, and inherits that base's id tiebreak for full
            // determinism without repeating it here.
            return sortByExpiry(items).sort((a, b) =>
                a.category.localeCompare(b.category, "th"),
            );
        case "quantity":
            // No real quantity data exists yet -- fridge_repository.py is
            // presence-only by design (quantity is always null/absent from
            // the API). Intentionally identical to "expiry" as a no-op
            // until a planned follow-up adds a real numeric quantity field
            // (the existing `quantity` column is legacy free text like
            // "12 pieces", not usable for numeric sorting as-is).
            return sortByExpiry(items);
        case "expiry":
        default:
            return sortByExpiry(items);
    }
}

export default function UserIngredients({
    userIngredients,
    onBack,
    activeTab,
    setActiveTab,
    onAddManually,
    onScanBarcode,
    onOpenIngredient,
}) {
    const [selectedCategory, setSelectedCategory] = useState("All");
    const [showAddMenu, setShowAddMenu] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [sortBy, setSortBy] = useState(DEFAULT_SORT);
    const [showSortSheet, setShowSortSheet] = useState(false);
    const [pendingSort, setPendingSort] = useState(DEFAULT_SORT);
    const [sheetTop, setSheetTop] = useState(0);
    const searchBarRef = useRef(null);
    const contentRef = useRef(null);

    useLayoutEffect(() => {
        if (showSortSheet && searchBarRef.current) {
            setSheetTop(
                searchBarRef.current.offsetTop + searchBarRef.current.offsetHeight,
            );
        }
    }, [showSortSheet]);

    const openSortSheet = () => {
        if (contentRef.current) contentRef.current.scrollTop = 0;
        setPendingSort(sortBy);
        setShowSortSheet(true);
    };

    const byCategory =
        selectedCategory === "All"
            ? userIngredients
            : userIngredients.filter(
                  (ing) => ing.category === selectedCategory,
              );

    const normalizedQuery = normalizeForSearch(searchQuery);
    const bySearch = normalizedQuery
        ? byCategory.filter((ing) =>
              normalizeForSearch(ing.name).includes(normalizedQuery),
          )
        : byCategory;

    const filteredIngredients = applySort(bySearch, sortBy);

    const hasAnyIngredients = userIngredients.length > 0;
    const hasActiveFilter = selectedCategory !== "All" || normalizedQuery !== "";
    const selectedCategoryLabel =
        CATEGORY_CHIPS.find((c) => c.value === selectedCategory)?.label ??
        selectedCategory;

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

                <div
                    ref={contentRef}
                    className="flex-1 overflow-y-auto pb-32"
                >
                    <div className="px-5 mb-4 flex items-center justify-between">
                        <h2 className="text-2xl font-bold text-gray-900">
                            My Fridge
                        </h2>
                        <span className="text-sm font-medium text-gray-500">
                            {userIngredients.length} Items
                        </span>
                    </div>

                    {/* Search + Sort filter */}
                    <div
                        ref={searchBarRef}
                        className="flex items-center gap-3 mb-4 px-5"
                    >
                        <div className="flex-1 flex items-center bg-white border border-gray-300 rounded-full px-4 py-2.5">
                            <Search className="w-4 h-4 text-gray-400 mr-2" />
                            <input
                                type="text"
                                placeholder="Search Ingredients..."
                                value={searchQuery}
                                onChange={(e) =>
                                    setSearchQuery(e.target.value)
                                }
                                className="w-full outline-none text-gray-700 bg-transparent text-sm"
                            />
                        </div>
                        <button
                            onClick={openSortSheet}
                            className="bg-[#EF5A3A] p-2.5 rounded-full text-white shadow-sm hover:bg-orange-600 transition shrink-0"
                        >
                            <SlidersHorizontal className="w-4 h-4" />
                        </button>
                    </div>

                    {/* Categories Strip */}
                    <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide mb-4 px-5">
                        {CATEGORY_CHIPS.map((chip) => (
                            <button
                                key={chip.value}
                                onClick={() => setSelectedCategory(chip.value)}
                                className={`px-5 py-2 rounded-full text-sm font-medium whitespace-nowrap shadow-sm transition ${
                                    selectedCategory === chip.value
                                        ? "bg-[#EF5A3A] text-white"
                                        : "bg-white border border-[#EF5A3A] text-[#EF5A3A] hover:bg-orange-50"
                                }`}
                            >
                                {chip.label}
                            </button>
                        ))}
                    </div>

                    {/* Ingredients List */}
                    <div className="flex flex-col gap-3 px-5">
                        {!hasAnyIngredients ? (
                            <div className="flex flex-col items-center text-center text-gray-400 mt-10">
                                <FaUtensils className="w-12 h-12 mb-3" />
                                <p>Add your ingredient to get started</p>
                            </div>
                        ) : filteredIngredients.length === 0 ? (
                            <div className="text-center text-gray-400 mt-10">
                                <p>
                                    {normalizedQuery
                                        ? "No ingredients match your search."
                                        : `No items found in '${selectedCategoryLabel}'.`}
                                </p>
                            </div>
                        ) : (
                            filteredIngredients.map((ing) => (
                                <button
                                    key={ing.id}
                                    onClick={() => onOpenIngredient(ing)}
                                    className="flex items-center justify-between bg-white border border-gray-100 p-3 rounded-2xl shadow-sm text-left hover:border-[#EF5A3A] transition"
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 bg-gray-50 rounded-full overflow-hidden shrink-0 border border-gray-100">
                                            <img
                                                src={
                                                    ing.image ||
                                                    "http://localhost:8000/images/No-image-available.png"
                                                }
                                                alt={ing.name}
                                                className="w-full h-full object-cover"
                                                onError={(e) => {
                                                    e.target.src =
                                                        "http://localhost:8000/images/No-image-available.png";
                                                }}
                                            />
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="font-semibold text-gray-800 text-lg leading-tight">
                                                {ing.name}
                                            </span>
                                            {expiryBadgeLabel(ing.expiry_date) && (
                                                <span className="text-xs font-medium text-red-500 mt-0.5">
                                                    {expiryBadgeLabel(ing.expiry_date)}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <ChevronRight className="w-5 h-5 text-gray-300" />
                                </button>
                            ))
                        )}
                    </div>
                </div>

                {/* Floating Action Button */}
                <button
                    onClick={() => setShowAddMenu(true)}
                    className="absolute bottom-28 right-6 w-14 h-14 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-lg hover:scale-105 transition-transform z-40"
                    style={{ boxShadow: "0 4px 20px rgba(0,0,0,0.3)" }}
                >
                    <Plus className="w-7 h-7" />
                </button>

                {/* Add-ingredient choice sheet */}
                {showAddMenu && (
                    <>
                        <div
                            className="absolute inset-0 bg-black/30 z-40"
                            onClick={() => setShowAddMenu(false)}
                        ></div>
                        <div className="absolute left-0 right-0 bottom-0 bg-white rounded-t-3xl shadow-[0_-10px_40px_rgba(0,0,0,0.1)] z-50 p-5 pb-28 flex flex-col gap-3">
                            <p className="text-sm font-bold text-gray-700 mb-1">
                                Add Ingredient
                            </p>
                            <button
                                onClick={() => {
                                    setShowAddMenu(false);
                                    onAddManually();
                                }}
                                className="w-full flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3.5 text-left hover:border-[#EF5A3A] transition"
                            >
                                <PenLine className="w-5 h-5 text-[#EF5A3A]" />
                                <span className="font-medium text-gray-800">
                                    Add Manually
                                </span>
                            </button>
                            <button
                                onClick={() => {
                                    setShowAddMenu(false);
                                    onScanBarcode();
                                }}
                                className="w-full flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3.5 text-left hover:border-[#EF5A3A] transition"
                            >
                                <ScanLine className="w-5 h-5 text-[#EF5A3A]" />
                                <span className="font-medium text-gray-800">
                                    Scan Barcode
                                </span>
                            </button>
                        </div>
                    </>
                )}

                {/* Sort sheet */}
                {showSortSheet && (
                    <>
                        <div
                            className="absolute inset-0 bg-black/30 z-40"
                            onClick={() => setShowSortSheet(false)}
                        ></div>
                        <div
                            className="absolute left-0 right-0 bottom-0 bg-white rounded-t-3xl shadow-[0_-10px_40px_rgba(0,0,0,0.1)] z-50 flex flex-col"
                            style={{ top: sheetTop }}
                        >
                            <p className="text-xs text-gray-400 font-medium px-5 pt-4 mb-2">
                                Sort By
                            </p>
                            <div className="flex-1 overflow-y-auto px-5">
                                {SORT_OPTIONS.map((opt) => {
                                    const Icon = opt.icon;
                                    const isSelected = pendingSort === opt.key;
                                    return (
                                        <button
                                            key={opt.key}
                                            onClick={() =>
                                                setPendingSort(opt.key)
                                            }
                                            className="w-full flex items-center justify-between py-3.5 border-b border-gray-100"
                                        >
                                            <span className="flex items-center gap-3 text-sm text-gray-700">
                                                <Icon className="w-4 h-4 text-gray-400" />
                                                {opt.label}
                                            </span>
                                            <span
                                                className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ${
                                                    isSelected
                                                        ? "border-[#EF5A3A]"
                                                        : "border-gray-300"
                                                }`}
                                            >
                                                {isSelected && (
                                                    <span className="w-2.5 h-2.5 rounded-full bg-[#EF5A3A]" />
                                                )}
                                            </span>
                                        </button>
                                    );
                                })}
                            </div>
                            <div className="flex items-center gap-3 px-5 py-4 pb-24 border-t border-gray-100">
                                <button
                                    onClick={() => setPendingSort(DEFAULT_SORT)}
                                    className="flex-1 py-3 rounded-full text-sm font-bold text-gray-600 border border-gray-300"
                                >
                                    Clear
                                </button>
                                <button
                                    onClick={() => {
                                        setSortBy(pendingSort);
                                        setShowSortSheet(false);
                                    }}
                                    className="flex-1 py-3 rounded-full text-sm font-bold text-white bg-[#EF5A3A] shadow-md hover:bg-orange-600 transition"
                                >
                                    Apply
                                </button>
                            </div>
                        </div>
                    </>
                )}

                {/* === Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

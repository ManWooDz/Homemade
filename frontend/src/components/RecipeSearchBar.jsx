import { Search, SlidersHorizontal } from "lucide-react";
import { useLocale } from "../context/LocaleContext";

export default function RecipeSearchBar({ value, onChange, onOpenFilters, filtersActive, filtersOpen, containerRef, placeholder = "Find the menu" }) {
    const { t } = useLocale();
    return (
        <div ref={containerRef} className="flex items-center gap-3 mb-6">
            <div className="min-w-0 flex-1 flex items-center bg-white border border-gray-400 rounded-full px-4 py-3 focus-within:border-[#B93E25]">
                <Search aria-hidden="true" className="w-5 h-5 shrink-0 text-gray-500 mr-2" />
                <input type="text" placeholder={t(placeholder)} aria-label={t(placeholder)} value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className="min-w-0 w-full outline-none text-gray-600 bg-transparent text-base" />
            </div>
            <button type="button" onClick={onOpenFilters} aria-label={t("Explore recipe by")}
                aria-expanded={filtersOpen} aria-controls="recipe-filter-panel"
                className="shrink-0 bg-[#EF5A3A] p-3 rounded-full text-white shadow-sm hover:bg-orange-600 transition relative focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]">
                <SlidersHorizontal aria-hidden="true" className="w-5 h-5" />
                {filtersActive && <span className="absolute -top-1 -right-1 w-3 h-3 bg-gray-900 rounded-full border-2 border-white" />}
            </button>
        </div>
    );
}

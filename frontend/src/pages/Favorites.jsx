import { useState } from "react";
import { ChevronLeft, Heart, Plus, Search } from "lucide-react";
import { BiSolidFoodMenu } from "react-icons/bi";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import { getTagColor } from "../utils/tagColors";

export default function Favorites({
    recipes,
    categories,
    favoriteRecipeIds,
    toggleFavorite,
    onBack,
    onSelectRecipe,
    activeTab,
    setActiveTab,
}) {
    const [selectedCategory, setSelectedCategory] = useState("All");
    const [searchQuery, setSearchQuery] = useState("");

    const allFavoriteRecipes = recipes.filter((recipe) =>
        favoriteRecipeIds.includes(recipe.id),
    );

    const categoryFilteredRecipes =
        selectedCategory === "All"
            ? allFavoriteRecipes
            : allFavoriteRecipes.filter((recipe) =>
                  recipe.tags && recipe.tags.includes(selectedCategory),
              );

    const favoriteRecipes = searchQuery.trim()
        ? categoryFilteredRecipes.filter((recipe) =>
              recipe.name
                  .toLowerCase()
                  .includes(searchQuery.trim().toLowerCase()),
          )
        : categoryFilteredRecipes;

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

                <div className="flex-1 overflow-y-auto pb-32">
                    <div className="px-5 mb-4 flex items-center justify-between">
                        <h2 className="text-2xl font-bold text-gray-900">
                            Favorites
                        </h2>
                        <span className="text-sm font-medium text-gray-500">
                            {favoriteRecipes.length} Items
                        </span>
                    </div>

                    {/* Search Bar */}
                    <div className="px-5 mb-4">
                        <div className="relative">
                            <Search className="w-4 h-4 text-gray-400 absolute left-4 top-1/2 -translate-y-1/2" />
                            <input
                                type="text"
                                placeholder="Search favorites..."
                                className="w-full bg-gray-50 border border-gray-300 rounded-2xl pl-10 pr-4 py-2.5 outline-none text-sm focus:border-[#EF5A3A] transition"
                                value={searchQuery}
                                onChange={(e) =>
                                    setSearchQuery(e.target.value)
                                }
                            />
                        </div>
                    </div>

                    {/* Categories Strip */}
                    <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide mb-4 px-5">
                        {categories.map((cat, index) => (
                            <button
                                key={index}
                                onClick={() => setSelectedCategory(cat)}
                                className={`px-5 py-2 rounded-full text-sm font-medium whitespace-nowrap shadow-sm transition ${
                                    selectedCategory === cat
                                        ? "bg-[#EF5A3A] text-white"
                                        : "bg-white border border-[#EF5A3A] text-[#EF5A3A] hover:bg-orange-50"
                                }`}
                            >
                                {cat}
                            </button>
                        ))}
                    </div>

                    {allFavoriteRecipes.length === 0 ? (
                        <div className="flex flex-col items-center text-center text-gray-400 mt-10">
                            <BiSolidFoodMenu className="w-12 h-12 mb-3" />
                            <p>Add your favorite menus to get started</p>
                            <button
                                onClick={onBack}
                                className="mt-4 px-5 py-2 rounded-full text-sm font-medium bg-[#EF5A3A] text-white shadow-sm hover:bg-[#d94f30] transition"
                            >
                                Discover new menu
                            </button>
                        </div>
                    ) : favoriteRecipes.length === 0 ? (
                        <div className="text-center text-gray-400 mt-10">
                            <p>No favorites found in '{selectedCategory}'.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 gap-4 px-5">
                            {favoriteRecipes.map((recipe) => (
                                <div
                                    key={recipe.id}
                                    className="bg-white border border-gray-100 rounded-3xl p-3 shadow-sm relative group cursor-pointer"
                                    onClick={() => onSelectRecipe(recipe)}
                                >
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            toggleFavorite(recipe.id);
                                        }}
                                        className="absolute top-4 right-4 text-red-500 hover:text-gray-300 z-10"
                                    >
                                        <Heart className="w-6 h-6 fill-current" />
                                    </button>
                                    <div className="w-full aspect-square bg-gray-100 rounded-full mb-3 overflow-hidden">
                                        <img
                                            src={recipe.image}
                                            alt={recipe.name}
                                            className="w-full h-full object-cover"
                                        />
                                    </div>
                                    <h4 className="font-bold text-gray-800 mb-2 truncate">
                                        {recipe.name}
                                    </h4>
                                    <div className="flex flex-col gap-1 mb-4">
                                        {recipe.tags &&
                                            recipe.tags
                                                .slice(0, 2)
                                                .map((tag, idx) => (
                                                    <span
                                                        key={idx}
                                                        className={`text-[10px] font-medium px-2 py-0.5 rounded-full w-max ${getTagColor(tag)}`}
                                                    >
                                                        {tag}
                                                    </span>
                                                ))}
                                    </div>
                                    <button className="absolute bottom-3 right-3 bg-gray-900 text-white p-2 rounded-full shadow-md">
                                        <Plus className="w-5 h-5" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* === Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

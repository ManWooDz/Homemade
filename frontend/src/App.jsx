import { useState, useEffect, useRef, useLayoutEffect, useMemo } from "react";
import {
    Home,
    Refrigerator,
    CookingPot,
    Heart,
    User,
    Search,
    SlidersHorizontal,
    Plus,
    X,
} from "lucide-react";
import logo from "./assets/HomeMade_Logo.png";
import BottomMenu from "./components/bottomMenu";
import RecipeDetail from "./pages/RecipeDetail";
import CreateRecipe from "./pages/CreateRecipe";
import CookingPage from "./pages/CookingPage";
import UserIngredients from "./pages/UserIngredients";
import CustomCookingPage from "./pages/CustomCookingPage";
import AddIngredient from "./pages/AddIngredient";
import Favorites from "./pages/Favorites";
import Profile from "./pages/Profile";
import { toPresenceIngredients } from "./utils/ingredientPayload";
import { getTagColor } from "./utils/tagColors";

function App() {

    const [activeTab, setActiveTab] = useState("home");
    const [currentView, setCurrentView] = useState("home"); // "home" | "recipe-detail" | "create-recipe" | "cooking-page" | "user-ingredients" | "custom-cooking"
    const [selectedIngredients, setSelectedIngredients] = useState([]);
    const [userIngredients, setUserIngredients] = useState([]);
    const [selectedRecipe, setSelectedRecipe] = useState(null);
    const [favoriteRecipeIds, setFavoriteRecipeIds] = useState([]);
    const [cookingHistory, setCookingHistory] = useState([]);

    const [recipes, setRecipes] = useState([]);
    const [categories, setCategories] = useState(["All"]);
    const [selectedCategory, setSelectedCategory] = useState("All");

    const [searchQuery, setSearchQuery] = useState("");
    const [showFilterPanel, setShowFilterPanel] = useState(false);
    const [filterTab, setFilterTab] = useState("ingredient");
    const [filterIngredientQuery, setFilterIngredientQuery] = useState("");
    const [selectedIngredientNames, setSelectedIngredientNames] = useState([]);
    const [selectedMealTypes, setSelectedMealTypes] = useState([]);
    const [selectedDietary, setSelectedDietary] = useState([]);
    const [selectedCuisine, setSelectedCuisine] = useState([]);
    const [selectedOccasion, setSelectedOccasion] = useState([]);
    const searchBarRef = useRef(null);
    const contentRef = useRef(null);
    const [filterPanelTop, setFilterPanelTop] = useState(0);

    const [generatedRecipe, setGeneratedRecipe] = useState(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [cookingSource, setCookingSource] = useState("create-recipe"); // "create-recipe" | "custom-cooking"

    useEffect(() => {
        const viewToFile = {
            home: "App.jsx",
            "recipe-detail": "RecipeDetail.jsx",
            "create-recipe": "CreateRecipe.jsx",
            "cooking-page": "CookingPage.jsx",
            "user-ingredients": "UserIngredients.jsx",
            "add-ingredient": "AddIngredient.jsx",
            "custom-cooking": "CustomCookingPage.jsx",
            favorites: "Favorites.jsx",
            profile: "Profile.jsx",
        };
        console.log("[PAGE]", viewToFile[currentView] ?? currentView);
    }, [currentView]);

    useEffect(() => {
        const fetchRecipes = async () => {
            try {
                const response = await fetch(
                    "http://localhost:8000/api/recipes",
                );
                const result = await response.json();
                if (result.status === "success") {
                    setRecipes(result.data);

                    const allTags = new Set(["All"]);
                    result.data.forEach((recipe) => {
                        if (recipe.tags && Array.isArray(recipe.tags)) {
                            recipe.tags.forEach((tag) => allTags.add(tag));
                        }
                    });
                    setCategories(Array.from(allTags));
                }
            } catch (error) {
                console.error("Error fetching recipes:", error);
            }
        };

        const fetchUserIngredients = async () => {
            try {
                const response = await fetch("http://localhost:8000/api/user-ingredients");
                const result = await response.json();
                if (result.status === "success") {
                    setUserIngredients(result.data);
                }
            } catch (error) {
                console.error("Error fetching user ingredients:", error);
            }
        };

        fetchRecipes();
        fetchUserIngredients();
    }, []);

    const FILTER_TABS = [
        { key: "ingredient", label: "Ingredient" },
        { key: "mealType", label: "Meal Type" },
        { key: "dietary", label: "Dietary" },
        { key: "cuisine", label: "Cuisine" },
        { key: "occasion", label: "Occasion" },
    ];
    const MEAL_TYPE_OPTIONS = ["Breakfast", "Brunch", "Lunch", "Dinner"];
    const DIETARY_OPTIONS = ["Vegetarian", "Vegan", "Glutan Free", "Low Carb"];
    const CUISINE_OPTIONS = ["British", "Thai", "Japan", "American"];
    const OCCASION_OPTIONS = ["Date Night", "Kid-Friendly", "Picnic"];
    const OPTION_EMOJI = {
        Breakfast: "🍳",
        Brunch: "🥐",
        Lunch: "🍱",
        Dinner: "🍽️",
        Vegetarian: "🥦",
        Vegan: "🌱",
        "Glutan Free": "🌾",
        "Low Carb": "🥑",
        British: "🇬🇧",
        Thai: "🇹🇭",
        Japan: "🇯🇵",
        American: "🇺🇸",
        "Date Night": "🌹",
        "Kid-Friendly": "🧒",
        Picnic: "🧺",
    };

    const filterCounts = {
        ingredient: selectedIngredientNames.length,
        mealType: selectedMealTypes.length,
        dietary: selectedDietary.length,
        cuisine: selectedCuisine.length,
        occasion: selectedOccasion.length,
    };

    const allIngredients = useMemo(() => {
        const map = new Map();
        recipes.forEach((recipe) => {
            (recipe.ingredients || []).forEach((ing) => {
                const key = (ing.name || "").toLowerCase().trim();
                if (key && !map.has(key)) {
                    map.set(key, { name: key, image: ing.image });
                }
            });
        });
        return Array.from(map.values());
    }, [recipes]);

    const visibleIngredients = allIngredients.filter((ing) =>
        ing.name.includes(filterIngredientQuery.trim().toLowerCase()),
    );
    const selectedIngredientObjs = allIngredients.filter((ing) =>
        selectedIngredientNames.includes(ing.name),
    );

    useLayoutEffect(() => {
        if (showFilterPanel && searchBarRef.current) {
            setFilterPanelTop(
                searchBarRef.current.offsetTop + searchBarRef.current.offsetHeight,
            );
        }
    }, [showFilterPanel]);

    const badgeRowRef = useRef(null);
    const badgeDrag = useRef({ isDown: false, startX: 0, scrollLeft: 0, moved: false });

    const handleBadgeMouseDown = (e) => {
        const el = badgeRowRef.current;
        if (!el) return;
        badgeDrag.current.isDown = true;
        badgeDrag.current.moved = false;
        badgeDrag.current.startX = e.pageX - el.offsetLeft;
        badgeDrag.current.scrollLeft = el.scrollLeft;
    };

    const handleBadgeMouseMove = (e) => {
        const el = badgeRowRef.current;
        if (!el || !badgeDrag.current.isDown) return;
        e.preventDefault();
        const x = e.pageX - el.offsetLeft;
        const walk = x - badgeDrag.current.startX;
        if (Math.abs(walk) > 5) badgeDrag.current.moved = true;
        el.scrollLeft = badgeDrag.current.scrollLeft - walk;
    };

    const stopBadgeDrag = () => {
        badgeDrag.current.isDown = false;
    };

    const handleFilterTabClick = (key) => {
        if (badgeDrag.current.moved) {
            badgeDrag.current.moved = false;
            return;
        }
        setFilterTab(key);
    };

    const toggleInList = (value, list, setList) => {
        setList(
            list.includes(value)
                ? list.filter((v) => v !== value)
                : [...list, value],
        );
    };

    const openFilterPanel = () => {
        if (contentRef.current) contentRef.current.scrollTop = 0;
        setShowFilterPanel(true);
    };

    const clearFilters = () => {
        setSelectedIngredientNames([]);
        setSelectedMealTypes([]);
        setSelectedDietary([]);
        setSelectedCuisine([]);
        setSelectedOccasion([]);
        setFilterIngredientQuery("");
    };

    const toggleFavorite = (recipeId) => {
        setFavoriteRecipeIds((prev) =>
            prev.includes(recipeId)
                ? prev.filter((id) => id !== recipeId)
                : [...prev, recipeId],
        );
    };

    const selectedTagFilters = [
        ...selectedMealTypes,
        ...selectedDietary,
        ...selectedCuisine,
        ...selectedOccasion,
    ].map((t) => t.toLowerCase());

    const filteredRecipes = recipes.filter((recipe) => {
        if (
            selectedCategory !== "All" &&
            !(recipe.tags && recipe.tags.includes(selectedCategory))
        )
            return false;

        const searchLower = searchQuery.trim().toLowerCase();
        if (searchLower && !recipe.name.toLowerCase().includes(searchLower))
            return false;

        if (selectedIngredientNames.length > 0) {
            const recipeIngNames = (recipe.ingredients || []).map((i) =>
                (i.name || "").toLowerCase(),
            );
            if (
                !selectedIngredientNames.some((n) =>
                    recipeIngNames.includes(n),
                )
            )
                return false;
        }

        if (selectedTagFilters.length > 0) {
            const recipeTagsLower = (recipe.tags || []).map((t) =>
                t.toLowerCase(),
            );
            if (!selectedTagFilters.some((t) => recipeTagsLower.includes(t)))
                return false;
        }

        return true;
    });

    const handleTabChange = (tab) => {
        setActiveTab(tab);
        if (tab === "home") {
            setCurrentView("home");
            setSelectedRecipe(null);
        } else if (tab === "fridge") {
            setCurrentView("user-ingredients");
        } else if (tab === "favorites") {
            setCurrentView("favorites");
        } else if (tab === "me") {
            setCurrentView("profile");
        } else if (tab === "cooking" && (currentView === "home" || currentView === "user-ingredients" || currentView === "add-ingredient")) {
            setSelectedRecipe(null);
            setCurrentView("custom-cooking");
        }
    };

    if (currentView === "recipe-detail") {
        return (
            <RecipeDetail
                recipe={selectedRecipe}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => {
                    setCurrentView("home");
                    setActiveTab("home");
                }}
                onConfirm={(ingredients) => {
                    setSelectedIngredients(ingredients);
                    setCurrentView("create-recipe");
                    setActiveTab("cooking");
                }}
            />
        );
    }

    if (currentView === "create-recipe") {
        return (
            <CreateRecipe
                recipe={selectedRecipe}
                selectedIngredients={selectedIngredients}
                userIngredients={userIngredients}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => setCurrentView("recipe-detail")}
                onGenerate={async (preferences, updatedIngredients) => {
                    setCurrentView("cooking-page");
                    setCookingSource("create-recipe");
                    setGeneratedRecipe(null);
                    setIsGenerating(true);
                    try {
                        const response = await fetch("http://localhost:8000/api/generate-recipe-text", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                recipe: selectedRecipe,
                                ingredients: toPresenceIngredients(
                                    updatedIngredients || selectedIngredients,
                                ),
                                preferences
                            })
                        });
                        const result = await response.json();
                        if (result.status === "success") {
                            setGeneratedRecipe(result.data);
                            setCookingHistory((prev) => [
                                {
                                    id: Date.now(),
                                    recipe_name: result.data.recipe_name,
                                    image: selectedRecipe?.image || null,
                                    diet_tags: result.data.diet_tags,
                                },
                                ...prev,
                            ]);
                        } else {
                            console.error("Failed to generate:", result.message);
                        }
                    } catch (err) {
                        console.error("Error generating recipe text:", err);
                    } finally {
                        setIsGenerating(false);
                    }
                }}
            />
        );
    }

    if (currentView === "cooking-page") {
        return (
            <CookingPage
                recipe={selectedRecipe}
                generatedRecipe={generatedRecipe}
                isGenerating={isGenerating}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => setCurrentView(cookingSource)}
                isCustom={cookingSource === "custom-cooking"}
            />
        );
    }

    if (currentView === "user-ingredients") {
        return (
            <UserIngredients
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                userIngredients={userIngredients}
                setUserIngredients={setUserIngredients}
                goToAddIngredient={() => setCurrentView("add-ingredient")}
                onBack={() => {
                    setCurrentView("home");
                    setActiveTab("home");
                }}
            />
        );
    }

    if (currentView === "favorites") {
        return (
            <Favorites
                recipes={recipes}
                categories={categories}
                favoriteRecipeIds={favoriteRecipeIds}
                toggleFavorite={toggleFavorite}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => {
                    setCurrentView("home");
                    setActiveTab("home");
                }}
                onSelectRecipe={(recipe) => {
                    setSelectedRecipe(recipe);
                    setActiveTab("cooking");
                    setCurrentView("recipe-detail");
                }}
            />
        );
    }

    if (currentView === "add-ingredient") {
        return (
            <AddIngredient
                userIngredients={userIngredients}
                setUserIngredients={setUserIngredients}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => setCurrentView("user-ingredients")}
            />
        );
    }

    if (currentView === "custom-cooking") {
        return (
            <CustomCookingPage
                userIngredients={userIngredients}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => {
                    setCurrentView("home");
                    setActiveTab("home");
                }}
                onGenerate={async (preferences, selectedIngredients) => {
                    setCurrentView("cooking-page");
                    setCookingSource("custom-cooking");
                    setGeneratedRecipe(null);
                    setIsGenerating(true);
                    try {
                        const response = await fetch("http://localhost:8000/api/generate-recipe-text", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                recipe: { name: "Custom Recipe from Fridge" },
                                ingredients: toPresenceIngredients(selectedIngredients),
                                preferences
                            })
                        });
                        const result = await response.json();
                        if (result.status === "success") {
                            setGeneratedRecipe(result.data);
                            setCookingHistory((prev) => [
                                {
                                    id: Date.now(),
                                    recipe_name: result.data.recipe_name,
                                    image: null,
                                    diet_tags: result.data.diet_tags,
                                },
                                ...prev,
                            ]);
                        } else {
                            console.error("Failed to generate:", result.message);
                        }
                    } catch (err) {
                        console.error("Error generating recipe text:", err);
                    } finally {
                        setIsGenerating(false);
                    }
                }}
            />
        );
    }

    if (currentView === "profile") {
        return (
            <Profile
                cookingHistory={cookingHistory}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => {
                    setCurrentView("home");
                    setActiveTab("home");
                }}
            />
        );
    }

    return (
        // พื้นหลังสีเทา เพื่อให้ตัวแอปสีขาวโดดเด่นขึ้นมา (เวลาเปิดบนคอม)
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            {/* 📱 กล่องแอปพลิเคชัน (จำกัดความกว้างเป็นทรงมือถือ) */}
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                {/* === เนื้อหาหลักของแอป (Content) === */}
                <div
                    ref={contentRef}
                    className="flex-1 overflow-y-auto pb-24 px-5 pt-8 scrollbar-hide"
                >
                    {/* Logo */}
                    <div className="flex justify-center mb-6">
                        <img
                            src={logo}
                            alt="HomeMade"
                            className="h-18 object-contain"
                        />
                    </div>

                    {/* Search Bar */}
                    <div ref={searchBarRef} className="flex items-center gap-3 mb-6">
                        <div className="flex-1 flex items-center bg-white border border-gray-400 rounded-full px-4 py-3">
                            <Search className="w-5 h-5 text-gray-500 mr-2" />
                            <input
                                type="text"
                                placeholder="Find the menu"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full outline-none text-gray-600 bg-transparent text-base"
                            />
                        </div>
                        <button
                            onClick={openFilterPanel}
                            className="bg-[#EF5A3A] p-3 rounded-full text-white shadow-sm hover:bg-orange-600 transition relative"
                        >
                            <SlidersHorizontal className="w-5 h-5" />
                            {Object.values(filterCounts).some((c) => c > 0) && (
                                <span className="absolute -top-1 -right-1 w-3 h-3 bg-gray-900 rounded-full border-2 border-white"></span>
                            )}
                        </button>
                    </div>

                    {/* Banner */}
                    <div className="w-full h-48 bg-black rounded-3xl mb-6 relative overflow-hidden shadow-sm flex items-center">
                        <img
                            src="https://images.unsplash.com/photo-1555939594-58d7cb561ad1?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
                            alt="Cooking Banner"
                            className="absolute inset-0 w-full h-full object-cover opacity-60"
                        />
                        <div className="absolute inset-0 bg-linear-to-r from-black/80 to-transparent z-0"></div>
                        <div className="relative z-10 text-white w-3/4 pl-6">
                            <h2 className="text-[34px] font-black italic text-white leading-none drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]">
                                TOP 10
                            </h2>
                            <h2 className="text-[34px] font-black italic text-yellow-400 leading-none drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]">
                                COOKING
                            </h2>
                            <h2 className="text-[34px] font-black italic text-yellow-400 leading-none drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]">
                                RECIPES
                            </h2>
                        </div>
                    </div>

                    {/* Categories */}
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-bold text-gray-900">
                            Categories
                        </h3>
                        <span className="text-[#EF5A3A] text-sm font-medium cursor-pointer">
                            See all
                        </span>
                    </div>
                    <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide mb-6 -mx-5 px-5">
                        {categories.map((category, index) => (
                            <button
                                key={index}
                                onClick={() => setSelectedCategory(category)}
                                className={`px-5 py-2 rounded-full text-sm font-medium whitespace-nowrap shadow-sm transition ${
                                    selectedCategory === category
                                        ? "bg-[#EF5A3A] text-white"
                                        : "bg-white border border-[#EF5A3A] text-[#EF5A3A] hover:bg-orange-50"
                                }`}
                            >
                                {category}
                            </button>
                        ))}
                    </div>

                    {/* Recipe Cards */}
                    <div className="grid grid-cols-2 gap-4">
                        {filteredRecipes.map((recipe) => (
                            <div
                                key={recipe.id}
                                className="bg-white border border-gray-100 rounded-3xl p-3 shadow-sm relative group cursor-pointer"
                                onClick={() => {
                                    setSelectedRecipe(recipe);
                                    setActiveTab("cooking");
                                    setCurrentView("recipe-detail");
                                }}
                            >
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        toggleFavorite(recipe.id);
                                    }}
                                    className={`absolute top-4 right-4 z-10 ${
                                        favoriteRecipeIds.includes(recipe.id)
                                            ? "text-red-500"
                                            : "text-gray-300 hover:text-red-500"
                                    }`}
                                >
                                    <Heart
                                        className={`w-6 h-6 ${favoriteRecipeIds.includes(recipe.id) ? "fill-current" : ""}`}
                                    />
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
                </div>

                {/* === Filter Panel === */}
                {showFilterPanel && (
                    <>
                        <div
                            className="absolute inset-0 bg-black/30 z-30"
                            onClick={() => setShowFilterPanel(false)}
                        ></div>
                        <div
                            className="absolute left-0 right-0 bottom-0 bg-white rounded-t-3xl shadow-[0_-10px_40px_rgba(0,0,0,0.1)] z-40 flex flex-col"
                            style={{ top: filterPanelTop }}
                        >
                            <p className="text-xs text-gray-400 font-medium px-5 pt-4">
                                Explore recipe by
                            </p>

                            {/* Tab badges */}
                            <div
                                ref={badgeRowRef}
                                onMouseDown={handleBadgeMouseDown}
                                onMouseMove={handleBadgeMouseMove}
                                onMouseUp={stopBadgeDrag}
                                onMouseLeave={stopBadgeDrag}
                                className="flex gap-2 overflow-x-auto scrollbar-hide px-5 py-3 cursor-grab active:cursor-grabbing select-none"
                            >
                                {FILTER_TABS.map((tab) => (
                                    <button
                                        key={tab.key}
                                        onClick={() => handleFilterTabClick(tab.key)}
                                        className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition ${
                                            filterTab === tab.key
                                                ? "bg-[#EF5A3A] text-white"
                                                : "bg-white border border-gray-300 text-gray-600"
                                        }`}
                                    >
                                        {tab.label}
                                        {filterCounts[tab.key] > 0 &&
                                            ` (${filterCounts[tab.key]})`}
                                    </button>
                                ))}
                            </div>

                            {/* Tab content */}
                            <div className="flex-1 overflow-y-auto px-5 pb-4 scrollbar-hide">
                                {filterTab === "ingredient" && (
                                    <>
                                        <div className="flex items-center bg-gray-100 rounded-full px-4 py-2.5 mb-4">
                                            <Search className="w-4 h-4 text-gray-400 mr-2" />
                                            <input
                                                type="text"
                                                placeholder="Search ingredient"
                                                value={filterIngredientQuery}
                                                onChange={(e) =>
                                                    setFilterIngredientQuery(
                                                        e.target.value,
                                                    )
                                                }
                                                className="w-full outline-none bg-transparent text-sm text-gray-600"
                                            />
                                        </div>

                                        {selectedIngredientObjs.length > 0 && (
                                            <div className="mb-4">
                                                <h4 className="text-sm font-bold text-gray-700 mb-2">
                                                    Selected
                                                </h4>
                                                <div className="grid grid-cols-4 gap-3">
                                                    {selectedIngredientObjs.map(
                                                        (ing) => (
                                                            <button
                                                                key={ing.name}
                                                                onClick={() =>
                                                                    toggleInList(
                                                                        ing.name,
                                                                        selectedIngredientNames,
                                                                        setSelectedIngredientNames,
                                                                    )
                                                                }
                                                                className="flex flex-col items-center gap-1"
                                                            >
                                                                <div className="relative w-14 h-14">
                                                                    <div className="w-14 h-14 rounded-full overflow-hidden bg-gray-100">
                                                                        <img
                                                                            src={
                                                                                ing.image
                                                                            }
                                                                            alt={
                                                                                ing.name
                                                                            }
                                                                            className="w-full h-full object-cover"
                                                                        />
                                                                    </div>
                                                                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-gray-900 text-white rounded-full flex items-center justify-center border-2 border-white">
                                                                        <X className="w-3 h-3" />
                                                                    </span>
                                                                </div>
                                                                <span className="text-[11px] text-gray-700 capitalize text-center truncate w-full">
                                                                    {ing.name}
                                                                </span>
                                                            </button>
                                                        ),
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        <h4 className="text-sm font-bold text-gray-700 mb-2">
                                            All Ingredient
                                        </h4>
                                        <div className="grid grid-cols-4 gap-3">
                                            {visibleIngredients.map((ing) => {
                                                const isSelected =
                                                    selectedIngredientNames.includes(
                                                        ing.name,
                                                    );
                                                return (
                                                    <button
                                                        key={ing.name}
                                                        onClick={() =>
                                                            toggleInList(
                                                                ing.name,
                                                                selectedIngredientNames,
                                                                setSelectedIngredientNames,
                                                            )
                                                        }
                                                        className="flex flex-col items-center gap-1"
                                                    >
                                                        <div
                                                            className={`w-14 h-14 rounded-full overflow-hidden bg-gray-100 ${
                                                                isSelected
                                                                    ? "opacity-40"
                                                                    : ""
                                                            }`}
                                                        >
                                                            <img
                                                                src={
                                                                    ing.image
                                                                }
                                                                alt={ing.name}
                                                                className="w-full h-full object-cover"
                                                            />
                                                        </div>
                                                        <span
                                                            className={`text-[11px] capitalize text-center truncate w-full ${
                                                                isSelected
                                                                    ? "text-gray-400"
                                                                    : "text-gray-700"
                                                            }`}
                                                        >
                                                            {ing.name}
                                                        </span>
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </>
                                )}

                                {filterTab === "mealType" && (
                                    <FilterCheckboxList
                                        emojiMap={OPTION_EMOJI}
                                        options={MEAL_TYPE_OPTIONS}
                                        selected={selectedMealTypes}
                                        onToggle={(v) =>
                                            toggleInList(
                                                v,
                                                selectedMealTypes,
                                                setSelectedMealTypes,
                                            )
                                        }
                                    />
                                )}

                                {filterTab === "dietary" && (
                                    <FilterCheckboxList
                                        emojiMap={OPTION_EMOJI}
                                        options={DIETARY_OPTIONS}
                                        selected={selectedDietary}
                                        onToggle={(v) =>
                                            toggleInList(
                                                v,
                                                selectedDietary,
                                                setSelectedDietary,
                                            )
                                        }
                                    />
                                )}

                                {filterTab === "cuisine" && (
                                    <FilterCheckboxList
                                        emojiMap={OPTION_EMOJI}
                                        options={CUISINE_OPTIONS}
                                        selected={selectedCuisine}
                                        onToggle={(v) =>
                                            toggleInList(
                                                v,
                                                selectedCuisine,
                                                setSelectedCuisine,
                                            )
                                        }
                                    />
                                )}

                                {filterTab === "occasion" && (
                                    <FilterCheckboxList
                                        emojiMap={OPTION_EMOJI}
                                        options={OCCASION_OPTIONS}
                                        selected={selectedOccasion}
                                        onToggle={(v) =>
                                            toggleInList(
                                                v,
                                                selectedOccasion,
                                                setSelectedOccasion,
                                            )
                                        }
                                    />
                                )}
                            </div>

                            {/* Clear / Apply */}
                            <div className="flex items-center gap-3 px-5 py-4 pb-24 border-t border-gray-100">
                                <button
                                    onClick={clearFilters}
                                    className="flex-1 py-3 rounded-full text-sm font-bold text-gray-600 border border-gray-300"
                                >
                                    Clear
                                </button>
                                <button
                                    onClick={() => setShowFilterPanel(false)}
                                    className="flex-1 py-3 rounded-full text-sm font-bold text-white bg-[#EF5A3A] shadow-md hover:bg-orange-600 transition"
                                >
                                    Apply
                                </button>
                            </div>
                        </div>
                    </>
                )}

                {/* === 🔘 Bottom Navigation (แถบเมนูด้านล่าง) === */}
                <BottomMenu
                    activeTab={activeTab}
                    setActiveTab={handleTabChange}
                />
            </div>
        </div>
    );
}

function FilterCheckboxList({ options, selected, onToggle, emojiMap }) {
    return (
        <div className="flex flex-col gap-3">
            {options.map((option) => {
                const isChecked = selected.includes(option);
                return (
                    <div
                        key={option}
                        onClick={() => onToggle(option)}
                        className="flex items-center justify-between bg-gray-100 p-3 rounded-2xl cursor-pointer"
                    >
                        <span className="font-medium text-black text-[15px]">
                            {emojiMap?.[option] && (
                                <span className="mr-2">{emojiMap[option]}</span>
                            )}
                            {option}
                        </span>
                        <div
                            className={`w-6 h-6 rounded flex items-center justify-center transition-colors ${
                                isChecked
                                    ? "bg-gray-800"
                                    : "bg-white border-2 border-gray-300"
                            }`}
                        >
                            {isChecked && (
                                <svg
                                    className="w-4 h-4 text-white"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth="3"
                                        d="M5 13l4 4L19 7"
                                    />
                                </svg>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

export default App;

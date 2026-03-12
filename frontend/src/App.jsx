import { useState, useEffect } from "react";
import {
    Home,
    Refrigerator,
    CookingPot,
    Heart,
    User,
    Search,
    SlidersHorizontal,
    Plus,
} from "lucide-react";
import logo from "./assets/HomeMade_Logo.png";
import BottomMenu from "./components/bottomMenu";
import RecipeDetail from "./pages/RecipeDetail";
import CreateRecipe from "./pages/CreateRecipe";
import CookingPage from "./pages/CookingPage";

function App() {
    const [activeTab, setActiveTab] = useState("home");
    const [currentView, setCurrentView] = useState("home"); // "home" | "recipe-detail" | "create-recipe" | "cooking-page"
    const [selectedIngredients, setSelectedIngredients] = useState([]);
    const [selectedRecipe, setSelectedRecipe] = useState(null);

    const [recipes, setRecipes] = useState([]);
    const [categories, setCategories] = useState(["All"]);
    const [selectedCategory, setSelectedCategory] = useState("All");
    
    const [generatedRecipe, setGeneratedRecipe] = useState(null);
    const [isGenerating, setIsGenerating] = useState(false);

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
        fetchRecipes();
    }, []);

    const filteredRecipes =
        selectedCategory === "All"
            ? recipes
            : recipes.filter(
                  (recipe) =>
                      recipe.tags && recipe.tags.includes(selectedCategory),
              );

    const handleTabChange = (tab) => {
        setActiveTab(tab);
        if (tab === "home") {
            setCurrentView("home");
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
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => setCurrentView("recipe-detail")}
                onGenerate={async (preferences) => {
                    setCurrentView("cooking-page");
                    setIsGenerating(true);
                    try {
                        const response = await fetch("http://localhost:8000/api/generate-recipe-text", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                recipe: selectedRecipe,
                                ingredients: selectedIngredients,
                                preferences
                            })
                        });
                        const result = await response.json();
                        if (result.status === "success") {
                            setGeneratedRecipe(result.data);
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
                onBack={() => setCurrentView("create-recipe")}
            />
        );
    }

    return (
        // พื้นหลังสีเทา เพื่อให้ตัวแอปสีขาวโดดเด่นขึ้นมา (เวลาเปิดบนคอม)
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            {/* 📱 กล่องแอปพลิเคชัน (จำกัดความกว้างเป็นทรงมือถือ) */}
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                {/* === เนื้อหาหลักของแอป (Content) === */}
                <div className="flex-1 overflow-y-auto pb-24 px-5 pt-8">
                    {/* Logo */}
                    <div className="flex justify-center mb-6">
                        <img
                            src={logo}
                            alt="HomeMade"
                            className="h-18 object-contain"
                        />
                    </div>

                    {/* Search Bar */}
                    <div className="flex items-center gap-3 mb-6">
                        <div className="flex-1 flex items-center bg-white border border-gray-400 rounded-full px-4 py-3">
                            <Search className="w-5 h-5 text-gray-500 mr-2" />
                            <input
                                type="text"
                                placeholder="Find the menu"
                                className="w-full outline-none text-gray-600 bg-transparent text-base"
                            />
                        </div>
                        <button className="bg-[#EF5A3A] p-3 rounded-full text-white shadow-sm hover:bg-orange-600 transition">
                            <SlidersHorizontal className="w-5 h-5" />
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
                                <button className="absolute top-4 right-4 text-gray-300 hover:text-red-500 z-10">
                                    <Heart className="w-6 h-6" />
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
                                                    className={`text-[10px] font-medium px-2 py-0.5 rounded-full w-max ${
                                                        idx === 0
                                                            ? "bg-green-100 text-green-700"
                                                            : "bg-yellow-100 text-yellow-700"
                                                    }`}
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

                {/* === 🔘 Bottom Navigation (แถบเมนูด้านล่าง) === */}
                <BottomMenu
                    activeTab={activeTab}
                    setActiveTab={handleTabChange}
                />
            </div>
        </div>
    );
}

export default App;

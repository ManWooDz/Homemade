import { useState, useEffect, useRef } from "react";
import { ChevronLeft, Plus, Search, Upload, Loader2 } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import { toUserIngredientCreate } from "../utils/ingredientPayload";

export default function AddIngredient({
    userIngredients,
    setUserIngredients,
    onBack,
    activeTab,
    setActiveTab,
}) {
    const [name, setName] = useState("");
    const [category, setCategory] = useState("Meat & poultry");

    const [searchTerm, setSearchTerm] = useState("");
    const [searchResults, setSearchResults] = useState([]);
    const [isSearching, setIsSearching] = useState(false);
    const [searchError, setSearchError] = useState("");
    const [fallbackImage, setFallbackImage] = useState("");
    const [selectedImage, setSelectedImage] = useState("");
    const [isSaving, setIsSaving] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef(null);

    const categories = ["Meat & poultry", "Vegetables", "Fruits", "Other"];

    useEffect(() => {
        const fetchFallback = async () => {
            try {
                const response = await fetch(
                    "http://localhost:8000/api/ingredient-images",
                );
                const result = await response.json();
                if (result.status === "success") {
                    setFallbackImage(result.data.fallback);
                    setSelectedImage(result.data.fallback); // default
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
                    `http://localhost:8000/api/ingredient-images/search?q=${encodeURIComponent(query)}`,
                );
                const result = await response.json();
                if (result.status === "success") {
                    setSearchResults(result.data.images);
                } else {
                    setSearchResults([]);
                    setSearchError(result.message || "Search failed");
                }
            } catch (error) {
                setSearchResults([]);
                setSearchError("Could not reach image search");
            } finally {
                setIsSearching(false);
            }
        }, 400);
        return () => clearTimeout(timer);
    }, [searchTerm, name]);

    const handleFileChange = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setIsUploading(true);
        setSearchError("");
        try {
            const formData = new FormData();
            formData.append("file", file);
            const response = await fetch(
                "http://localhost:8000/api/ingredient-images/upload",
                { method: "POST", body: formData },
            );
            const result = await response.json();
            if (result.status === "success") {
                setSelectedImage(result.data.image);
            } else {
                setSearchError(result.message || "Upload failed");
            }
        } catch (error) {
            setSearchError("Could not reach upload server");
        } finally {
            setIsUploading(false);
            e.target.value = "";
        }
    };

    const handleSave = async () => {
        if (!name.trim()) return;
        setIsSaving(true);
        try {
            const response = await fetch(
                "http://localhost:8000/api/user-ingredients",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(
                        toUserIngredientCreate({
                            name,
                            category,
                            image: selectedImage,
                        }),
                    ),
                },
            );
            const result = await response.json();
            if (result.status === "success") {
                setUserIngredients([...userIngredients, result.data]);
                onBack(); // Return to previous screen (My Fridge)
            } else {
                console.error("Failed to add ingredient", result.message);
            }
        } catch (error) {
            console.error("Error adding ingredient:", error);
        } finally {
            setIsSaving(false);
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
                    <div className="mb-6">
                        <h2 className="text-2xl font-bold text-gray-900">
                            Add Ingredient
                        </h2>
                    </div>

                    {/* Selected Image Preview */}
                    <div className="flex justify-center mb-6">
                        <div className="w-32 h-32 bg-gray-100 rounded-full overflow-hidden shadow-sm border-2 border-gray-200">
                            {selectedImage && (
                                <img
                                    src={selectedImage}
                                    alt="Preview"
                                    className="w-full h-full object-cover"
                                />
                            )}
                        </div>
                    </div>

                    <div className="flex flex-col gap-6">
                        {/* Name Input */}
                        <div>
                            <h3 className="text-sm font-bold text-gray-700 mb-2">
                                Ingredient Name
                            </h3>
                            <input
                                type="text"
                                placeholder="e.g. Eggs, Pork Belly..."
                                className="w-full bg-gray-50 border border-gray-300 rounded-2xl px-4 py-3 outline-none text-base focus:border-[#EF5A3A] transition"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                            />
                        </div>

                        {/* Image Picker */}
                        <div>
                            <h3 className="text-sm font-bold text-gray-700 mb-2">
                                Find an Image
                            </h3>
                            <div className="relative mb-3">
                                <Search className="w-4 h-4 text-gray-400 absolute left-4 top-1/2 -translate-y-1/2" />
                                <input
                                    type="text"
                                    placeholder={
                                        name.trim()
                                            ? `Search "${name.trim()}"...`
                                            : "Search online images..."
                                    }
                                    className="w-full bg-gray-50 border border-gray-300 rounded-2xl pl-10 pr-4 py-2.5 outline-none text-sm focus:border-[#EF5A3A] transition"
                                    value={searchTerm}
                                    onChange={(e) =>
                                        setSearchTerm(e.target.value)
                                    }
                                />
                            </div>

                            {isSearching && (
                                <div className="flex items-center gap-2 text-sm text-gray-400 py-2">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Searching...
                                </div>
                            )}

                            {!isSearching && searchError && (
                                <p className="text-sm text-red-500 py-2">
                                    {searchError} — try uploading a photo
                                    instead.
                                </p>
                            )}

                            {!isSearching &&
                                !searchError &&
                                searchResults.length === 0 && (
                                    <p className="text-sm text-gray-400 py-2">
                                        No results yet. Type an ingredient
                                        name to search, or upload your own.
                                    </p>
                                )}

                            {searchResults.length > 0 && (
                                <div className="grid grid-cols-4 gap-3 mb-1">
                                    {searchResults.map((img, idx) => (
                                        <button
                                            key={idx}
                                            onClick={() =>
                                                setSelectedImage(img)
                                            }
                                            className={`aspect-square rounded-2xl overflow-hidden border-2 transition ${selectedImage === img ? "border-[#EF5A3A] p-0.5" : "border-transparent shadow-sm"}`}
                                        >
                                            <div className="w-full h-full rounded-xl overflow-hidden">
                                                <img
                                                    src={img}
                                                    alt="Ingredient option"
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
                                accept="image/*"
                                capture="environment"
                                className="hidden"
                                onChange={handleFileChange}
                            />
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isUploading}
                                className="w-full mt-3 flex items-center justify-center gap-2 border-2 border-dashed border-gray-300 text-gray-500 rounded-2xl py-3 text-sm font-medium hover:border-[#EF5A3A] hover:text-[#EF5A3A] transition disabled:opacity-50"
                            >
                                {isUploading ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Uploading...
                                    </>
                                ) : (
                                    <>
                                        <Upload className="w-4 h-4" />
                                        Upload or Take Photo
                                    </>
                                )}
                            </button>
                        </div>

                        {/* Category Selection */}
                        <div>
                            <h3 className="text-sm font-bold text-gray-700 mb-2">
                                Category
                            </h3>
                            <div className="grid grid-cols-2 gap-3">
                                {categories.map((cat) => (
                                    <button
                                        key={cat}
                                        onClick={() => setCategory(cat)}
                                        className={`py-3 px-4 rounded-xl text-sm font-medium transition ${
                                            category === cat
                                                ? "bg-[#EF5A3A] text-white shadow-md"
                                                : "bg-white border border-gray-300 text-gray-600 hover:bg-gray-50"
                                        }`}
                                    >
                                        {cat}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <button
                        onClick={handleSave}
                        disabled={!name.trim() || isSaving}
                        className="w-full mt-8 bg-[#EF5A3A] text-white py-4 rounded-full text-lg font-bold shadow-md hover:bg-orange-600 disabled:opacity-50 transition flex justify-center items-center"
                    >
                        {isSaving ? "Saving..." : "Add to My Fridge"}
                    </button>
                </div>

                {/* === Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

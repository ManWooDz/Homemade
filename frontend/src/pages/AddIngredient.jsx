import { useState, useEffect } from "react";
import { ChevronLeft, Plus } from "lucide-react";
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

    const [availableImages, setAvailableImages] = useState([]);
    const [fallbackImage, setFallbackImage] = useState("");
    const [selectedImage, setSelectedImage] = useState("");
    const [isSaving, setIsSaving] = useState(false);

    const categories = ["Meat & poultry", "Vegetables", "Fruits", "Other"];

    useEffect(() => {
        const fetchImages = async () => {
            try {
                const response = await fetch(
                    "http://localhost:8000/api/ingredient-images",
                );
                const result = await response.json();
                if (result.status === "success") {
                    setAvailableImages(result.data.images);
                    setFallbackImage(result.data.fallback);
                    setSelectedImage(result.data.fallback); // default
                }
            } catch (error) {
                console.error("Error fetching images:", error);
            }
        };
        fetchImages();
    }, []);

    const filteredImages = availableImages.filter((img) => {
        if (!name.trim()) return true;
        const searchTerm = name.toLowerCase().trim();
        const filename = img.split("/").pop().toLowerCase();
        return filename.includes(searchTerm);
    });

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
                        <p className="text-sm text-gray-500 mt-1">
                            Fill in the details for your new ingredient.
                        </p>
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

                        {/* Selected Image Preview */}
                        <div className="flex justify-center mb-2">
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

                        {/* Image Picker */}
                        <div>
                            <h3 className="text-sm font-bold text-gray-700 mb-2">
                                Choose an Image
                            </h3>
                            <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide py-1">
                                {/* Fallback Option */}
                                <button
                                    onClick={() =>
                                        setSelectedImage(fallbackImage)
                                    }
                                    className={`w-14 h-14 shrink-0 rounded-2xl overflow-hidden border-2 transition ${selectedImage === fallbackImage ? "border-[#EF5A3A] p-0.5" : "border-transparent"}`}
                                >
                                    <div className="w-full h-full bg-gray-200 flex items-center justify-center rounded-xl overflow-hidden">
                                        <img
                                            src={fallbackImage}
                                            alt="None"
                                            className="w-full h-full object-cover opacity-60"
                                        />
                                    </div>
                                </button>

                                {filteredImages.map((img, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => setSelectedImage(img)}
                                        className={`w-14 h-14 shrink-0 rounded-2xl overflow-hidden border-2 transition ${selectedImage === img ? "border-[#EF5A3A] p-0.5" : "border-transparent shadow-sm"}`}
                                    >
                                        <div className="w-full h-full rounded-xl overflow-hidden">
                                            <img
                                                src={img}
                                                alt="Ingredient"
                                                className="w-full h-full object-cover"
                                            />
                                        </div>
                                    </button>
                                ))}
                            </div>
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

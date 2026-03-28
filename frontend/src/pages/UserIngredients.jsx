import { useState } from "react";
import { ChevronLeft, Trash2, Plus } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";

export default function UserIngredients({ userIngredients, setUserIngredients, onBack, activeTab, setActiveTab }) {
    const [newIngredient, setNewIngredient] = useState("");
    const [isAdding, setIsAdding] = useState(false);

    const handleAddIngredient = async () => {
        if (!newIngredient.trim()) return;
        setIsAdding(true);
        try {
            const response = await fetch("http://localhost:8000/api/user-ingredients", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: newIngredient })
            });
            const result = await response.json();
            if (result.status === "success") {
                setUserIngredients([...userIngredients, result.data]);
                setNewIngredient("");
            } else {
                console.error("Failed to add ingredient", result.message);
            }
        } catch (error) {
            console.error("Error adding ingredient:", error);
        } finally {
            setIsAdding(false);
        }
    };

    const handleDeleteIngredient = async (id) => {
        try {
            const response = await fetch(`http://localhost:8000/api/user-ingredients/${id}`, {
                method: "DELETE"
            });
            const result = await response.json();
            if (result.status === "success") {
                setUserIngredients(userIngredients.filter(ing => ing.id !== id));
            } else {
                console.error("Failed to delete ingredient", result.message);
            }
        } catch (error) {
            console.error("Error deleting ingredient:", error);
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
                    <div className="mb-6 flex items-center justify-between">
                        <h2 className="text-2xl font-bold text-gray-900">My Fridge</h2>
                        <span className="text-sm font-medium text-gray-500">{userIngredients.length} Items</span>
                    </div>

                    {/* Add New Ingredient */}
                    <div className="bg-gray-50 border border-gray-200 rounded-3xl p-4 mb-8 shadow-sm">
                        <div className="flex gap-2">
                            <input
                                type="text"
                                placeholder="Add an ingredient (e.g. Eggs, Milk...)"
                                className="flex-1 bg-white border border-gray-300 rounded-full px-4 py-3 outline-none text-base"
                                value={newIngredient}
                                onChange={(e) => setNewIngredient(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleAddIngredient()}
                            />
                            <button 
                                onClick={handleAddIngredient}
                                disabled={isAdding || !newIngredient.trim()}
                                className="bg-[#EF5A3A] text-white w-12 h-12 rounded-full flex items-center justify-center shadow-md hover:bg-orange-600 disabled:opacity-50 transition"
                            >
                                <Plus className="w-6 h-6" />
                            </button>
                        </div>
                    </div>

                    {/* Ingredients List */}
                    <div className="flex flex-col gap-3">
                        {userIngredients.length === 0 ? (
                            <div className="text-center text-gray-400 mt-10">
                                <p>Your fridge is empty.</p>
                                <p className="text-sm">Add some ingredients above!</p>
                            </div>
                        ) : (
                            userIngredients.map((ing) => (
                                <div key={ing.id} className="flex items-center justify-between bg-white border border-gray-100 p-3 rounded-2xl shadow-sm">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 bg-gray-50 rounded-full overflow-hidden shrink-0 border border-gray-100">
                                            <img
                                                src={ing.image}
                                                alt={ing.name}
                                                className="w-full h-full object-cover"
                                                onError={(e) => {
                                                    // fallback image
                                                    e.target.src = "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=150";
                                                }}
                                            />
                                        </div>
                                        <span className="font-semibold text-gray-800 text-lg">
                                            {ing.name}
                                        </span>
                                    </div>
                                    <button 
                                        onClick={() => handleDeleteIngredient(ing.id)}
                                        className="w-10 h-10 flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-full transition"
                                    >
                                        <Trash2 className="w-5 h-5" />
                                    </button>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* === Bottom Navigation === */}
                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

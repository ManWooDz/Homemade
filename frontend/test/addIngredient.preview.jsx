// Development-only: all requests are intercepted; no account or inventory is modified.
import { useState } from "react";
import { createRoot } from "react-dom/client";
import AddIngredient from "../src/pages/AddIngredient.jsx";
import { AuthProvider } from "../src/context/AuthContext.jsx";
import { LocaleProvider } from "../src/context/LocaleContext.jsx";
import "../src/index.css";

const params = new URLSearchParams(location.search);
const locale = params.get("locale") === "en" ? "en" : "th";
// Existing catalog photo; illustrative QA values below are not a product nutrition claim.
const photo = "https://images.pexels.com/photos/11806204/pexels-photo-11806204.jpeg?auto=compress&cs=tinysrgb&h=350";
const nutrition = { calories: 143, protein_g: 12.6, carbs_g: null, fat_g: 9.5 };
const prefill = params.has("barcode") ? {
    name: locale === "th" ? "ไข่ไก่" : "Organic free-range eggs for this week's meal preparation",
    category: "Other", image: photo, nutrition_data: nutrition,
} : null;
window.fetch = async (input, options = {}) => {
    const path = new URL(typeof input === "string" ? input : input.url, location.origin).pathname;
    if (path === "/api/auth/me") return Response.json({ status: "success", data: { id: 1, locale } });
    if (path === "/api/ingredient-images") return Response.json({ status: "success", data: { fallback: "http://localhost:8000/images/No-image-available.png" } });
    if (path === "/api/ingredient-images/search") return Response.json({ status: params.has("searchError") ? "error" : "success", data: { images: params.has("empty") ? [] : [photo, photo.replace("h=350", "h=300")] } });
    if (path === "/api/ingredient-images/upload") return Response.json({ status: "success", data: { image: photo } });
    if (path === "/api/user-ingredients" && options.method === "POST") {
        if (params.has("fail")) return Response.json({ status: "error", message: "Synthetic failure" }, { status: 500 });
        return Response.json({ status: "success", data: { id: 1, ...JSON.parse(options.body) } });
    }
    throw new Error("Unexpected request blocked by add-ingredient QA: " + path);
};
export default function Preview() {
    const [items, setItems] = useState([]);
    const [receipt, setReceipt] = useState("");
    return <><output className="sr-only">{JSON.stringify({ receipt, items })}</output><AddIngredient
        prefill={prefill} userIngredients={items} setUserIngredients={setItems}
        activeTab="fridge" setActiveTab={tab => setReceipt("nav:" + tab)} onBack={() => setReceipt("back")}
    /></>;
}
createRoot(document.getElementById("root")).render(<AuthProvider><LocaleProvider><Preview /></LocaleProvider></AuthProvider>);

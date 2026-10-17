// Development-only synthetic inventory. Every fetch is intercepted; no real record is edited.
import { useState } from "react";
import { createRoot } from "react-dom/client";
import IngredientDetail from "../src/pages/IngredientDetail.jsx";
import { AuthProvider } from "../src/context/AuthContext.jsx";
import { LocaleProvider } from "../src/context/LocaleContext.jsx";
import { bangkokDate } from "../src/utils/expiry.js";
import "../src/index.css";

const params = new URLSearchParams(location.search);
const locale = params.get("locale") === "en" ? "en" : "th";
const rich = params.has("rich");
let record = {
    id: 1,
    name: params.has("long") ? (locale === "th" ? "ไข่ไก่ออร์แกนิกสำหรับเตรียมอาหารหลายมื้อในสัปดาห์นี้" : "Organic free-range eggs for this week's meal preparation") : (locale === "th" ? "ไข่ไก่" : "Eggs"),
    category: "Other",
    // Existing catalog image observed on the user's IngredientDetail page.
    image: "https://images.pexels.com/photos/11806204/pexels-photo-11806204.jpeg?auto=compress&cs=tinysrgb&h=350",
    quantity_amount: rich ? 6 : null,
    quantity_unit: rich ? "ฟอง" : null,
    expiry_date: rich ? bangkokDate() : null,
    nutrition_data: rich ? { calories: 143, protein_g: 12.6, carbs_g: null, fat_g: 9.5 } : null,
};
window.fetch = async (input, options = {}) => {
    const path = new URL(typeof input === "string" ? input : input.url, location.origin).pathname;
    if (path === "/api/auth/me") return Response.json({ status: "success", data: { id: 1, locale } });
    if (path === "/api/user-ingredients/1" && options.method === "PUT") {
        if (params.has("fail")) return Response.json({ status: "error" }, { status: 500 });
        record = { ...record, ...JSON.parse(options.body) };
        return Response.json({ status: "success", data: record });
    }
    throw new Error("Unexpected request blocked by ingredient QA: " + path);
};

export default function Preview() {
    const [ingredient, setIngredient] = useState(record);
    const [items, setItems] = useState([record]);
    const [receipt, setReceipt] = useState("");
    return <><output className="sr-only">{receipt}</output><IngredientDetail
        ingredient={ingredient} userIngredients={items} setUserIngredients={setItems}
        onUpdated={setIngredient} onBack={() => setReceipt("back")}
        onDeleted={() => setReceipt("deleted")} activeTab="fridge" setActiveTab={tab => setReceipt("nav:" + tab)}
    /></>;
}
createRoot(document.getElementById("root")).render(<AuthProvider><LocaleProvider><Preview /></LocaleProvider></AuthProvider>);

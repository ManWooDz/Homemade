// Development-only recipe/preferences. All requests and generation are synthetic.
import { useState } from "react";
import { createRoot } from "react-dom/client";
import CreateRecipe from "../src/pages/CreateRecipe.jsx";
import { AuthProvider } from "../src/context/AuthContext.jsx";
import { LocaleProvider } from "../src/context/LocaleContext.jsx";
import { bangkokDate } from "../src/utils/expiry.js";
import "../src/index.css";

const params = new URLSearchParams(location.search);
const locale = params.get("locale") === "en" ? "en" : "th";
const image = "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80";
const recipe = { name: params.has("long") ? "Superfood Veggie Bowl — colourful vegetables with a long recipe name for layout QA" : "Superfood Veggie Bowl",
    image, short_description: locale === "th" ? "โบลผักหลากสีสำหรับมื้อง่าย ๆ ที่บ้าน" : "A colourful vegetable bowl for a simple meal at home.", tags: ["Healthy / Diet", "Quick & Easy"] };
const selected = params.has("empty") ? [] : [{ id: 1, name: locale === "en" ? "green oak lettuce" : "กรีนโอ๊ค", image }, { id: 2, name: locale === "en" ? "tomato" : "มะเขือเทศ", image }];
const fridge = params.has("empty") ? [] : [{ id: 3, name: locale === "en" ? (params.has("long") ? "organic chicken eggs for preparing several meals throughout the week" : "egg") : (params.has("long") ? "ไข่ไก่ออร์แกนิกสำหรับเตรียมอาหารหลายมื้อในสัปดาห์นี้" : "ไข่ไก่"), image, expiry_date: bangkokDate() }, ...selected];
window.fetch = async input => {
    const path = new URL(typeof input === "string" ? input : input.url, location.origin).pathname;
    if (path === "/api/auth/me") return Response.json({ status: "success", data: { id: 1, locale } });
    if (path === "/api/user-preferences") return Response.json({ status: "success", data: { dietary_restrictions: ["แพ้นม / ผลิตภัณฑ์จากนม"], equipment: ["กระทะ"] } });
    throw new Error("Unexpected request blocked by CreateRecipe QA: " + path);
};
export default function Preview() {
    const [receipt, setReceipt] = useState(null);
    return <><output className="sr-only">{JSON.stringify(receipt)}</output><CreateRecipe
        recipe={recipe} selectedIngredients={selected} userIngredients={fridge} onBack={() => setReceipt("back")}
        activeTab="cooking" setActiveTab={tab => setReceipt("nav:" + tab)}
        onGenerate={async (preferences, ingredients) => {
            setReceipt({ preferences, ingredients });
            await new Promise(resolve => setTimeout(resolve, 500));
            return params.has("error") ? "กรุณาระบุอาหารที่แพ้ให้ชัดเจน เช่น แพ้กุ้ง หรือเลือกไม่มีอาการแพ้" : null;
        }}
    /></>;
}
const root = createRoot(document.getElementById("root"));
root.render(<AuthProvider><LocaleProvider><Preview /></LocaleProvider></AuthProvider>);
if (import.meta.hot) import.meta.hot.dispose(() => root.unmount());

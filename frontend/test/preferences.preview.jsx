// Development-only: all account requests and generation are intercepted.
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, useLocation } from "react-router-dom";
import Profile from "../src/pages/Profile.jsx";
import Onboarding from "../src/pages/auth/Onboarding.jsx";
import CreateRecipe from "../src/pages/CreateRecipe.jsx";
import CustomCookingPage from "../src/pages/CustomCookingPage.jsx";
import { AuthProvider } from "../src/context/AuthContext.jsx";
import { LocaleProvider } from "../src/context/LocaleContext.jsx";
import "../src/index.css";

const params = new URLSearchParams(location.search);
let stored = params.has("empty") ? null : {
    age: 25, cuisine_preferences: ["อาหารไทย"], dietary_restrictions: ["แพ้ถั่ว", "แพ้อาหารทะเล", "ทาน Vegan", ...(params.has("legacy") ? ["แพ้กีวี", "ไม่กินเนื้อวัว"] : [])],
    equipment: ["กระทะ", "หม้อ", "เตาไฟฟ้า", "ซึ้งนึ่ง"], cooking_frequency: null, cooking_goals: [],
};
let reads = 0;
let writes = 0;
const requests = [];
window.fetch = async (input, options = {}) => {
    const path = new URL(typeof input === "string" ? input : input.url, location.origin).pathname;
    if (path === "/api/auth/me") return Response.json({ status: "success", data: { id: 999, display_name: "เชฟทดสอบ", email: "fixture@example.test", locale: params.get("locale") === "en" ? "en" : "th" } });
    if (path === "/api/user-preferences") {
        requests.push({ method: options.method || "GET", body: options.body ? JSON.parse(options.body) : null });
        if (options.method === "PUT") {
            writes++;
            await new Promise(resolve => setTimeout(resolve, params.has("slowSave") ? 600 : 30));
            if (params.has("saveError") && writes === 1) return new Response(null, { status: 503 });
            stored = JSON.parse(options.body);
            return Response.json({ status: "success", data: stored });
        }
        reads++;
        if (params.has("slow")) await new Promise(resolve => setTimeout(resolve, 3500));
        if (params.has("loadError") && reads === 1) return new Response(null, { status: 503 });
        return Response.json({ status: "success", data: stored });
    }
    throw new Error("Unexpected request blocked by preference QA: " + path);
};
const ingredients = [{ id: 1, name: "ผักบุ้ง", image: "/src/assets/HomeMade_Logo.png" }, { id: 2, name: "ไข่ไก่" }];
export default function Preview() {
    const [surface, setSurface] = useState(params.get("surface") || "create");
    const [view, setView] = useState("preferences");
    const [receipt, setReceipt] = useState(null);
    const [historyBrowse, setHistoryBrowse] = useState({ query: "", rating: "all" });
    const route = useLocation();
    const common = { userIngredients: ingredients, onBack: () => setSurface("profile"), activeTab: "cooking", setActiveTab: () => {}, onGenerate: async (preferences, selected) => { setReceipt({ preferences, selected, stored, requests }); return null; } };
    return <>
        <nav aria-label="QA surfaces" className={params.has("clean") ? "hidden" : "fixed right-0 top-0 z-50 flex flex-col bg-white text-xs"}>{["profile", "onboarding", "create", "custom"].map(name => <button type="button" key={name} className="min-h-11 border px-2" onClick={() => { setSurface(name); setView("preferences"); }}>{name}</button>)}</nav>
        <output className="sr-only" id="qa-receipt">{JSON.stringify({ receipt, route: route.pathname })}</output>
        {surface === "profile" ? <Profile view={view} setView={setView} historyBrowse={historyBrowse} setHistoryBrowse={setHistoryBrowse} cookingHistory={[]} activeTab="me" setActiveTab={() => {}} onBack={() => {}} />
            : surface === "onboarding" ? <Onboarding />
                : surface === "custom" ? <CustomCookingPage {...common} />
                    : <CreateRecipe {...common} recipe={{ name: "เมนูทดสอบ", image: "/src/assets/HomeMade_Logo.png", tags: [] }} selectedIngredients={ingredients} />}
    </>;
}
const root = createRoot(document.getElementById("root"));
root.render(<MemoryRouter><AuthProvider><LocaleProvider><Preview /></LocaleProvider></AuthProvider></MemoryRouter>);
if (import.meta.hot) import.meta.hot.dispose(() => root.unmount());

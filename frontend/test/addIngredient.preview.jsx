// Development-only: all requests are intercepted; no account or inventory is modified.
import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import AddIngredient from "../src/pages/AddIngredient.jsx";
import { AuthProvider } from "../src/context/AuthContext.jsx";
import { LocaleProvider } from "../src/context/LocaleContext.jsx";
import "../src/index.css";
import logo from "../src/assets/HomeMade_Logo.png";

const params = new URLSearchParams(location.search);
const locale = params.get("locale") === "en" ? "en" : "th";
const originalFetch = import.meta.hot?.data.originalFetch ?? window.fetch;
if (import.meta.hot) import.meta.hot.data.originalFetch = originalFetch;
const samplePicture = params.has("cropQa") ? await originalFetch(logo).then(response => response.blob()) : null;
const uploads = [];
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
    if (path === "/api/ingredient-images/upload") {
        const file = options.body.get("file");
        const bitmap = await createImageBitmap(file);
        uploads.push({ name: file.name, type: file.type, size: file.size, width: bitmap.width, height: bitmap.height });
        bitmap.close();
        window.dispatchEvent(new Event("qa-upload"));
        return params.has("uploadFail") ? Response.json({ status: "error" }, { status: 500 }) : Response.json({ status: "success", data: { image: URL.createObjectURL(file) } });
    }
    if (path === "/api/user-ingredients" && options.method === "POST") {
        if (params.has("fail")) return Response.json({ status: "error", message: "Synthetic failure" }, { status: 500 });
        return Response.json({ status: "success", data: { id: 1, ...JSON.parse(options.body) } });
    }
    throw new Error("Unexpected request blocked by add-ingredient QA: " + path);
};
export default function Preview() {
    const [items, setItems] = useState([]);
    const [receipt, setReceipt] = useState("");
    useEffect(() => {
        const update = () => setReceipt("upload:" + uploads.length);
        window.addEventListener("qa-upload", update);
        return () => window.removeEventListener("qa-upload", update);
    }, []);
    return <><output className="sr-only">{JSON.stringify({ receipt, items, uploads })}</output>{params.has("cropQa") && <aside aria-label="Synthetic QA controls">
        <button onClick={() => {
            const input = document.querySelector('input[type="file"]');
            const transfer = new DataTransfer();
            transfer.items.add(new File([samplePicture], "sample.png", { type: "image/png" }));
            input.files = transfer.files;
            input.dispatchEvent(new Event("change", { bubbles: true }));
        }}>QA: select sample picture</button>
    </aside>}<AddIngredient
        prefill={prefill} userIngredients={items} setUserIngredients={setItems}
        activeTab="fridge" setActiveTab={tab => setReceipt("nav:" + tab)} onBack={() => setReceipt("back")}
    /></>;
}
const root = createRoot(document.getElementById("root"));
root.render(<AuthProvider><LocaleProvider><Preview /></LocaleProvider></AuthProvider>);
if (import.meta.hot) import.meta.hot.dispose(() => { root.unmount(); window.fetch = originalFetch; });

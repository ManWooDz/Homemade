// Development-only synthetic account. Every request is intercepted; no real profile is changed.
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, useLocation } from "react-router-dom";
import Profile from "../src/pages/Profile.jsx";
import { AuthProvider, useAuth } from "../src/context/AuthContext.jsx";
import { LocaleProvider } from "../src/context/LocaleContext.jsx";
import "../src/index.css";
import logo from "../src/assets/HomeMade_Logo.png";

const params = new URLSearchParams(location.search);
const samplePicture = await fetch(logo).then(response => response.blob());
let avatar = samplePicture;
const writes = [];
let user = { id: 1, locale: params.get("locale") === "en" ? "en" : "th",
    display_name: params.has("long") ? "เชฟโฮมเมดผู้ชอบทำอาหารด้วยวัตถุดิบที่มีอยู่ในตู้เย็น" : "เชฟโฮมเมด",
    email: params.has("long") ? "homemade.kitchen.enthusiast.for.preview@example.test" : "chef@example.test", has_avatar: params.has("avatarError") || params.has("avatar") };
window.fetch = async (input, options = {}) => {
    const path = new URL(typeof input === "string" ? input : input.url, location.origin).pathname;
    if (path === "/api/auth/me") return Response.json({ status: "success", data: user });
    if (path === "/api/user-preferences") return Response.json({ status: "success", data: {} });
    if (path === "/api/user-profile/avatar") return params.has("avatarError") ? new Response(null, { status: 503 }) : new Response(avatar);
    if (path === "/api/auth/logout") return new Response(null, { status: params.has("fail") ? 503 : 204 });
    if (path === "/api/user-profile/language") {
        user = { ...user, ...JSON.parse(options.body) };
        return Response.json({ status: "success", data: user });
    }
    if (path === "/api/user-profile" && options.method === "PUT") {
        const file = options.body.get("avatar");
        writes.push({ name: options.body.get("display_name"), action: options.body.get("avatar_action"), image: file && { type: file.type, size: file.size } });
        if (params.has("saveFail")) return Response.json({ status: "error", code: "profile_save_failed" }, { status: 503 });
        if (file) avatar = file;
        const action = options.body.get("avatar_action");
        user = { ...user, display_name: options.body.get("display_name"), has_avatar: action === "keep" ? user.has_avatar : action === "replace" };
        return Response.json({ status: "success", data: user });
    }
    throw new Error("Unexpected request blocked by profile QA: " + path);
};
export default function Preview() {
    const { user: sessionUser } = useAuth();
    const [view, setView] = useState(params.get("view") || "main");
    const [sampleUsed, setSampleUsed] = useState(false);
    const [historyBrowse, setHistoryBrowse] = useState({ query: "", rating: "all" });
    const [receipt, setReceipt] = useState("");
    const route = useLocation();
    if (!sessionUser) return null;
    const chooseSample = () => {
        const transfer = new DataTransfer();
        transfer.items.add(new File([params.has("imageFail") ? "Unreadable test image" : samplePicture], "sample.png", { type: samplePicture.type }));
        const input = document.querySelector('input[type="file"]');
        input.files = transfer.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
        setSampleUsed(true);
        window.scrollTo(0, 0);
    };
    return <>{params.has("sample") && !sampleUsed && view === "edit" && <button type="button" onClick={chooseSample} style={{ position: "fixed", top: 8, left: 8, zIndex: 100, background: "white", padding: 8 }}>QA: เลือกรูปตัวอย่าง</button>}
    <output className="sr-only">{JSON.stringify({ view, receipt, route: route.pathname, writes })}</output><Profile
        view={view} setView={setView} historyBrowse={historyBrowse} setHistoryBrowse={setHistoryBrowse} cookingHistory={[]}
        activeTab="me" setActiveTab={tab => setReceipt("nav:" + tab)} onBack={() => setReceipt("back")}
        notificationCount={3} onNotifications={() => setReceipt("notifications")} onOpenHistoryItem={() => setReceipt("history")}
    /></>;
}
createRoot(document.getElementById("root")).render(<MemoryRouter><AuthProvider><LocaleProvider><Preview /></LocaleProvider></AuthProvider></MemoryRouter>);

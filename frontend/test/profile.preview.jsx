// Development-only synthetic account. Every request is intercepted; no real profile is changed.
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, useLocation } from "react-router-dom";
import Profile from "../src/pages/Profile.jsx";
import { AuthProvider } from "../src/context/AuthContext.jsx";
import { LocaleProvider } from "../src/context/LocaleContext.jsx";
import "../src/index.css";

const params = new URLSearchParams(location.search);
let user = { id: 1, locale: params.get("locale") === "en" ? "en" : "th",
    display_name: params.has("long") ? "เชฟโฮมเมดผู้ชอบทำอาหารด้วยวัตถุดิบที่มีอยู่ในตู้เย็น" : "เชฟโฮมเมด",
    email: params.has("long") ? "homemade.kitchen.enthusiast.for.preview@example.test" : "chef@example.test", has_avatar: params.has("avatarError") };
window.fetch = async (input, options = {}) => {
    const path = new URL(typeof input === "string" ? input : input.url, location.origin).pathname;
    if (path === "/api/auth/me") return Response.json({ status: "success", data: user });
    if (path === "/api/user-preferences") return Response.json({ status: "success", data: {} });
    if (path === "/api/user-profile/avatar") return new Response(null, { status: 503 });
    if (path === "/api/auth/logout") return new Response(null, { status: params.has("fail") ? 503 : 204 });
    if (path === "/api/user-profile/language") {
        user = { ...user, ...JSON.parse(options.body) };
        return Response.json({ status: "success", data: user });
    }
    if (path === "/api/user-profile" && options.method === "PUT") {
        user = { ...user, display_name: options.body.get("display_name") };
        return Response.json({ status: "success", data: user });
    }
    throw new Error("Unexpected request blocked by profile QA: " + path);
};
export default function Preview() {
    const [view, setView] = useState("main");
    const [historyBrowse, setHistoryBrowse] = useState({ query: "", rating: "all" });
    const [receipt, setReceipt] = useState("");
    const route = useLocation();
    return <><output className="sr-only">{JSON.stringify({ view, receipt, route: route.pathname })}</output><Profile
        view={view} setView={setView} historyBrowse={historyBrowse} setHistoryBrowse={setHistoryBrowse} cookingHistory={[]}
        activeTab="me" setActiveTab={tab => setReceipt("nav:" + tab)} onBack={() => setReceipt("back")}
        notificationCount={3} onNotifications={() => setReceipt("notifications")} onOpenHistoryItem={() => setReceipt("history")}
    /></>;
}
createRoot(document.getElementById("root")).render(<MemoryRouter><AuthProvider><LocaleProvider><Preview /></LocaleProvider></AuthProvider></MemoryRouter>);

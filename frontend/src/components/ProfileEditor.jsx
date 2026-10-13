import { useEffect, useRef, useState } from "react";
import { UserRound } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../context/LocaleContext";
import { isValidDisplayName, profileErrorKey, profileImageError } from "../utils/profileValidation";
import AvatarCropper from "./AvatarCropper";

export default function ProfileEditor({ avatarUrl, onCancel, onSaved }) {
    const { user, updateProfile } = useAuth();
    const { t } = useLocale();
    const [name, setName] = useState(user?.display_name || "");
    const [action, setAction] = useState("keep");
    const [image, setImage] = useState(null);
    const [source, setSource] = useState("");
    const [preview, setPreview] = useState("");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const input = useRef(null);
    const nameInput = useRef(null);
    const request = useRef(null);
    const active = useRef(true);
    useEffect(() => {
        active.current = true;
        nameInput.current?.focus();
        return () => { active.current = false; request.current?.abort(); };
    }, []);
    useEffect(() => () => { if (source) URL.revokeObjectURL(source); }, [source]);
    useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
    const select = event => {
        const file = event.target.files?.[0];
        event.target.value = "";
        if (!file) return;
        const code = profileImageError(file);
        setError(code ? profileErrorKey(code) : "");
        if (!code) setSource(URL.createObjectURL(file));
    };
    const save = async event => {
        event.preventDefault();
        if (request.current) return;
        if (!isValidDisplayName(name)) {
            setError(profileErrorKey("profile_name_invalid"));
            nameInput.current?.focus();
            return;
        }
        const controller = new AbortController();
        request.current = controller;
        setBusy(true);
        setError("");
        const body = new FormData();
        body.set("display_name", name.trim());
        body.set("avatar_action", action);
        if (action === "replace") body.set("avatar", image, "avatar.jpg");
        const result = await updateProfile(body, controller.signal);
        request.current = null;
        if (!active.current || controller.signal.aborted) return;
        setBusy(false);
        if (result.success) onSaved();
        else setError(profileErrorKey(result.code));
    };
    if (source) return <AvatarCropper key={source} source={source} onCancel={() => setSource("")} onConfirm={blob => {
        setImage(blob); setPreview(URL.createObjectURL(blob)); setAction("replace"); setSource("");
    }} />;
    const shownImage = action === "remove" ? "" : preview || avatarUrl;
    return (
        <form onSubmit={save} className="px-5 pb-8 flex flex-col gap-5 [&_button:focus-visible]:outline-2 [&_button:focus-visible]:outline-offset-2 [&_button:focus-visible]:outline-[#B93E25]">
            <h1 className="text-xl font-bold text-gray-900">{t("แก้ไขโปรไฟล์")}</h1>
            <div className="w-24 h-24 rounded-full overflow-hidden bg-gray-100 self-center flex items-center justify-center">
                {shownImage ? <img src={shownImage} alt={t("รูปโปรไฟล์")} className="w-full h-full object-cover" /> : <UserRound aria-hidden="true" className="w-12 h-12 text-gray-500" />}
            </div>
            <div className="flex flex-wrap justify-center gap-3">
                <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" onChange={select} className="sr-only" tabIndex={-1} aria-label={t("เลือกรูป")} />
                <button type="button" disabled={busy} onClick={() => input.current?.click()} className="min-h-11 px-4 rounded-full border border-[#B93E25] text-[#B93E25]">{t("เลือกรูป")}</button>
                <button type="button" disabled={busy || !shownImage} onClick={() => { setAction("remove"); setImage(null); setPreview(""); }} className="min-h-11 px-4 rounded-full border border-gray-400 text-gray-700 disabled:opacity-50">{t("ใช้รูปเริ่มต้น")}</button>
            </div>
            <p className="text-sm text-gray-600 text-center">{t("JPG, PNG หรือ WebP ไม่เกิน 5 MB")}</p>
            <div className="flex flex-col gap-2">
                <label htmlFor="profile-name" className="text-sm font-semibold text-gray-900">{t("ชื่อแสดง")}</label>
                <input ref={nameInput} id="profile-name" value={name} disabled={busy} onChange={event => setName(event.target.value)} aria-describedby="profile-name-help" aria-invalid={!!error && !isValidDisplayName(name)} placeholder={t("ผู้ใช้ Homemade")} className="w-full min-h-11 px-4 text-base rounded-full border border-gray-400 text-gray-900 focus:outline-2 focus:outline-[#B93E25]" />
                <p id="profile-name-help" className="text-sm text-gray-600">{t("ชื่อซ้ำกับผู้อื่นได้ ไม่ใช่อีเมลเข้าสู่ระบบ")}</p>
            </div>
            {error && <p role="alert" className="text-sm text-red-700">{t(error)}</p>}
            <div className="grid grid-cols-2 gap-3">
                <button type="button" onClick={onCancel} disabled={busy} className="min-h-11 px-4 rounded-full border border-gray-400 text-gray-700 disabled:opacity-50">{t("ยกเลิก")}</button>
                <button type="submit" disabled={busy} className="min-h-11 px-4 rounded-full bg-[#B93E25] text-white disabled:opacity-50">{t(busy ? "กำลังบันทึก..." : "บันทึก")}</button>
            </div>
        </form>
    );
}

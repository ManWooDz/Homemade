import { useEffect, useRef, useState } from "react";
import { ImagePlus, RotateCcw, UserRound } from "lucide-react";
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
    const heading = useRef(null);
    const request = useRef(null);
    const active = useRef(true);
    useEffect(() => {
        active.current = true;
        return () => { active.current = false; request.current?.abort(); };
    }, []);
    useEffect(() => { if (!source) heading.current?.focus(); }, [source]);
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
        <form onSubmit={save} className="profile-editor px-6 pb-8">
            <h1 ref={heading} tabIndex={-1} className="text-2xl font-bold leading-normal text-gray-900 outline-none">{t("แก้ไขโปรไฟล์")}</h1>
            <section aria-labelledby="profile-picture-heading" className="mt-6 border-b border-gray-200 pb-6">
                <h2 id="profile-picture-heading" className="text-base font-semibold text-gray-900">{t("รูปโปรไฟล์")}</h2>
                <div className="mx-auto mt-4 flex h-28 w-28 items-center justify-center overflow-hidden rounded-full bg-[#fdece5]">
                    {shownImage ? <img src={shownImage} alt={t("รูปโปรไฟล์")} className="h-full w-full object-cover" /> : <UserRound aria-hidden="true" className="h-14 w-14 text-[#b93e25]" strokeWidth={1.5} />}
                </div>
                <div className="mt-4 flex flex-wrap justify-center gap-x-3 gap-y-2">
                    <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" onChange={select} hidden aria-label={t("เลือกรูป")} />
                    <button type="button" disabled={busy} onClick={() => input.current?.click()} className="profile-picture-choose inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-[#b93e25] px-4 font-semibold text-[#b93e25] hover:bg-[#fdece5] disabled:opacity-50">
                        <ImagePlus aria-hidden="true" className="h-5 w-5 shrink-0" />{t("เลือกรูป")}
                    </button>
                    <button type="button" disabled={busy || !shownImage} onClick={() => { setAction("remove"); setImage(null); setPreview(""); }} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-3 text-gray-600 hover:bg-gray-100 disabled:opacity-50">
                        <RotateCcw aria-hidden="true" className="h-4 w-4 shrink-0" />{t("ใช้รูปเริ่มต้น")}
                    </button>
                </div>
                <p className="mt-3 text-center text-caption text-gray-600">{t("JPG, PNG หรือ WebP ไม่เกิน 5 MB")}</p>
            </section>
            <div className="mt-6 flex flex-col gap-2">
                <label htmlFor="profile-name" className="text-base font-semibold text-gray-900">{t("ชื่อแสดง")}</label>
                <input ref={nameInput} id="profile-name" value={name} disabled={busy} onChange={event => setName(event.target.value)} aria-describedby={`profile-name-help${error ? " profile-editor-error" : ""}`} aria-invalid={!!error && !isValidDisplayName(name)} placeholder={t("ผู้ใช้ Homemade")} className="min-h-12 w-full rounded-full border border-gray-400 px-4 text-base text-gray-900 placeholder:text-gray-500" />
                <p id="profile-name-help" className="text-caption text-gray-600">{t("ชื่อซ้ำกับผู้อื่นได้ ไม่ใช่อีเมลเข้าสู่ระบบ")}</p>
            </div>
            {error && <p id="profile-editor-error" role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-base text-red-800">{t(error)}</p>}
            <div className="profile-editor-actions mt-8 grid grid-cols-2 gap-3">
                <button type="button" onClick={onCancel} disabled={busy} className="min-h-12 rounded-full border border-gray-400 px-4 font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-50">{t("ยกเลิก")}</button>
                <button type="submit" disabled={busy} aria-busy={busy} className="min-h-12 rounded-full bg-[#b93e25] px-4 font-semibold text-white hover:bg-[#9f351f] disabled:opacity-50">{t(busy ? "กำลังบันทึก..." : "บันทึก")}</button>
            </div>
        </form>
    );
}

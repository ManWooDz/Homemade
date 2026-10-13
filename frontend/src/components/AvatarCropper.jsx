import { useEffect, useRef, useState } from "react";
import Cropper from "react-easy-crop";
import { useLocale } from "../context/LocaleContext";
import { cropAvatar } from "../utils/profileValidation";

export default function AvatarCropper({ source, onConfirm, onCancel }) {
    const { t } = useLocale();
    const [crop, setCrop] = useState({ x: 0, y: 0 });
    const [zoom, setZoom] = useState(1);
    const [area, setArea] = useState(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [imageFailed, setImageFailed] = useState(false);
    const image = useRef(null);
    const mounted = useRef(true);
    const heading = useRef(null);
    useEffect(() => {
        mounted.current = true;
        heading.current?.focus();
        return () => { mounted.current = false; };
    }, []);
    const confirm = async () => {
        if (busy || !area || !image.current) return;
        setBusy(true);
        setError("");
        try {
            const blob = await cropAvatar(image.current, area);
            if (mounted.current) onConfirm(blob);
        } catch {
            if (mounted.current) setError(t("ครอปรูปไม่สำเร็จ กรุณาลองอีกครั้ง"));
        } finally {
            if (mounted.current) setBusy(false);
        }
    };
    return (
        <section className="px-5 pb-8 flex flex-col gap-5">
            <h1 ref={heading} tabIndex={-1} className="text-xl font-bold text-gray-900 outline-none">{t("ครอปรูปโปรไฟล์")}</h1>
            <p id="crop-help" className="text-sm text-gray-600">{t("ลากรูปเพื่อจัดตำแหน่ง ใช้ปุ่มลูกศรเลื่อนรูปได้")}</p>
            <div className="relative h-72 w-full overflow-hidden rounded-2xl bg-gray-900">
                <Cropper image={source} crop={crop} zoom={zoom} aspect={1} cropShape="round" showGrid={false} zoomWithScroll={false}
                    onCropChange={setCrop} onZoomChange={setZoom} onCropComplete={(_, pixels) => setArea(pixels)}
                    setImageRef={ref => { image.current = ref.current; }}
                    mediaProps={{ onError: () => { setImageFailed(true); setError(t("เลือกรูป JPG, PNG หรือ WebP ที่เปิดอ่านได้")); } }}
                    cropperProps={{ "aria-label": t("รูปโปรไฟล์"), "aria-describedby": "crop-help" }} keyboardStep={10} />
            </div>
            <label htmlFor="avatar-zoom" className="text-sm font-semibold text-gray-900">{t("ซูม")} {Math.round(zoom * 100)}%</label>
            <input id="avatar-zoom" type="range" min="1" max="3" step="0.05" value={zoom} onChange={event => setZoom(Number(event.target.value))} disabled={busy} className="w-full min-h-11 accent-[#B93E25] focus-visible:outline-2 focus-visible:outline-[#B93E25]" />
            {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
            <div className="grid grid-cols-2 gap-3">
                <button type="button" onClick={onCancel} disabled={busy} className="min-h-11 px-4 rounded-full border border-gray-400 text-gray-700 focus-visible:outline-2 focus-visible:outline-[#B93E25]">{t("ยกเลิก")}</button>
                <button type="button" onClick={confirm} disabled={busy || !area || imageFailed} className="min-h-11 px-4 rounded-full bg-[#B93E25] text-white disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]">{t(busy ? "กำลังเตรียมรูป..." : "ยืนยันครอป")}</button>
            </div>
        </section>
    );
}

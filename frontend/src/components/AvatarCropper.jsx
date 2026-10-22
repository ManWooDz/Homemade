import { useEffect, useRef, useState } from "react";
import Cropper from "react-easy-crop";
import { Minus, Plus } from "lucide-react";
import { useLocale } from "../context/LocaleContext";
import { cropAvatar } from "../utils/profileValidation";

export default function AvatarCropper({ source, onConfirm, onCancel, title = "ครอปรูปโปรไฟล์", imageLabel = "รูปโปรไฟล์", cropShape = "round" }) {
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
        <section aria-labelledby="avatar-crop-heading" className="avatar-cropper px-6 pb-8">
            <h1 id="avatar-crop-heading" ref={heading} tabIndex={-1} className="text-2xl font-bold leading-normal text-gray-900 outline-none">{t(title)}</h1>
            <p id="crop-help" className="mt-2 text-caption text-gray-600">{t("ลากรูปเพื่อจัดตำแหน่ง ใช้ปุ่มลูกศรเลื่อนรูปได้")}</p>
            <div className="avatar-crop-stage relative mt-5 w-full overflow-hidden rounded-2xl bg-gray-900">
                <Cropper image={source} crop={crop} zoom={zoom} aspect={1} cropShape={cropShape} showGrid={false} zoomWithScroll={false}
                    onCropChange={setCrop} onZoomChange={setZoom} onCropComplete={(_, pixels) => setArea(pixels)}
                    setImageRef={ref => { image.current = ref.current; }}
                    mediaProps={{ onError: () => { setImageFailed(true); setError(t("เลือกรูป JPG, PNG หรือ WebP ที่เปิดอ่านได้")); } }}
                    cropperProps={{ "aria-label": t(imageLabel), "aria-describedby": "crop-help", "aria-disabled": busy, tabIndex: busy ? -1 : 0 }} keyboardStep={10}
                    style={{ cropAreaStyle: { border: "2px solid white" }, containerStyle: { pointerEvents: busy ? "none" : "auto" } }} />
            </div>
            <div className="mt-5">
                <div className="flex items-baseline justify-between gap-3">
                    <label htmlFor="avatar-zoom" className="text-base font-semibold text-gray-900">{t("ซูม")}</label>
                    <span aria-hidden="true" className="font-semibold tabular-nums text-[#b93e25]">{Math.round(zoom * 100)}%</span>
                </div>
                <div className="flex items-center gap-3">
                    <Minus aria-hidden="true" className="h-4 w-4 shrink-0 text-gray-500" />
                    <input id="avatar-zoom" type="range" min="1" max="3" step="0.05" value={zoom} aria-valuetext={`${Math.round(zoom * 100)}%`} onChange={event => setZoom(Number(event.target.value))} disabled={busy || imageFailed} className="min-h-11 min-w-0 flex-1 accent-[#b93e25]" />
                    <Plus aria-hidden="true" className="h-4 w-4 shrink-0 text-gray-500" />
                </div>
            </div>
            {error && <p role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-base text-red-800">{error}</p>}
            <div className="mt-6 grid grid-cols-2 gap-3">
                <button type="button" onClick={onCancel} disabled={busy} className="min-h-12 rounded-full border border-gray-400 px-4 font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-50">{t("ยกเลิก")}</button>
                <button type="button" onClick={confirm} disabled={busy || !area || imageFailed} aria-busy={busy} className="min-h-12 rounded-full bg-[#b93e25] px-4 font-semibold text-white hover:bg-[#9f351f] disabled:opacity-50">{t(busy ? "กำลังเตรียมรูป..." : "ยืนยันครอป")}</button>
            </div>
        </section>
    );
}

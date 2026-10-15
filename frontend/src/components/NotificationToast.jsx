import { useEffect, useState } from "react";
import { Bell, BookmarkCheck, X } from "lucide-react";
import { useLocale } from "../context/LocaleContext";
import NotificationImage from "./NotificationImage";

export default function NotificationToast({ notice, ingredients = [], onDismiss, onOpen }) {
    const { t } = useLocale();
    const [hovered, setHovered] = useState(false);
    const [focused, setFocused] = useState(false);
    useEffect(() => {
        if (hovered || focused) return;
        const timeout = setTimeout(onDismiss, 8000);
        return () => clearTimeout(timeout);
    }, [hovered, focused, onDismiss]);
    const summary = notice.kind === "expiry_summary";
    const title = summary ? t("มีวัตถุดิบที่ควรตรวจสอบ {count} รายการ", { count: notice.items.length })
        : t(notice.kind === "recipe_history_saved" ? "สร้างสูตรและบันทึกในประวัติแล้ว" : "บันทึกเป็นสูตรที่ชอบแล้ว");
    const Icon = summary ? Bell : BookmarkCheck;
    const singleIngredient = summary && notice.items.length === 1;
    const image = singleIngredient && ingredients.find(ingredient => ingredient.id === notice.items[0].target_id)?.image;
    return <aside className="notification-toast fixed top-4 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-[398px] z-50 rounded-2xl bg-white p-4 shadow-[0_8px_32px_rgba(17,24,39,0.18)]"
        onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
        onFocus={() => setFocused(true)} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false); }}>
        <div className="flex items-start gap-3">
            <span className={`${singleIngredient ? "w-10 h-10" : "w-5 h-5 mt-1"} shrink-0 flex items-center justify-center text-[#B93E25]`}><NotificationImage image={image} Icon={Icon} /></span>
            <div className="min-w-0 flex-1" role="status" aria-live="polite" aria-atomic="true">
                <p className="text-sm font-semibold text-gray-900 leading-relaxed">{title}</p>
                <p className="text-sm text-gray-600 mt-1 break-words">{summary ? t("อ้างอิงวันที่หมดอายุที่คุณบันทึกไว้") : notice.payload.name}</p>
            </div>
            <button type="button" aria-label={t("ปิดแจ้งเตือน")} onClick={onDismiss} className="w-11 h-11 -mt-2 -mr-2 shrink-0 flex items-center justify-center rounded-full text-gray-600 hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-[#B93E25]"><X className="w-5 h-5" /></button>
        </div>
        <button type="button" onClick={onOpen} className="mt-2 ml-8 min-h-11 font-semibold text-sm text-[#B93E25] underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-[#B93E25]">{t(summary ? "ดูรายการแจ้งเตือน" : "ดูสูตร")}</button>
    </aside>;
}

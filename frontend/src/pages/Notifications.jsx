import PageShell from "../components/PageShell";
import { useEffect } from "react";
import { Bell, BookmarkCheck, ChevronLeft, ChevronRight, Clock, RefreshCw } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import NotificationImage from "../components/NotificationImage";
import { useLocale } from "../context/LocaleContext";

export default function Notifications({ items, ingredients = [], count, tab, onTabChange, loading, pending, error,
    nextCursor, onLoadMore, onRetry, onReadAll, onOpen, onBack, activeTab, setActiveTab, getScroll, rememberScroll }) {
    const { t, locale } = useLocale();
    useEffect(() => {
        const remember = () => rememberScroll?.(tab, window.scrollY);
        window.addEventListener("scroll", remember, { passive: true });
        return () => window.removeEventListener("scroll", remember);
    }, [tab, rememberScroll]);
    const dateFormat = new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "th-TH", { timeZone: "Asia/Bangkok", dateStyle: "medium" });
    const timestamp = new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "th-TH", { timeZone: "Asia/Bangkok", dateStyle: "short", timeStyle: "short" });
    const titles = { expiry_near: "วัตถุดิบใกล้วันที่หมดอายุ", expiry_today: "ถึงวันที่หมดอายุที่บันทึกไว้", expiry_passed: "เลยวันที่หมดอายุที่บันทึกไว้", recipe_history_saved: "สร้างสูตรและบันทึกในประวัติแล้ว", recipe_favorite_added: "บันทึกเป็นสูตรที่ชอบแล้ว" };
    return <PageShell scrollKey={tab} initialScroll={getScroll?.(tab) ?? 0}>

            <header className="pt-8 px-5 pb-6 relative flex justify-center items-center">
                <button type="button" aria-label={t("กลับ")} onClick={onBack} className="absolute left-5 w-11 h-11 flex items-center justify-center rounded-full bg-[#B93E25] text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]"><ChevronLeft /></button>
                <img src={logo} alt="HomeMade" className="h-18 object-contain" />
            </header>
            <div className="px-5">
                <div className="flex items-center justify-between gap-2 mb-5">
                    <h1 className="text-2xl font-bold text-gray-900">{t("แจ้งเตือน")}</h1>
                    <button type="button" onClick={onRetry} disabled={loading || pending} aria-label={t("รีเฟรชแจ้งเตือน")} className="w-11 h-11 rounded-full flex items-center justify-center text-gray-600 hover:bg-gray-100 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-[#B93E25]"><RefreshCw className="w-5 h-5" /></button>
                </div>
                <div className="flex rounded-full bg-gray-100 p-1 gap-1" role="group" aria-label={t("สถานะแจ้งเตือน")}>
                    {["unread", "read"].map(state => <button type="button" key={state} aria-pressed={tab === state} onClick={() => onTabChange(state)} disabled={pending}
                        className={`min-h-11 flex-1 px-3 rounded-full text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25] ${tab === state ? "bg-[#B93E25] text-white" : "text-gray-600 hover:bg-white"}`}>
                        {t(state === "unread" ? "ยังไม่อ่าน" : "อ่านแล้ว")}{state === "unread" && count != null && <span className="ml-2 tabular-nums">{count}</span>}
                    </button>)}
                </div>
                <div className="min-h-14 flex items-center justify-end gap-2">
                    {tab === "unread" && count > 0 && <button type="button" onClick={onReadAll} disabled={pending || loading} className="min-h-11 text-sm font-semibold text-[#B93E25] disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-[#B93E25]">{t(pending ? "กำลังบันทึก..." : "อ่านทั้งหมด")}</button>}
                </div>
            </div>
            <div className="flex-1 px-5 pb-8" aria-busy={loading || pending}>
                {error && <div role="alert" className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-800">{t(error)} <button type="button" onClick={onRetry} disabled={loading || pending} className="block min-h-11 font-semibold underline underline-offset-4">{t("ลองอีกครั้ง")}</button></div>}
                {loading && items.length === 0 && <p role="status" className="py-10 text-center text-gray-600">{t("กำลังโหลดแจ้งเตือน...")}</p>}
                {!loading && !error && items.length === 0 && <div className="py-12 text-center">
                    <Bell className="w-9 h-9 mx-auto text-gray-400 mb-4" aria-hidden="true" />
                    <h2 className="font-semibold text-gray-900">{t(tab === "unread" ? "ไม่มีแจ้งเตือนที่ยังไม่อ่าน" : "ยังไม่มีแจ้งเตือนที่อ่านแล้ว")}</h2>
                    <p className="mt-2 text-sm text-gray-600 leading-relaxed">{t("เมื่อมีรายการใหม่ เราจะแสดงให้คุณที่นี่")}</p>
                </div>}
                <ul className="divide-y divide-gray-200">
                    {items.map(item => {
                        const expiry = item.kind.startsWith("expiry_");
                        const Icon = expiry ? Clock : BookmarkCheck;
                        return <li key={item.id}><button type="button" onClick={() => onOpen(item)} disabled={pending || loading}
                            className="w-full text-left py-5 flex gap-3 rounded-xl hover:bg-orange-50 focus-visible:outline-2 focus-visible:outline-[#B93E25] disabled:opacity-60">
                            <span className={`w-10 h-10 rounded-full shrink-0 flex items-center justify-center ${expiry ? "bg-orange-50 text-[#B93E25]" : "bg-gray-100 text-gray-600"}`}><NotificationImage image={expiry && ingredients.find(ingredient => ingredient.id === item.target_id)?.image} Icon={Icon} /></span>
                            <span className="min-w-0 flex-1">
                                <span className="flex items-start gap-2"><span className="text-sm font-semibold leading-relaxed text-gray-900">{t(titles[item.kind])}</span>{!item.read_at && <span aria-label={t("ยังไม่อ่าน")} className="w-2 h-2 shrink-0 rounded-full mt-2 bg-[#B93E25]" />}</span>
                                <span className="block mt-1 text-sm text-gray-700 break-words leading-relaxed">{item.payload.name}</span>
                                {expiry && <span className="block mt-1 text-xs text-gray-600">{t("วันที่บันทึก: {date}", { date: dateFormat.format(new Date(`${item.payload.expiry_date}T00:00:00+07:00`)) })}</span>}
                                <time dateTime={item.created_at} className="block mt-2 text-xs text-gray-500 tabular-nums">{timestamp.format(new Date(item.created_at))}</time>
                            </span><ChevronRight className="w-4 h-4 text-gray-400 shrink-0 mt-2" aria-hidden="true" />
                        </button></li>;
                    })}
                </ul>
                {nextCursor && <button type="button" onClick={onLoadMore} disabled={loading || pending} className="w-full min-h-11 rounded-full border border-gray-300 text-sm font-semibold text-gray-700 my-4 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-[#B93E25]">{t(loading ? "กำลังโหลดแจ้งเตือน..." : "โหลดเพิ่มเติม")}</button>}
            </div>
            <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />

    </PageShell>;
}

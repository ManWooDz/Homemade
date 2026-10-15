import { Bell } from "lucide-react";
import { useLocale } from "../context/LocaleContext";

export default function NotificationBell({ count, onClick }) {
    const { t } = useLocale();
    return <button type="button" onClick={onClick}
        aria-label={count == null ? t("แจ้งเตือน") : t("แจ้งเตือน ยังไม่อ่าน {count} รายการ", { count })}
        className="absolute right-0 top-1/2 -translate-y-1/2 w-11 h-11 flex items-center justify-center rounded-full text-gray-700 hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]">
        <Bell className="w-6 h-6" aria-hidden="true" />
        {count > 0 && <span aria-hidden="true" className="absolute top-0 right-0 min-w-5 h-5 px-1 flex items-center justify-center rounded-full bg-[#B93E25] text-white text-xs font-semibold tabular-nums">{count > 99 ? "99+" : count}</span>}
    </button>;
}

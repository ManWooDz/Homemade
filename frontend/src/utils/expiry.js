// "YYYY-MM-DD" strings compare correctly as plain strings, so this mirrors
// the backend's ORDER BY expiry_date ASC NULLS LAST, id ASC exactly. Used to
// re-sort the in-memory list right after adding an ingredient, since the
// list is only re-fetched (and thus re-sorted server-side) on page load.
export function sortByExpiry(items) {
    return [...items].sort((a, b) => {
        if (a.expiry_date == null && b.expiry_date == null) return a.id - b.id;
        if (a.expiry_date == null) return 1;
        if (b.expiry_date == null) return -1;
        if (a.expiry_date !== b.expiry_date) {
            return a.expiry_date < b.expiry_date ? -1 : 1;
        }
        return a.id - b.id;
    });
}

const NEAR_EXPIRY_THRESHOLD_DAYS = 3;

export function bangkokDate(now = new Date()) {
    return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Bangkok", year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
}

// Compare calendar dates, so all devices agree with account notifications.
export function daysUntilExpiry(expiryDateStr, now = new Date()) {
    if (!expiryDateStr) return null;
    const [y, m, d] = expiryDateStr.split("-").map(Number);
    const expiry = Date.UTC(y, m - 1, d);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(expiryDateStr) || new Date(expiry).toISOString().slice(0, 10) !== expiryDateStr) return null;
    const [ty, tm, td] = bangkokDate(now).split("-").map(Number);
    const today = Date.UTC(ty, tm - 1, td);
    const msPerDay = 24 * 60 * 60 * 1000;
    return (expiry - today) / msPerDay;
}

// null when there's no expiry date or it's not near enough to flag.
export function expiryBadgeLabel(expiryDateStr, locale = "th") {
    const days = daysUntilExpiry(expiryDateStr);
    if (days === null || days > NEAR_EXPIRY_THRESHOLD_DAYS) return null;
    if (days < 0) return locale === "en" ? "Expired" : "หมดอายุแล้ว";
    if (days === 0) return locale === "en" ? "Expires today" : "หมดอายุวันนี้";
    return locale === "en" ? `Expires in ${days} ${days === 1 ? "day" : "days"}` : `หมดอายุใน ${days} วัน`;
}

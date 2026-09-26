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

// Parses "YYYY-MM-DD" as a LOCAL date, not UTC — new Date("YYYY-MM-DD")
// parses as UTC midnight, which reads as "already expired" from ~7am
// onward in Bangkok time (UTC+7). Compares against local midnight today.
export function daysUntilExpiry(expiryDateStr) {
    if (!expiryDateStr) return null;
    const [y, m, d] = expiryDateStr.split("-").map(Number);
    const expiry = new Date(y, m - 1, d);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const msPerDay = 24 * 60 * 60 * 1000;
    return Math.round((expiry - today) / msPerDay);
}

// null when there's no expiry date or it's not near enough to flag.
export function expiryBadgeLabel(expiryDateStr) {
    const days = daysUntilExpiry(expiryDateStr);
    if (days === null || days > NEAR_EXPIRY_THRESHOLD_DAYS) return null;
    if (days < 0) return "หมดอายุแล้ว";
    if (days === 0) return "หมดอายุวันนี้";
    return `หมดอายุใน ${days} วัน`;
}

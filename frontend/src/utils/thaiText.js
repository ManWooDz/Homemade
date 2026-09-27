// Mirrors backend/nutrition/text.py's normalize_thai/normalize_alias --
// duplicated (not shared across the language boundary), not imported.
// See MEMORY.md's 2026-09-21 entry: plain NFC normalization alone is NOT
// enough for Thai SARA AM (ำ) equivalence with its decomposed form.
const THAI_TONE_MARKS = "่้๊๋";
const TONE_MARK_AFTER_NIKHAHIT_RE = new RegExp(`ํ([${THAI_TONE_MARKS}])`, "g");

export function normalizeThai(s) {
    let result = s.normalize("NFC");
    result = result.replaceAll("ำ", "ํา");
    result = result.replace(TONE_MARK_AFTER_NIKHAHIT_RE, "$1ํ");
    return result;
}

export function normalizeForSearch(s) {
    return normalizeThai(s.trim()).toLowerCase();
}

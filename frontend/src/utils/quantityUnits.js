// Must match backend/main.py's QuantityUnit Literal exactly, byte-for-byte
// (Thai combining marks are the same encoding-sensitivity class as the
// SARA AM search bug) -- a mismatch here means the dropdown offers a value
// the backend 422s on.
export const QUANTITY_UNITS = [
    "ชิ้น",
    "กรัม",
    "กก.",
    "มล.",
    "ลิตร",
    "ขวด",
    "ถุง",
    "แพ็ค",
    "ฟอง",
    "หัว",
    "ลูก",
    "ห่อ",
];

// Units that convert to a common base so cross-unit amounts compare
// meaningfully (2 กก. vs 500 กรัม); everything else groups by its own
// exact unit string since there's no sensible conversion between e.g.
// ขวด and ถุง.
const WEIGHT_TO_GRAMS = { "กรัม": 1, "กก.": 1000 };
const VOLUME_TO_ML = { "มล.": 1, "ลิตร": 1000 };

export function quantityDimension(unit) {
    if (unit in WEIGHT_TO_GRAMS) return "weight";
    if (unit in VOLUME_TO_ML) return "volume";
    if (unit) return `unit:${unit}`;
    return "none";
}

export function normalizedQuantityAmount(amount, unit) {
    if (unit in WEIGHT_TO_GRAMS) return amount * WEIGHT_TO_GRAMS[unit];
    if (unit in VOLUME_TO_ML) return amount * VOLUME_TO_ML[unit];
    return amount;
}

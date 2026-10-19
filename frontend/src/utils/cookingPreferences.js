import { ALLERGY_OPTIONS, ALLERGY_NONE, DIETARY_OPTIONS, DIETARY_NONE, EQUIPMENT_OPTIONS, EQUIPMENT_NONE, NO_RESTRICTION, OTHER_OPTION, toggleInList } from "../constants/preferenceOptions.js";

// Category information lives inside existing string[] storage; never send tags to generation.
const CUSTOM_PREFIX = "homemade:preference:v1:";
export const emptyCookingPreferences = () => ({ allergies: [], allergyOther: [], dietary: [], dietaryOther: [], equipment: [], equipmentOther: [], unclassified: [] });
const unique = values => [...new Set(values)];
const strings = values => Array.isArray(values) ? values.filter(value => typeof value === "string" && value.trim()) : [];
const legacyAllergies = {
    "แพ้ถั่ว": ["แพ้ถั่วลิสง"], "ถั่ว": ["แพ้ถั่วลิสง"],
    "แพ้อาหารทะเล": ["แพ้กุ้ง", "แพ้ปู/หอย", "แพ้ปลา"], "กุ้ง/อาหารทะเล": ["แพ้กุ้ง", "แพ้ปู/หอย", "แพ้ปลา"],
    "นม/ผลิตภัณฑ์จากนม": ["แพ้นม / ผลิตภัณฑ์จากนม"], "ไข่": ["แพ้ไข่"], "ปลา": ["แพ้ปลา"],
    "แป้งสาลี/กลูเตน": ["แพ้แป้งสาลี / Gluten"], "ถั่วเหลือง": ["แพ้ถั่วเหลือง"], "งา": ["แพ้งา"],
};

export function readCookingPreferences(data = {}) {
    const result = emptyCookingPreferences();
    for (const value of strings(data.dietary_restrictions)) {
        if (value === NO_RESTRICTION) { result.allergies.push(ALLERGY_NONE); result.dietary.push(DIETARY_NONE); }
        else if (value === "ไม่มี") result.allergies.push(ALLERGY_NONE);
        else if (Object.hasOwn(legacyAllergies, value)) result.allergies.push(...legacyAllergies[value]);
        else if (ALLERGY_OPTIONS.includes(value) && value !== OTHER_OPTION) result.allergies.push(value);
        else if (DIETARY_OPTIONS.includes(value) && value !== OTHER_OPTION) result.dietary.push(value);
        else {
            let custom;
            try { if (value.startsWith(CUSTOM_PREFIX)) custom = JSON.parse(value.slice(CUSTOM_PREFIX.length)); } catch { /* Invalid tags remain visible as legacy text. */ }
            if (custom && ["allergy", "dietary"].includes(custom.kind) && typeof custom.text === "string" && custom.text.trim()) {
                result[custom.kind === "allergy" ? "allergies" : "dietary"].push(OTHER_OPTION);
                result[custom.kind === "allergy" ? "allergyOther" : "dietaryOther"].push(custom.text);
            } else result.unclassified.push(value);
        }
    }
    for (const value of strings(data.equipment)) {
        if (value === "กระทะ/เตาแก๊สทั่วไป") result.equipment.push("กระทะ", "เตาแก๊ส");
        else if (EQUIPMENT_OPTIONS.includes(value) && value !== OTHER_OPTION) result.equipment.push(value);
        else { result.equipment.push(OTHER_OPTION); result.equipmentOther.push(value === OTHER_OPTION || value === "อื่นๆ" ? "" : value); }
    }
    for (const [key, none] of [["allergies", ALLERGY_NONE], ["dietary", DIETARY_NONE], ["equipment", EQUIPMENT_NONE]]) {
        result[key] = unique(result[key]);
        if (result[key].length > 1) result[key] = result[key].filter(value => value !== none);
    }
    return result;
}

export function serializeCookingPreferences(model) {
    const custom = (key, other, kind) => model[key].includes(OTHER_OPTION)
        ? strings(model[other]).map(text => CUSTOM_PREFIX + JSON.stringify({ kind, text })) : [];
    return {
        dietary_restrictions: unique([
            ...model.allergies.filter(value => value !== OTHER_OPTION), ...model.dietary.filter(value => value !== OTHER_OPTION),
            ...custom("allergies", "allergyOther", "allergy"), ...custom("dietary", "dietaryOther", "dietary"), ...model.unclassified,
        ]),
        equipment: unique([...model.equipment.filter(value => value !== OTHER_OPTION), ...(model.equipment.includes(OTHER_OPTION) ? strings(model.equipmentOther) : [])]),
    };
}

export function classifyRestriction(model, index, kind) {
    const key = kind === "allergy" ? "allergies" : "dietary";
    const other = kind === "allergy" ? "allergyOther" : "dietaryOther";
    const none = kind === "allergy" ? ALLERGY_NONE : DIETARY_NONE;
    const text = model.unclassified[index];
    return { ...model, [key]: unique([...model[key].filter(value => value !== none), OTHER_OPTION]), [other]: [...model[other], [OTHER_OPTION, "อื่นๆ"].includes(text) ? "" : text], unclassified: model.unclassified.filter((_, i) => i !== index) };
}

export function toggleCookingChoice(model, key, option, none, other) {
    return { ...model, [key]: toggleInList(model[key], option, none), ...(option === OTHER_OPTION && model[other].length === 0 ? { [other]: [""] } : {}) };
}

export function cookingPreferenceError(model) {
    if (model.unclassified.length) return "กรุณาจัดหมวดข้อความเดิมก่อนสร้างสูตร";
    for (const [key, other] of [["allergies", "allergyOther"], ["dietary", "dietaryOther"], ["equipment", "equipmentOther"]]) {
        if (model[key].includes(OTHER_OPTION) && (!model[other].length || model[other].some(text => !text.trim()))) return "กรุณาระบุข้อความในตัวเลือกอื่น ๆ ให้ครบ";
    }
    return null;
}

export function generationPreferences(model, taste, extra) {
    const resolve = (key, other) => model[key].flatMap(value => value === OTHER_OPTION ? strings(model[other]) : [value]);
    const diet = resolve("dietary", "dietaryOther").filter(value => value !== DIETARY_NONE);
    return { taste, allergies: resolve("allergies", "allergyOther").join(", "), equipment: resolve("equipment", "equipmentOther").join(", "), extra: [diet.length ? `ข้อจำกัดในการกิน: ${diet.join(", ")}` : "", extra].filter(Boolean).join("\n") };
}

export async function loadCookingPreferences(apiFetch) {
    const response = await apiFetch("/api/user-preferences");
    if (!response.ok) throw new Error("preference_load_failed");
    const payload = await response.json();
    if (!payload || !("data" in payload) || (payload.data !== null && (typeof payload.data !== "object" || Array.isArray(payload.data)))) throw new Error("preference_payload_invalid");
    if ("status" in payload && payload.status !== "success") throw new Error("preference_payload_invalid");
    for (const key of ["dietary_restrictions", "equipment"]) {
        if (payload.data?.[key] !== undefined && (!Array.isArray(payload.data[key]) || payload.data[key].some(value => typeof value !== "string"))) throw new Error("preference_payload_invalid");
    }
    return payload.data || {};
}

export function mergeUntouchedPreferences(current, loaded, touched) {
    return Object.fromEntries(Object.keys(current).map(key => [key, touched.has(key) ? current[key] : loaded[key]]));
}

// Whole-record PUTs must complete in edit order, including recovery after a failed save.
export function orderedPreferenceSaver(apiFetch) {
    let pending = Promise.resolve();
    return body => {
        const snapshot = JSON.stringify(body);
        pending = pending.catch(() => {}).then(async () => {
            const response = await apiFetch("/api/user-preferences", { method: "PUT", headers: { "Content-Type": "application/json" }, body: snapshot });
            if (!response.ok) throw new Error("preference_save_failed");
        });
        return pending;
    };
}

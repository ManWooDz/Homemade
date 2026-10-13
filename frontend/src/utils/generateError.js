import { translate } from "./translations.js";

// Keep known user-facing copy; hide raw provider/developer exceptions.
const THAI_CHAR = /[฀-๿]/;

export function toUserFacingGenerateError(message, locale = "th") {
    if (typeof message !== "string" || !THAI_CHAR.test(message)) return null;
    if (locale !== "en") return message;
    const translated = translate(message, "en");
    if (translated !== message) return translated;
    if (message.startsWith("ไม่สามารถสร้างสูตรได้ เพราะมีวัตถุดิบที่ขัดกับอาการแพ้ของคุณ:")) return "Some selected ingredients conflict with your allergies. Remove them and try again.";
    if (message.startsWith("ไม่สามารถสร้างสูตรได้ เพราะหาสูตรที่ปลอดภัยกับอาการแพ้ของคุณไม่เจอ")) return "Could not find a recipe that passes your allergy checks. Change the ingredients and try again.";
    return translate("ไม่สามารถสร้างสูตรที่ผ่านการตรวจสอบได้ กรุณาลองใหม่อีกครั้งหรือเปลี่ยนวัตถุดิบ", "en");
}

export async function validateAllergyPreferences(apiFetch, preferences) {
    const unavailable = "ตรวจสอบอาการแพ้ไม่ได้ กรุณาลองกดสร้างเมนูอีกครั้ง";
    try {
        const response = await apiFetch("/api/validate-allergy-preferences", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ preferences }),
        });
        const result = await response.json();
        if (!response.ok) return unavailable;
        if (result.status === "success") return null;
        return result.code === "allergy_preferences_ambiguous"
            ? "กรุณาระบุอาหารที่แพ้ให้ชัดเจน เช่น แพ้กุ้ง หรือเลือกไม่มีอาการแพ้"
            : unavailable;
    } catch {
        return unavailable;
    }
}

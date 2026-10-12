// Keep Thai user-facing copy; hide raw provider/developer exceptions.
const THAI_CHAR = /[฀-๿]/;

export function toUserFacingGenerateError(message) {
    if (typeof message !== "string" || !THAI_CHAR.test(message)) return null;
    return message;
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

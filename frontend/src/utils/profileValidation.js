export const MAX_PROFILE_IMAGE_BYTES = 5 * 1024 * 1024;

export function isValidDisplayName(value) {
    const name = value.trim();
    return Array.from(name).length >= 1 && Array.from(name).length <= 50 && !Array.from(name).some(character => {
        const code = character.codePointAt(0);
        return code <= 31 || (code >= 127 && code <= 159);
    });
}

export function profileImageError(file) {
    if (!file || !["image/jpeg", "image/png", "image/webp"].includes(file.type)) return "profile_image_invalid";
    return file.size > MAX_PROFILE_IMAGE_BYTES ? "profile_image_too_large" : null;
}

export function profileErrorKey(code) {
    const messages = {
        profile_name_invalid: "ใช้ชื่อ 1–50 ตัวอักษร โดยไม่มีอักขระควบคุม",
        profile_image_invalid: "เลือกรูป JPG, PNG หรือ WebP ที่เปิดอ่านได้",
        profile_image_too_large: "รูปมีขนาดใหญ่เกินไป กรุณาเลือกรูปไม่เกิน 5 MB",
        profile_image_dimensions_invalid: "ครอปรูปเป็นสี่เหลี่ยมจัตุรัสแล้วลองใหม่",
        profile_image_action_invalid: "กรุณาเลือกรูปและยืนยันการครอปอีกครั้ง",
    };
    return Object.hasOwn(messages, code) ? messages[code] : "บันทึกโปรไฟล์ไม่สำเร็จ กรุณาลองอีกครั้ง";
}

export async function cropAvatar(image, area) {
    if (![area?.x, area?.y, area?.width, area?.height].every(Number.isFinite) || area.x < 0 || area.y < 0 || area.width <= 0 || area.height <= 0 || Math.abs(area.width - area.height) > 1 || area.x + area.width > image.naturalWidth + 1 || area.y + area.height > image.naturalHeight + 1) {
        throw new Error("Invalid crop area");
    }
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 512;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Canvas unavailable");
    context.fillStyle = "white";
    context.fillRect(0, 0, 512, 512);
    context.drawImage(image, area.x, area.y, area.width, area.height, 0, 0, 512, 512);
    return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error("Image export failed")), "image/jpeg", 0.85));
}

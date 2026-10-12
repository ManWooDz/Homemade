export function isValidBarcode(code) {
    return typeof code === "string" && /^\d{8,14}$/.test(code);
}

// The lookup endpoint can return raw provider exceptions; keep them out of the UI.
export function toUserFacingBarcodeError(message) {
    return message === "Product not found"
        ? "ยังไม่พบสินค้านี้ในฐานข้อมูล ตรวจเลขอีกครั้งหรือเพิ่มวัตถุดิบเองได้"
        : "ค้นหาสินค้าไม่สำเร็จ ลองค้นหาอีกครั้งหรือเพิ่มวัตถุดิบเองได้";
}

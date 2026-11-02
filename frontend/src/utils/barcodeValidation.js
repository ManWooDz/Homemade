export function isValidBarcode(code) {
    return typeof code === "string" && /^\d{8,14}$/.test(code);
}

export function createCameraBarcodeConfirmation() {
    let candidate = null;
    return (detectedCodes, source, frameId, now) => {
        const codes = [...new Set(detectedCodes.map(({ rawValue }) => rawValue).filter(isValidBarcode))];
        if (codes.length > 1) candidate = null;
        if (codes.length !== 1 || !["full", "finder"].includes(source) || !Number.isFinite(frameId) || !Number.isFinite(now)) return null;
        const code = codes[0];
        const lastFrame = candidate?.readers[source]?.frameId;
        if (!candidate || candidate.code !== code || now - candidate.startedAt > 1000 || frameId < lastFrame) {
            candidate = { code, startedAt: now, readers: {} };
        }
        const previous = candidate.readers[source];
        if (previous?.frameId === frameId) return null;
        const count = (previous?.count ?? 0) + 1;
        candidate.readers[source] = { frameId, count };
        // A full-frame result and its crop must never count as two independent reads.
        return count >= 3 ? code : null;
    };
}

// The lookup endpoint can return raw provider exceptions; keep them out of the UI.
export function toUserFacingBarcodeError(message) {
    return message === "Product not found"
        ? "ยังไม่พบสินค้านี้ในฐานข้อมูล ตรวจเลขอีกครั้งหรือเพิ่มวัตถุดิบเองได้"
        : "ค้นหาสินค้าไม่สำเร็จ ลองค้นหาอีกครั้งหรือเพิ่มวัตถุดิบเองได้";
}

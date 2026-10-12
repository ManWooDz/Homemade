import test from "node:test";
import assert from "node:assert/strict";
import { isValidBarcode, toUserFacingBarcodeError } from "../src/utils/barcodeValidation.js";

test("retail barcodes keep leading zeros and accept the endpoint length range", () => {
    for (const code of ["00000001", "012345678905", "8850999327015", "10012345678902"]) {
        assert.equal(isValidBarcode(code), true);
    }
});

test("short, long, non-ASCII, spaced and non-string barcodes are rejected", () => {
    for (const code of ["", "1", "1234567", "123456789012345", "๑๒๓๔๕๖๗๘", "1234 5678", "abcdefgh", "12345678\n", 12345678, null]) {
        assert.equal(isValidBarcode(code), false);
    }
});

test("not-found recovery is Thai and offers a manual route", () => {
    assert.match(toUserFacingBarcodeError("Product not found"), /ยังไม่พบสินค้า/);
    assert.match(toUserFacingBarcodeError("Product not found"), /เพิ่มวัตถุดิบเอง/);
});

test("provider and malformed errors never leak internal details", () => {
    for (const message of ["Could not reach Open Food Facts: private token", "internal traceback", undefined, null, {}]) {
        const copy = toUserFacingBarcodeError(message);
        assert.match(copy, /ค้นหาสินค้าไม่สำเร็จ/);
        assert.doesNotMatch(copy, /private|traceback|Open Food Facts/);
    }
});

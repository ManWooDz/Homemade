import test from "node:test";
import assert from "node:assert/strict";
import { binarizeBarcodeImage } from "../src/utils/barcodeImage.js";

test("barcode fallback preserves geometry and thresholds luminance at 160", () => {
    const image = { width: 2, height: 2, data: new Uint8ClampedArray([
        159, 159, 159, 255, 160, 160, 160, 255,
        0, 0, 0, 255, 255, 255, 255, 255,
    ]) };
    assert.equal(binarizeBarcodeImage(image), image);
    assert.deepEqual([image.width, image.height], [2, 2]);
    assert.deepEqual([...image.data], [
        0, 0, 0, 255, 255, 255, 255, 255,
        0, 0, 0, 255, 255, 255, 255, 255,
    ]);
});

test("barcode fallback uses color luminance rather than a single color channel", () => {
    const image = { data: new Uint8ClampedArray([
        255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255, 255, 255, 0, 255,
    ]) };
    binarizeBarcodeImage(image);
    assert.deepEqual([...image.data], [
        0, 0, 0, 255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255, 255,
    ]);
});

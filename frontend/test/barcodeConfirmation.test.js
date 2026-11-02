import test from "node:test";
import assert from "node:assert/strict";
import * as barcode from "../src/utils/barcodeValidation.js";

const wrong = "0878888581023";
const correct = "8858998581023";
const result = code => [{ rawValue: code }];
const reader = () => {
    assert.equal(typeof barcode.createCameraBarcodeConfirmation, "function");
    return barcode.createCameraBarcodeConfirmation();
};

test("one checksum-valid misread cannot trigger camera acceptance", () => {
    const observe = reader();
    assert.equal(observe(result(wrong), "finder", 1, 0), null);
});

test("camera accepts three matching observations with advancing playback markers", () => {
    const observe = reader();
    assert.equal(observe(result(correct), "finder", 10, 0), null);
    assert.equal(observe(result(correct), "finder", 11, 150), null);
    assert.equal(observe(result(correct), "finder", 12, 300), correct);
});

test("confirmed reads preserve leading zeros without restricting country prefixes", () => {
    const observe = reader();
    assert.equal(observe(result(wrong), "full", 1, 0), null);
    assert.equal(observe(result(wrong), "full", 2, 150), null);
    assert.equal(observe(result(wrong), "full", 3, 300), wrong);
});

test("duplicate playback markers and the two readers cannot manufacture confirmation", () => {
    const observe = reader();
    assert.equal(observe(result(correct), "full", 10, 0), null);
    assert.equal(observe(result(correct), "finder", 10, 10), null);
    assert.equal(observe(result(correct), "full", 10, 150), null);
    assert.equal(observe(result(correct), "finder", 11, 160), null);
    assert.equal(observe(result(correct), "full", 11, 300), null);
    assert.equal(observe(result(correct), "full", 12, 450), correct);
});

test("a conflicting read resets accumulated confirmation", () => {
    const observe = reader();
    observe(result(wrong), "finder", 1, 0);
    observe(result(wrong), "finder", 2, 150);
    assert.equal(observe(result(correct), "full", 3, 200), null);
    assert.equal(observe(result(correct), "full", 4, 350), null);
    assert.equal(observe(result(correct), "full", 5, 500), correct);
});

test("stale observations and a restarted frame counter cannot confirm", () => {
    const observe = reader();
    observe(result(correct), "full", 30, 0);
    observe(result(correct), "full", 31, 150);
    assert.equal(observe(result(correct), "full", 32, 1100), null);
    assert.equal(observe(result(correct), "full", 1, 1250), null);
    assert.equal(observe(result(correct), "full", 2, 1400), null);
    assert.equal(observe(result(correct), "full", 3, 1550), correct);
});

test("an empty crop does not prevent whole-frame confirmation outside the finder", () => {
    const observe = reader();
    observe(result(correct), "full", 1, 0);
    observe([], "finder", 1, 50);
    observe(result(correct), "full", 2, 150);
    observe([], "finder", 2, 200);
    assert.equal(observe(result(correct), "full", 3, 300), correct);
});

test("ambiguous codes reset confidence and invalid frame metadata cannot confirm", () => {
    const observe = reader();
    observe(result(correct), "full", 1, 0);
    observe(result(correct), "full", 2, 150);
    assert.equal(observe([...result(correct), ...result(wrong)], "finder", 3, 200), null);
    assert.equal(observe(result(correct), "full", 4, 300), null);
    assert.equal(observe(result(correct), "full", undefined, 400), null);
    assert.equal(observe(result(correct), "full", 5, 450), null);
    assert.equal(observe(result(correct), "full", 6, 600), correct);
});

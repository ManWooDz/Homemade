import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const addIngredient = readFileSync(
    new URL("../src/pages/AddIngredient.jsx", import.meta.url),
    "utf8",
);
const userIngredients = readFileSync(
    new URL("../src/pages/UserIngredients.jsx", import.meta.url),
    "utf8",
);

test("Add Ingredient has no stock amount state or control", () => {
    assert.doesNotMatch(addIngredient, /quantityAmount|quantityUnit|unitOptions/);
    assert.doesNotMatch(addIngredient, /Quantity Input|>\s*Quantity\s*</);
});

test("My Fridge does not display a quantity label", () => {
    assert.doesNotMatch(userIngredients, /Qty:|ing\.quantity/);
});

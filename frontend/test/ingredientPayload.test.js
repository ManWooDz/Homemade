import test from "node:test";
import assert from "node:assert/strict";

import {
  toPresenceIngredients,
  toUserIngredientCreate,
} from "../src/utils/ingredientPayload.js";
import * as ingredientPayload from "../src/utils/ingredientPayload.js";

test("a deliberate fridge selection replaces a matching catalog or fridge source and keeps the displayed binding revision", () => {
  const catalog = [{ id: 7, name: "นมจืด" }, { id: 8, name: "ไข่" }];
  const milkA = { id: 7, name: " นมจืด ", barcode_product: { revision: "milk-a", name: "Milk A" } };
  const milkB = { id: 9, name: "นมจืด", barcode_product: { revision: "milk-b", name: "Milk B" } };
  const selected = ingredientPayload.selectFridgeIngredient(catalog, milkA);
  assert.deepEqual(toPresenceIngredients(selected), [
    { name: "นมจืด", fridge_ingredient_id: 7, fridge_binding_revision: "milk-a" },
    { id: 8, name: "ไข่" },
  ]);
  assert.deepEqual(toPresenceIngredients(ingredientPayload.selectFridgeIngredient(selected, milkB)), [
    { name: "นมจืด", fridge_ingredient_id: 9, fridge_binding_revision: "milk-b" },
    { id: 8, name: "ไข่" },
  ]);
  assert.deepEqual(toPresenceIngredients(ingredientPayload.selectFridgeIngredient([], { id: 2, name: "ไข่" })), [
    { name: "ไข่", fridge_ingredient_id: 2, fridge_binding_revision: null },
  ]);
  assert.deepEqual(toPresenceIngredients(ingredientPayload.selectFridgeIngredient([
    { id: 14, name: "minced pork" },
  ], { id: 42, name: "หมูสับ" })), [
    { name: "หมูสับ", fridge_ingredient_id: 42, fridge_binding_revision: null },
  ]);
});

test("a confirmed barcode is sent as a string including its leading zero", () => {
  const input = { name: "milk", barcodeCode: "01234567" };
  assert.equal(toUserIngredientCreate(input).barcode_code, "01234567");
  assert.equal(Object.hasOwn(toUserIngredientCreate({ ...input, barcodeCode: null }), "barcode_code"), false);
});

test("generation payload keeps identity and removes stock metadata", () => {
  const result = toPresenceIngredients([
    {
      id: 7,
      name: "  minced pork  ",
      category: "Meat & Poultry",
      quantity: "250 grams (กรัม)",
      image: "pork.png",
      selected: true,
    },
  ]);

  assert.deepEqual(result, [{ id: 7, name: "minced pork" }]);
  assert.equal("quantity" in result[0], false);
  assert.equal("image" in result[0], false);
});

test("generation payload accepts legacy string ingredients", () => {
  assert.deepEqual(toPresenceIngredients([" egg "]), [{ name: "egg" }]);
});

test("empty ingredient names are rejected", () => {
  assert.throws(() => toPresenceIngredients([{ id: 1, name: " " }]), {
    name: "TypeError",
    message: "Ingredient name is required",
  });
});

test("fridge create payload excludes quantity", () => {
  const result = toUserIngredientCreate({
    name: "  egg ",
    category: "Other",
    image: "egg.png",
    quantity: "12 pieces",
  });

  assert.deepEqual(result, {
    name: "egg",
    category: "Other",
    image: "egg.png",
  });
});

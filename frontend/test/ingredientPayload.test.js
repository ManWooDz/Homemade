import test from "node:test";
import assert from "node:assert/strict";

import {
  toPresenceIngredients,
  toUserIngredientCreate,
} from "../src/utils/ingredientPayload.js";

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

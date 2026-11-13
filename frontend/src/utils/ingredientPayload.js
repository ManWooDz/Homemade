import { normalizeForSearch } from "./thaiText.js";
import { formatIngredientName } from "./translations.js";

function cleanIngredientName(value) {
  const name = typeof value === "string" ? value.trim() : "";
  if (!name) {
    throw new TypeError("Ingredient name is required");
  }
  return name;
}

export function selectFridgeIngredient(items, item) {
  const displayedName = (ingredient) => normalizeForSearch(formatIngredientName(ingredient.name.trim(), "th"));
  const name = displayedName(item);
  const selected = {
    ...item,
    id: `fridge-${item.id}`,
    fridge_ingredient_id: item.id,
    fridge_binding_revision: item.barcode_product?.revision ?? null,
  };
  const replaces = (candidate) => candidate.fridge_ingredient_id === item.id || displayedName(candidate) === name;
  const index = items.findIndex(replaces);
  if (index === -1) return [...items, selected];
  return [...items.slice(0, index), selected, ...items.slice(index + 1).filter((candidate) => !replaces(candidate))];
}

export function isSelectedFridgeIngredient(items, item) {
  return items.some((selected) => selected.fridge_ingredient_id === item.id
    && selected.name === item.name && selected.fridge_binding_revision === (item.barcode_product?.revision ?? null));
}

export function barcodeProductDescription(product) {
  if (!product) return "";
  const suffix = product.barcode?.slice(-4);
  return [product.name, suffix && `…${suffix}`].filter(Boolean).join(" · ");
}

export function toPresenceIngredients(items = []) {
  if (!Array.isArray(items)) {
    throw new TypeError("Ingredients must be an array");
  }

  return items.map((item) => {
    if (typeof item === "string") {
      return { name: cleanIngredientName(item) };
    }

    const result = { name: cleanIngredientName(item?.name) };
    if (item.fridge_ingredient_id != null) {
      return {
        ...result,
        fridge_ingredient_id: item.fridge_ingredient_id,
        fridge_binding_revision: item.fridge_binding_revision ?? null,
      };
    }
    if (item?.id !== undefined && item?.id !== null) {
      return { id: item.id, ...result };
    }
    return result;
  });
}

export function toUserIngredientCreate({
  name,
  category,
  image,
  expiryDate,
  nutritionData,
  quantityAmount,
  quantityUnit,
  barcodeCode,
}) {
  // "" from an empty number input/select must become null, not "" or NaN —
  // same 422 trap as expiry_date. Number("") is 0 (a real, wrong value), so
  // this can't just be `Number(quantityAmount) || null`.
  const trimmedAmount =
    typeof quantityAmount === "string" ? quantityAmount.trim() : quantityAmount;
  const parsedAmount =
    trimmedAmount === "" || trimmedAmount == null ? null : Number(trimmedAmount);
  return {
    name: cleanIngredientName(name),
    category: category || "Other",
    image,
    // An empty string from <input type="date"> must become null, not "" —
    // Pydantic's `date` type 422s on "", and apiFetch doesn't throw on
    // non-2xx, so that would otherwise fail the save silently.
    expiry_date: expiryDate || null,
    // Passed straight through from a barcode-lookup response, or null when
    // manually added — never user-editable, so no client-side shaping here.
    nutrition_data: nutritionData || null,
    quantity_amount: parsedAmount,
    // Backend rejects a unit with no amount (422) -- drop the unit here too
    // if there's no amount, so the UI's own state can't produce that
    // invalid combination on save.
    quantity_unit: parsedAmount == null ? null : quantityUnit || null,
    ...(barcodeCode ? { barcode_code: barcodeCode } : {}),
  };
}

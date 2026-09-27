function cleanIngredientName(value) {
  const name = typeof value === "string" ? value.trim() : "";
  if (!name) {
    throw new TypeError("Ingredient name is required");
  }
  return name;
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
  };
}

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

export function toUserIngredientCreate({ name, category, image, expiryDate }) {
  return {
    name: cleanIngredientName(name),
    category: category || "Other",
    image,
    // An empty string from <input type="date"> must become null, not "" —
    // Pydantic's `date` type 422s on "", and apiFetch doesn't throw on
    // non-2xx, so that would otherwise fail the save silently.
    expiry_date: expiryDate || null,
  };
}

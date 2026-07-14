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

export function toUserIngredientCreate({ name, category, image }) {
  return {
    name: cleanIngredientName(name),
    category: category || "Other",
    image,
  };
}

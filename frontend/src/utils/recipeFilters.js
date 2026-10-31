export function recipeIngredients(recipe) {
    return (recipe.ingredients?.length ? recipe.ingredients : recipe.adjusted_ingredients || []).map((ingredient) =>
        typeof ingredient === "string" ? { name: ingredient } : ingredient,
    );
}

function normalizeTag(tag) {
    const key = tag.trim().toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ");
    return ({ "thai food": "thai", "japanese food": "japanese", japan: "japanese", "glutan free": "gluten free" })[key] || key;
}

export function matchesRecipeFilters(recipe, { ingredientNames = [], mealType = [], dietary = [], cuisine = [], occasion = [] } = {}) {
    const names = recipeIngredients(recipe).map((ingredient) => (ingredient.name || "").trim().toLowerCase());
    const recipeTags = [...(recipe.tags || []), ...(recipe.diet_tags || [])].map(normalizeTag);
    return (!ingredientNames.length || ingredientNames.some((name) => names.includes(name.trim().toLowerCase()))) &&
        [mealType, dietary, cuisine, occasion].every((group) =>
            !group.length || group.some((tag) => recipeTags.includes(normalizeTag(tag))),
        );
}

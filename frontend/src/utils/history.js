import { normalizeForSearch } from "./thaiText.js";

export function filterHistory(history, { query, favorite, rating }) {
    const search = normalizeForSearch(query);
    // shortcut: search covers loaded history only; add server search with pagination when needed.
    return history.filter(item =>
        (favorite !== "favorites" || item.is_favorite) &&
        (rating === "all" || (item.stars || 0) === (rating === "unrated" ? 0 : Number(rating))) &&
        (!search || [item.recipe_name, ...(item.adjusted_ingredients || [])]
            .some(text => typeof text === "string" && normalizeForSearch(text).includes(search)))
    );
}

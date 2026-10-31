import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { matchesRecipeFilters, recipeIngredients } from "../src/utils/recipeFilters.js";

test("recipe filters match ANY ingredient and ANY choice within each required category", () => {
    const recipe = { ingredients: [{ name: " Chicken " }], tags: ["Thai", "Dinner"] };
    assert.equal(matchesRecipeFilters(recipe), true);
    assert.equal(matchesRecipeFilters(recipe, { ingredientNames: ["egg", "chicken"], cuisine: ["Japan", "Thai"], mealType: ["Lunch", "Dinner"] }), true);
    assert.equal(matchesRecipeFilters(recipe, { ingredientNames: ["egg"], cuisine: ["Thai"] }), false);
    assert.equal(matchesRecipeFilters(recipe, { ingredientNames: ["chicken"], dietary: ["Vegan"] }), false);
    assert.equal(matchesRecipeFilters(recipe, { ingredientNames: ["chick"] }), false);
});

test("saved generated recipes use their stored ingredient labels and dietary tags without guessing metadata", () => {
    const recipe = { adjusted_ingredients: ["ไข่ไก่ 2 ฟอง", "น้ำปลา 1 ช้อนชา"], diet_tags: ["Thai"] };
    assert.deepEqual(recipeIngredients(recipe), [{ name: "ไข่ไก่ 2 ฟอง" }, { name: "น้ำปลา 1 ช้อนชา" }]);
    assert.equal(matchesRecipeFilters(recipe, { ingredientNames: ["ไข่ไก่ 2 ฟอง"], cuisine: ["Thai"] }), true);
    assert.equal(matchesRecipeFilters(recipe, { ingredientNames: ["ไข่ไก่"] }), false);
    assert.equal(matchesRecipeFilters(recipe, { mealType: ["Dinner"] }), false);
    assert.equal(matchesRecipeFilters({}, { cuisine: ["Thai"] }), false);
    assert.equal(matchesRecipeFilters({}), true);
});

test("each selected category must match, rather than allowing cuisine to bypass dietary", () => {
    assert.equal(matchesRecipeFilters({ tags: ["Thai Food", "Dinner"] }, {
        cuisine: ["Thai"], mealType: ["Dinner"], dietary: ["Vegan"],
    }), false);
    assert.equal(matchesRecipeFilters({ tags: ["Thai Food", "Dinner", "Vegan"] }, {
        cuisine: ["Thai"], mealType: ["Dinner"], dietary: ["Vegan"],
    }), true);
});

test("catalog cuisine tags and explicit spelling variants match the Figma choices", () => {
    for (const [stored, choice] of [["Thai Food", "Thai"], ["Japanese Food", "Japan"],
        ["Japanese", "Japan"], ["Gluten-Free", "Glutan Free"], ["low_carb", "Low Carb"], ["Kid-Friendly", "Kid-Friendly"]]) {
        assert.equal(matchesRecipeFilters({ tags: [stored] }, { cuisine: [choice] }), true, stored);
    }
    assert.equal(matchesRecipeFilters({ tags: ["Western Food"] }, { cuisine: ["British"] }), false);
    assert.equal(matchesRecipeFilters({ tags: ["Healthy / Diet"] }, { dietary: ["Vegan"] }), false);
});

test("empty catalog fields do not hide stored generated ingredients or dietary metadata", () => {
    const recipe = { ingredients: [], adjusted_ingredients: ["egg"], tags: [], diet_tags: ["Vegan"] };
    assert.equal(matchesRecipeFilters(recipe, { ingredientNames: ["egg"], dietary: ["Vegan"] }), true);
    assert.equal(matchesRecipeFilters(recipe, { occasion: ["Picnic"] }), false);
});

test("actual base-menu seed tags enable the approved meal and occasion filters", () => {
    const source = readFileSync(new URL("../../backend/database/seed_postgres.py", import.meta.url), "utf8");
    const recipes = [...source.matchAll(/ {8}"name": ("[^"\r\n]*")[\s\S]*? {8}"tags": (\[[^\r\n]*\])/g)]
        .map(([, name, tags]) => ({ name: JSON.parse(name), tags: JSON.parse(tags) }));
    assert.equal(recipes.length, 9);
    const names = (filters) => recipes.filter((recipe) => matchesRecipeFilters(recipe, filters)).map((recipe) => recipe.name);
    assert.equal(names({ mealType: ["Lunch"] }).length, 9);
    assert.equal(names({ mealType: ["Dinner"] }).length, 9);
    assert.deepEqual(names({ mealType: ["Brunch"] }), ["Superfood Veggie", "Fresh Power Salad", "Greek Salad"]);
    assert.deepEqual(names({ occasion: ["Picnic"] }), ["Superfood Veggie", "Fresh Power Salad", "Rainbow Healthy", "Greek Salad"]);
    assert.deepEqual(names({ occasion: ["Date Night"] }), ["Grilled Steak"]);
    assert.equal(names({ cuisine: ["Thai"], mealType: ["Lunch"] }).length, 3);
    assert.deepEqual(names({ cuisine: ["Japan"], mealType: ["Dinner"] }), ["Chashu Ramen"]);
    assert.deepEqual(names({ cuisine: ["Thai"], occasion: ["Picnic"] }), []);
    assert.deepEqual(names({ dietary: ["Vegan"] }), []);
});

import math


def _read_name(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("name")
    return getattr(item, "name", None)


def ingredient_names(items):
    names = []
    for item in items:
        raw_name = _read_name(item)
        name = raw_name.strip() if isinstance(raw_name, str) else ""
        if not name:
            raise ValueError("Ingredient name is required")
        names.append(name)
    return names


def validate_generated_recipe_shape(recipe):
    if not isinstance(recipe, dict):
        return False, "Invalid recipe"

    recipe_name = recipe.get("recipe_name")
    if not isinstance(recipe_name, str) or not recipe_name.strip():
        return False, "Invalid recipe name"

    servings = recipe.get("servings")
    if isinstance(servings, bool) or not isinstance(servings, int) or servings < 1:
        return False, "Invalid servings"

    ingredients = recipe.get("adjusted_ingredients")
    if (
        not isinstance(ingredients, list)
        or not ingredients
        or any(not isinstance(item, str) or not item.strip() for item in ingredients)
    ):
        return False, "Invalid adjusted ingredients"

    instructions = recipe.get("instructions")
    if (
        not isinstance(instructions, list)
        or not instructions
        or any(not isinstance(item, str) or not item.strip() for item in instructions)
    ):
        return False, "Invalid instructions"

    diet_tags = recipe.get("diet_tags")
    if not isinstance(diet_tags, list) or any(
        not isinstance(tag, str) or not tag.strip() for tag in diet_tags
    ):
        return False, "Invalid diet tags"

    safety_warning = recipe.get("safety_warning")
    if not isinstance(safety_warning, str) or not safety_warning.strip():
        return False, "Invalid safety warning"

    nutrition = recipe.get("nutrition")
    if not isinstance(nutrition, dict) or nutrition.get("basis") != "per_serving":
        return False, "Invalid nutrition basis"

    for nutrient in ("calories", "protein_g", "carbs_g", "fat_g"):
        value = nutrition.get(nutrient)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            return False, f"Invalid nutrition value: {nutrient}"

    return True, "OK"

# backend/nutrition/calculator.py
"""Generated recipes retain usable estimates with uncertainty reasons.
The base-seed numeric helper raises for unresolved or invalid inputs;
neither an exact alias nor a hardcoded zero certifies grounding."""
from dataclasses import dataclass, field, replace
import re

from barcode_nutrition import product_contribution
from nutrition.curated_aliases import ZERO_NUTRITION_CONSTANTS
from nutrition.evidence import qualify_match
from nutrition.lookup import MacroValues, match_ingredient
from nutrition.parser import parse_ingredient_string
from nutrition.text import normalize_alias
from nutrition.units import is_nonnegative_finite, resolve_grams_detailed, resolve_product_quantity

_MACRO_KEYS = ("calories", "protein_g", "carbs_g", "fat_g")
_RECIPE_VOLUME_SUFFIX = re.compile(r"(?<=\d)\s*([mcd]?l)\s*$", re.I)


@dataclass
class NutritionResult:
    nutrition: dict
    partially_estimated: bool
    partially_estimated_reasons: list[str]
    ingredient_evidence: list[dict] = field(default_factory=list)


def _has_deep_fry(instructions: list[str]) -> bool:
    for line in instructions:
        if "ทอด" in line.replace("ผัดทอด", "").replace("ผัด", ""):
            return True
    return False


def _accumulate_macros(totals: dict, macros: MacroValues, factor: float) -> None:
    for key in _MACRO_KEYS:
        value = getattr(macros, key)
        if is_nonnegative_finite(value):
            contribution = value * factor
            total = (totals[key] or 0.0) + contribution
            if not is_nonnegative_finite(contribution) or not is_nonnegative_finite(total):
                raise ValueError(f"nutrition arithmetic overflow: {key}")
            totals[key] = total


def _add_contribution(totals: dict, macros: MacroValues, quantity_g: float) -> None:
    _accumulate_macros(totals, macros, quantity_g / 100.0)


def _missing_macro_keys(macros: MacroValues) -> list[str]:
    return [key for key in _MACRO_KEYS if not is_nonnegative_finite(getattr(macros, key))]


def _check_servings(servings) -> None:
    if not is_nonnegative_finite(servings) or servings == 0:
        raise ValueError("servings must be a positive finite number")


def _per_serving_nutrition(totals: dict, servings) -> dict:
    values = {key: total / servings if total is not None else None for key, total in totals.items()}
    if any(value is not None and not is_nonnegative_finite(value) for value in values.values()):
        raise ValueError("per-serving nutrition arithmetic overflow")
    return {"basis": "per_serving", **{key: round(value, 1) if value is not None else None
                                        for key, value in values.items()}}


def _zero_nutrition_constant(name: str) -> MacroValues | None:
    return ZERO_NUTRITION_CONSTANTS.get(normalize_alias(name))


def compute_recipe_nutrition(db, adjusted_ingredients, instructions, servings, llm_estimator,
                             *, fridge_context=None) -> NutritionResult:
    _check_servings(servings)
    totals = dict.fromkeys(_MACRO_KEYS, None if fridge_context is not None else 0.0)
    reasons: list[str] = []
    pending_llm_estimate: list[tuple[str, float, dict]] = []
    ingredient_evidence: list[dict] = []

    if not adjusted_ingredients:
        reasons.append("no ingredient evidence: empty ingredient list")
    for raw in adjusted_ingredients:
        binding, fallback = (fridge_context or {}).get(raw, (None, None))
        volume_suffix = _RECIPE_VOLUME_SUFFIX.search(raw) if binding else None
        if volume_suffix:
            item = parse_ingredient_string(raw[:volume_suffix.start()] + " มล.")
            volume = resolve_product_quantity(item.quantity, volume_suffix[1])
            item = replace(item, raw=raw, quantity=volume[0] if volume else None)
        else:
            item = parse_ingredient_string(raw)
        trace = {"ingredient": item.name, "raw": raw, "source": "unresolved", "status": "incomplete"}
        if fridge_context is not None:
            ingredient_evidence.append(trace)
        if binding:
            trace.update(barcode=binding["barcode"], product_name=binding["product_name"])
            if fallback is None:
                label, fallback = product_contribution(binding, item.quantity, item.unit)
                if label:
                    _accumulate_macros(totals, MacroValues(**label["contribution"]), 1)
                    trace.update(label, status="calculated")
                    continue
        if fallback:
            trace["reason"] = fallback
            reasons.append(f"{fallback}: {item.name}")

        constant = _zero_nutrition_constant(item.name)
        if constant is not None:
            trace.update(source="hardcoded_zero", status="estimated")
            reasons.append(f"hardcoded zero composition; identity/source unverified: {item.name}")
            resolution = resolve_grams_detailed(item.quantity, item.unit, None)
            if resolution.grams is None:
                trace.update(status="incomplete")
                reasons.append(f"quantity not determined: {item.raw}")
            elif resolution.source_backed is not True:
                reasons.append(f"gram conversion {resolution.method}; source unverified or estimated: {item.name}")
            if resolution.grams is not None:
                trace.update(converted_quantity={"amount": resolution.grams, "unit": "g"}, method=resolution.method)
            continue

        if item.parse_status == "unparsed":
            reasons.append(f"quantity not determined: {item.raw}")
            continue

        match = match_ingredient(db, item.name)
        qualification = qualify_match(item.name, match) if match else None
        portion_grams = match.portion_grams if match else None
        resolution = resolve_grams_detailed(item.quantity, item.unit, portion_grams,
                                           verified_portion_grams=qualification.verified_portion_grams if qualification else None)
        quantity_g = resolution.grams
        if quantity_g is not None and resolution.source_backed is not True:
            reasons.append(f"gram conversion {resolution.method}; source unverified or estimated: {item.name}")

        if match is not None and quantity_g is not None:
            row_is_verified = qualification.identity_verified and qualification.macros_verified
            if not row_is_verified:
                reasons.append(f"DB identity/composition source unverified: {item.name}")
            # Portion uncertainty is reported for the selected conversion, not unused units.
            reasons.extend(f"{reason}: {item.name}" for reason in qualification.reasons
                           if not reason.startswith("nutrition evidence portion"))
            derivation = match.derivation if isinstance(match.derivation, dict) else {}
            if "proxy" in derivation:
                reasons.append(f"proxy composition ({derivation['proxy']}): {item.name}")
            for key in ("energy_kcal", "carbs_g"):
                if key in derivation:
                    reasons.append(f"project-filled {key} ({derivation[key]}): {item.name}")
            if match.unit_basis != "100g":
                reasons.append(f"unsupported macro basis {match.unit_basis!r}; contribution skipped: {item.name}")
                continue
            _add_contribution(totals, match.macros, quantity_g)
            missing = _missing_macro_keys(match.macros)
            status = "estimated"
            if missing:
                status = "incomplete"
            elif row_is_verified and resolution.source_backed is True and not fallback:
                status = "calculated"
            trace.update(
                source=match.source, source_ref=match.source_ref, basis={"quantity": 100, "unit": "g"},
                converted_quantity={"amount": quantity_g, "unit": "g"}, method=resolution.method,
                status=status,
            )
            if missing:
                reasons.append(f"missing or invalid {', '.join(missing)} in DB row {match.source_ref}: {item.name}")
            continue
        if match is None and quantity_g is not None:
            trace.update(converted_quantity={"amount": quantity_g, "unit": "g"}, method=resolution.method)
            pending_llm_estimate.append((item.name, quantity_g, trace))
            continue
        reasons.append(f"quantity or ingredient not resolved: {item.raw}")

    if pending_llm_estimate:
        names = [name for name, _, _ in pending_llm_estimate]
        estimates = iter(llm_estimator.estimate(names))
        for name, quantity_g, trace in pending_llm_estimate:
            macros = next(estimates, MacroValues(None, None, None, None))
            _add_contribution(totals, macros, quantity_g)
            missing = _missing_macro_keys(macros)
            if len(missing) == len(_MACRO_KEYS):
                # No key / API error / malformed reply: nothing was actually
                # estimated, so don't word it as if an estimate happened.
                reasons.append(f"could not estimate composition (no usable LLM result): {name}")
            else:
                trace.update(source="llm_estimate", basis={"quantity": 100, "unit": "g"},
                             status="incomplete" if missing else "estimated")
                reasons.append(f"LLM_ESTIMATE composition: {name}")

    if _has_deep_fry(instructions):
        reasons.append("deep-fry (ทอด): oil absorption not modeled, fat/kcal may be overcounted")

    return NutritionResult(
        nutrition=_per_serving_nutrition(totals, servings),
        partially_estimated=len(reasons) > 0,
        partially_estimated_reasons=reasons,
        ingredient_evidence=ingredient_evidence,
    )


def compute_quantities_nutrition(db, quantities: list[dict], servings: int) -> NutritionResult:
    _check_servings(servings)
    if not isinstance(quantities, list) or not quantities:
        raise ValueError("explicit ingredient quantities are required")
    totals = {key: 0.0 for key in _MACRO_KEYS}
    unmatched: list[str] = []
    incomplete: list[str] = []
    reasons: list[str] = []

    for entry in quantities:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not entry["name"].strip():
            raise ValueError("ingredient name is required")
        if "quantity_g" not in entry:
            raise ValueError("explicit gram quantity is required")
        name, quantity_g = entry["name"], entry["quantity_g"]
        if not is_nonnegative_finite(quantity_g):
            raise ValueError(f"invalid gram quantity: {name}")
        constant = _zero_nutrition_constant(name)
        if constant is not None:
            _add_contribution(totals, constant, quantity_g)
            reasons.append("constant_unverified")
            continue

        match = match_ingredient(db, name)
        if match is None:
            unmatched.append(name)
            continue
        if match.unit_basis != "100g":
            incomplete.append(f"{name} (unsupported macro basis {match.unit_basis!r})")
            continue
        missing = _missing_macro_keys(match.macros)
        if missing:
            # Same policy as an unmatched name: an incomplete DB row would
            # silently undercount the missing macro(s) as 0.
            incomplete.append(f"{name} (row {match.source_ref} missing or invalid {', '.join(missing)})")
            continue
        qualification = qualify_match(name, match)
        if not (qualification.identity_verified and qualification.macros_verified):
            reasons.append("source_unverified")
        derivation = match.derivation if isinstance(match.derivation, dict) else {}
        if "proxy" in derivation:
            reasons.append("proxy_composition")
        if "energy_kcal" in derivation or "carbs_g" in derivation:
            reasons.append("derived_macros")
        _add_contribution(totals, match.macros, quantity_g)

    if unmatched or incomplete:
        raise ValueError(
            f"base-recipe ingredient(s) not found in ingredient_nutrition: {unmatched}; "
            f"matched but with incomplete/invalid macro data: {incomplete} "
            "-- add a curated alias (nutrition/data/curated_aliases.json) or a USDA search "
            "term (or point the alias at a complete row) before seeding base recipes; "
            "silently contributing 0 here would repeat the original hand-typed-nutrition problem."
        )

    return NutritionResult(
        nutrition=_per_serving_nutrition(totals, servings),
        partially_estimated=bool(reasons),
        partially_estimated_reasons=list(dict.fromkeys(reasons)),
    )


def compute_from_quantities(db, quantities: list[dict], servings: int) -> dict:
    return compute_quantities_nutrition(db, quantities, servings).nutrition

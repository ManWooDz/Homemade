"""All source/reviewer/receipt claims below are synthetic, never real evidence."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import unittest
from unittest.mock import patch

from nutrition.evidence import qualify_match
from nutrition.lookup import MacroValues, NutritionMatch
from nutrition.text import normalize_alias


def synthetic_match(alias="sample", full_name="sample, raw", portions=None, basis="100g", markers=None):
    """Reusable test-only receipt; example.invalid is deliberately not retrieved."""
    review = {"status": "accepted", "reviewer": "synthetic-reviewer",
              "reviewed_at_utc": "2000-01-01T00:00:00Z", "receipt_ref": "synthetic-only",
              "receipt_sha256": "a" * 64}
    citation = {"publisher": "Synthetic source, not a publisher", "source": "INMU",
                "source_ref": "SYN1", "release": "synthetic-v1", "url": "https://example.invalid/record",
                "artifact_sha256": "b" * 64, "locator": "synthetic table/field",
                "extraction": "Synthetic independently reviewed extraction"}
    values = {"calories": 100.0, "protein_g": 5.0, "carbs_g": 10.0, "fat_g": 1.0}
    derivation = deepcopy(markers or {})
    evidence = {
        "schema_version": 1, "review": review,
        "row_binding": {"source": "INMU", "source_ref": "SYN1", "ingredient_name": full_name,
                        "unit_basis": basis, "macros": values, "portion_grams": deepcopy(portions or {}),
                        "estimate_markers": deepcopy(derivation)},
        "identity": [{"alias": normalize_alias(alias), "relation": "exact", "ingredient_name": full_name,
                      "preparation": "raw", "rationale": "Synthetic exact identity review",
                      "citation": deepcopy(citation), "review": deepcopy(review)}],
        "macros": [{"key": key, "value": value, "unit": "kcal" if key == "calories" else "g",
                    "basis": basis, "definition": definition, "origin": "source_published",
                    "source_field": "synthetic-" + key, "citation": deepcopy(citation), "review": deepcopy(review)}
                   for (key, value), definition in zip(values.items(), ("energy", "protein", "total_carbohydrate", "total_fat"))],
        "portions": [],
    }
    for unit, factor in (portions or {}).items():
        evidence["portions"].append({
            "unit": unit, "portion_id": "synthetic-portion", "description": "Synthetic size, raw",
            "source_ingredient_name": "synthetic source ingredient", "source_preparation": "raw",
            "source_unit": "synthetic count", "amount": 2, "gram_weight": factor * 2,
            "grams_per_unit": factor, "method": "gram_weight/amount",
            "target": {"source": "INMU", "source_ref": "SYN1", "ingredient_name": full_name, "preparation": "raw"},
            "equivalence": {"relation": "exact", "rationale": "Synthetic cross-source equivalence"},
            "unit_mapping": {"source_unit": "synthetic count", "runtime_unit": unit, "rationale": "Synthetic unit mapping"},
            "citation": {**deepcopy(citation), "source": "USDA", "source_ref": "SYN-P1", "locator": "synthetic portion"},
            "review": deepcopy(review),
        })
    derivation["nutrition_evidence"] = evidence
    return NutritionMatch(1, MacroValues(**values), "INMU", "SYN1", derivation, deepcopy(portions), basis, full_name)


class QualifyMatchTests(unittest.TestCase):
    def setUp(self):
        self.match = synthetic_match(portions={"ฟอง": 50})
        self.evidence = self.match.derivation["nutrition_evidence"]

    def qualification(self, name="sample"):
        return qualify_match(name, self.match)

    def assert_unknown(self):
        result = self.qualification()
        self.assertFalse(result.identity_verified)
        self.assertFalse(result.macros_verified)
        self.assertEqual(dict(result.verified_portion_grams), {})

    def test_complete_synthetic_binding_and_cross_source_portion(self):
        result = self.qualification()
        self.assertTrue(result.identity_verified)
        self.assertTrue(result.macros_verified)
        self.assertEqual(dict(result.verified_portion_grams), {"ฟอง": 50})
        self.assertEqual(result.reasons, ())

    def test_legacy_constructor_and_missing_evidence_stay_unknown(self):
        self.match.derivation = None
        self.assert_unknown()
        self.match.ingredient_name = None
        self.assert_unknown()

    def test_source_ref_name_and_basis_drift_invalidate_all(self):
        for key, value in (("source", "USDA"), ("source_ref", "SYN2"),
                           ("ingredient_name", "sample, cooked"), ("unit_basis", "100ml")):
            with self.subTest(key=key):
                match = synthetic_match(portions={"ฟอง": 50})
                setattr(match, key, value)
                result = qualify_match("sample", match)
                self.assertFalse(result.identity_verified or result.macros_verified or result.verified_portion_grams)

    def test_macro_and_portion_drift_invalidate_binding(self):
        self.match.macros.protein_g = 7
        self.assert_unknown()
        self.match = synthetic_match(portions={"ฟอง": 50})
        self.match.portion_grams["ฟอง"] = 55
        self.assert_unknown()

    def test_bool_missing_nonfinite_and_negative_binding_values(self):
        for value in (True, "100", -1, float("inf"), float("nan"), 10 ** 400):
            with self.subTest(value=value):
                self.match = synthetic_match()
                self.match.macros.calories = value
                self.match.derivation["nutrition_evidence"]["row_binding"]["macros"]["calories"] = value
                self.assert_unknown()

    def test_complete_macros_do_not_verify_another_alias(self):
        result = self.qualification("another sample")
        self.assertFalse(result.identity_verified)
        self.assertTrue(result.macros_verified)
        self.assertEqual(dict(result.verified_portion_grams), {})

    def test_normalization_only_no_semantic_alias_expansion(self):
        self.assertTrue(self.qualification(" SAMPLE ").identity_verified)
        match = synthetic_match(alias="น้ำ", full_name="synthetic water")
        self.assertTrue(qualify_match("นํ้า", match).identity_verified)

    def test_assumed_proxy_unresolved_unknown_preparation_do_not_verify_identity(self):
        for relation in ("assumed", "proxy", "unresolved", None, []):
            with self.subTest(relation=relation):
                self.evidence["identity"][0]["relation"] = relation
                self.assertFalse(self.qualification().identity_verified)
        self.evidence["identity"][0]["relation"] = "exact"
        self.evidence["identity"][0]["preparation"] = "unknown"
        self.assertFalse(self.qualification().identity_verified)

    def test_duplicate_alias_or_unnormalized_identity_entries_do_not_verify(self):
        self.evidence["identity"].append(deepcopy(self.evidence["identity"][0]))
        self.assertFalse(self.qualification().identity_verified)
        self.evidence["identity"] = [self.evidence["identity"][0]]
        self.evidence["identity"][0]["alias"] = "Sample"
        self.assertFalse(self.qualification().identity_verified)

    def test_invalid_schema_and_top_level_review_stay_unknown(self):
        original = deepcopy(self.evidence)
        for schema in (True, "1", 2, None):
            with self.subTest(schema=schema):
                self.evidence["schema_version"] = schema
                self.assert_unknown()
        self.evidence.update(original)
        for key, value in (("reviewer", ""), ("status", "pending"), ("receipt_sha256", "url"),
                           ("reviewed_at_utc", "badZ"), ("reviewed_at_utc", "2000-01-01T00:00:00+07:00")):
            with self.subTest(key=key, value=value):
                self.evidence["review"] = {**original["review"], key: value}
                self.assert_unknown()

    def test_malformed_sections_fail_closed_without_throwing(self):
        for section in ("identity", "macros", "portions"):
            for value in (None, True, "url", [None], [{}]):
                with self.subTest(section=section, value=value):
                    match = synthetic_match()
                    match.derivation["nutrition_evidence"][section] = value
                    result = qualify_match("sample", match)
                    if section == "identity":
                        self.assertFalse(result.identity_verified)
                    elif section == "macros":
                        self.assertFalse(result.macros_verified)
                    else:
                        self.assertEqual(dict(result.verified_portion_grams), {})

    def test_citation_fields_source_ref_and_entry_review_required(self):
        for key, value in (("artifact_sha256", ""), ("source_ref", "SYN2"), ("source", "USDA"),
                           ("release", "unknown"), ("extraction", ""), ("locator", ""), ("url", "file:///secret")):
            with self.subTest(key=key):
                match = synthetic_match()
                match.derivation["nutrition_evidence"]["macros"][0]["citation"][key] = value
                self.assertFalse(qualify_match("sample", match).macros_verified)
        self.evidence["identity"][0]["review"]["reviewer"] = "different-reviewer"
        self.assertFalse(self.qualification().identity_verified)

    def test_missing_duplicate_macro_and_bad_definition_fail_composition(self):
        original = deepcopy(self.evidence["macros"])
        for entries in (original[:-1], original + [original[0]],
                        [{**e, "definition": []} for e in original],
                        [{**e, "definition": "available_carbohydrate"} for e in original]):
            with self.subTest(entries=entries):
                self.evidence["macros"] = entries
                self.assertFalse(self.qualification().macros_verified)
                self.assertTrue(self.qualification().identity_verified)

    def test_publisher_calculation_is_not_project_imputation(self):
        self.evidence["macros"][0]["publisher_method"] = "source-published Atwater"
        self.assertTrue(self.qualification().macros_verified)
        self.evidence["macros"][0]["origin"] = "project_imputed"
        self.evidence["macros"][0]["method"] = "atwater"
        self.assertFalse(self.qualification().macros_verified)

    def test_legacy_estimate_markers_cannot_be_overridden_by_positive_claims(self):
        for markers in ({"proxy": "synthetic substitute"}, {"energy_kcal": "atwater"},
                        {"carbs_g": "by_difference"}, {"carbs_g": "by_difference_clamped"}):
            with self.subTest(markers=markers):
                match = synthetic_match(markers=markers)
                result = qualify_match("sample", match)
                self.assertFalse(result.macros_verified)
                if "proxy" in markers:
                    self.assertFalse(result.identity_verified)
        self.match.derivation["energy_kcal"] = "atwater"
        self.assert_unknown()

    def test_numeric_zero_and_missing_are_distinct(self):
        self.match.macros.calories = 0
        self.evidence["row_binding"]["macros"]["calories"] = 0
        self.evidence["macros"][0]["value"] = 0
        self.assertTrue(self.qualification().macros_verified)
        self.match.macros.calories = None
        self.evidence["row_binding"]["macros"]["calories"] = None
        self.evidence["macros"][0]["value"] = None
        self.assertFalse(self.qualification().macros_verified)
        self.assertTrue(self.qualification().identity_verified)

    def test_volume_basis_metadata_is_independent_of_calculator_support(self):
        match = synthetic_match(basis="100ml")
        self.assertTrue(qualify_match("sample", match).macros_verified)

    def test_uncited_duplicate_or_changed_portion_entries_not_qualified(self):
        original = deepcopy(self.evidence["portions"])
        for entries in ([], original + [original[0]], [{**original[0], "citation": None}],
                        [{**original[0], "grams_per_unit": 55}]):
            with self.subTest(entries=entries):
                self.evidence["portions"] = entries
                self.assertEqual(dict(self.qualification().verified_portion_grams), {})

    def test_portion_amount_never_defaults_to_one(self):
        original = deepcopy(self.evidence["portions"][0])
        for field in ("amount", "gram_weight", "grams_per_unit"):
            for value in (None, 0, -1, True, float("inf"), "2"):
                with self.subTest(field=field, value=value):
                    self.evidence["portions"] = [{**original, field: value}]
                    self.assertEqual(dict(self.qualification().verified_portion_grams), {})
        self.evidence["portions"] = [{**original, "amount": 1e-308, "gram_weight": 1e308}]
        self.assertEqual(dict(self.qualification().verified_portion_grams), {})

    def test_cross_source_equivalence_target_preparation_and_unit_mapping_required(self):
        original = deepcopy(self.evidence["portions"][0])
        for field, value in (("target", {**original["target"], "source": "USDA"}),
                             ("target", {**original["target"], "preparation": "cooked"}),
                             ("equivalence", {"relation": "assumed", "rationale": "guess"}),
                             ("source_preparation", "unknown"), ("portion_id", ""),
                             ("unit_mapping", {**original["unit_mapping"], "runtime_unit": "ถ้วย"})):
            with self.subTest(field=field):
                self.evidence["portions"] = [{**original, field: value}]
                self.assertEqual(dict(self.qualification().verified_portion_grams), {})

    def test_only_cited_current_unit_qualifies(self):
        self.match = synthetic_match(portions={"ฟอง": 50, "ช้อนโต๊ะ": 12})
        self.match.derivation["nutrition_evidence"]["portions"] = self.match.derivation["nutrition_evidence"]["portions"][:1]
        self.assertEqual(dict(self.qualification().verified_portion_grams), {"ฟอง": 50})

    def test_result_immutable_and_input_not_mutated_after_json_roundtrip(self):
        self.match.derivation = json.loads(json.dumps(self.match.derivation))
        before = deepcopy(self.match)
        result = self.qualification()
        self.assertEqual(self.match, before)
        with self.assertRaises(FrozenInstanceError):
            result.macros_verified = False
        with self.assertRaises(TypeError):
            result.verified_portion_grams["ฟอง"] = 1

    def test_qualification_has_no_source_or_file_io(self):
        with patch("builtins.open", side_effect=AssertionError("no source read")), \
             patch("socket.getaddrinfo", side_effect=AssertionError("no DNS")):
            self.assertTrue(self.qualification().macros_verified)


if __name__ == "__main__":
    unittest.main()

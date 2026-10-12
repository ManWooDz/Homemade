import json
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from eval.allergen_kg_eval import (
    HISTORICAL_KEYS, V2_KEYS, _is_literal, empty_resolver, load_labels, main, score_pairs,
)


class VersionedEvaluationTests(unittest.TestCase):
    def test_historical_labels_keep_nine_keys_hash_and_old_strata(self):
        labels, version, keys, digest = load_labels()
        self.assertEqual(version, 1)
        self.assertEqual(set(keys), set(HISTORICAL_KEYS))
        self.assertNotIn("sesame", keys)
        self.assertEqual(len(labels["items"]), 275)
        self.assertEqual(digest, Path("eval/fixtures/allergen_kg_labels.sha256").read_text().strip())
        self.assertTrue(_is_literal("eggplant", "egg"))  # frozen historical definition only
        scores = score_pairs(labels["items"], empty_resolver(), False)
        self.assertEqual(scores["literal"]["positives"], 63)
        self.assertEqual(scores["derived_only"]["positives"], 65)
        self.assertEqual(set(scores["by_key"]), set(HISTORICAL_KEYS))

    def test_frozen_v2_loads_without_development_opt_in(self):
        path = "eval/fixtures/allergen_kg_labels_v2.json"
        labels, version, keys, digest = load_labels(path)
        self.assertEqual(version, 2)
        self.assertEqual(set(keys), set(V2_KEYS))
        self.assertEqual(labels["review_status"], "frozen")
        self.assertEqual(labels["split"], "development")
        self.assertEqual(digest, Path(path).with_suffix(".sha256").read_text().strip())
        scores = score_pairs(labels["items"], empty_resolver(), False, keys=keys, label_version=version)
        self.assertIn("sesame", scores["by_key"])
        self.assertEqual(scores["by_key"]["sesame"]["derived_only"]["positives"], 2)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            score_pairs(labels["items"], empty_resolver(), False, keys=V2_KEYS, label_version=1)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            score_pairs(labels["items"], empty_resolver(), False, keys=HISTORICAL_KEYS, label_version=2)

    def test_v2_strata_come_from_annotations_not_the_runtime_floor(self):
        item = {"id": "oil", "string": "น้ำมันงา", "allergens": ["sesame"],
                "literal_allergens": [], "derived_allergens": ["sesame"], "public": False,
                "scoring_status": "eligible"}
        scores = score_pairs([item], empty_resolver(), False, keys=V2_KEYS, label_version=2)
        self.assertEqual(scores["literal"]["positives"], 0)
        self.assertEqual(scores["derived_only"]["caught"], 1)
        item["literal_allergens"] = ["sesame"]
        with self.assertRaisesRegex(ValueError, "annotated"):
            score_pairs([item], empty_resolver(), False, keys=V2_KEYS, label_version=2)

    def test_incomplete_rows_never_reach_matcher_or_any_score_denominator(self):
        labels, version, keys, _ = load_labels("eval/fixtures/allergen_kg_labels_v2.json", allow_draft=True)
        expected_ids = [f"v2-dev-{number:02}" for number in (5, 10, 11, 18)]
        excluded_strings = {i["string"] for i in labels["items"] if i["id"] in expected_ids}
        with patch("eval.allergen_kg_eval.find_allergy_violation", return_value=None) as matcher:
            scores = score_pairs(labels["items"], empty_resolver(), False, keys=keys, label_version=version)
        self.assertEqual([i["id"] for i in scores["excluded_items"]], expected_ids)
        self.assertTrue(all(i["reason"].strip() for i in scores["excluded_items"]))
        self.assertEqual(scores["n_scored_strings"], 16)
        self.assertEqual(scores["n_scored_pairs"], 160)
        self.assertEqual(scores["n_excluded_strings"], 4)
        self.assertEqual(scores["literal"]["positives"], 10)
        self.assertEqual(scores["derived_only"]["positives"], 3)
        self.assertEqual(scores["negatives"]["total"], 147)
        self.assertEqual(matcher.call_count, 160)
        self.assertTrue(all(call.args[0]["adjusted_ingredients"][0] not in excluded_strings
                            for call in matcher.call_args_list))
        self.assertEqual(sum(v["negatives"]["total"] for v in scores["by_key"].values()), 147)
        scores = score_pairs(labels["items"], empty_resolver(), True, keys=keys, label_version=version)
        self.assertEqual(scores["n_scored_pairs"], 0)
        self.assertEqual(scores["n_excluded_strings"], 0)
        self.assertEqual(scores["excluded_items"], [])  # already removed by public filter

    def test_v2_scoring_status_is_explicit_and_fail_closed_even_for_excluded_rows(self):
        item = {"id": "unknown", "string": "ซอสงา", "allergens": ["sesame"],
                "literal_allergens": [], "derived_allergens": ["sesame"], "public": False}
        for metadata in ({}, {"scoring_status": "typo"},
                         {"scoring_status": "excluded"},
                         {"scoring_status": "excluded", "exclusion_reason": " "},
                         {"scoring_status": "excluded", "exclusion_reason": 123},
                         {"scoring_status": "eligible", "exclusion_reason": "unknown composition"}):
            with self.subTest(metadata=metadata), self.assertRaisesRegex(ValueError, "scoring"):
                score_pairs([dict(item, **metadata)], empty_resolver(), False, keys=V2_KEYS, label_version=2)
        item.update(scoring_status="excluded", exclusion_reason="composition incomplete", literal_allergens=["sesame"])
        with self.assertRaisesRegex(ValueError, "annotated"):
            score_pairs([item], empty_resolver(), False, keys=V2_KEYS, label_version=2)

    def test_recipe_specific_sauce_labels_are_retained_but_not_generic_ground_truth(self):
        labels, _, _, _ = load_labels("eval/fixtures/allergen_kg_labels_v2.json", allow_draft=True)
        sauce = next(i for i in labels["items"] if i["id"] == "v2-dev-18")
        self.assertIn("Kikkoman", sauce["string"])
        self.assertEqual(set(sauce["allergens"]), {"sesame", "soy", "gluten", "egg"})
        self.assertEqual(sauce["literal_allergens"], [])
        self.assertEqual(set(sauce["derived_allergens"]), set(sauce["allergens"]))
        self.assertEqual(sauce["scoring_status"], "excluded")
        self.assertNotIn("peanut", sauce["allergens"])
        self.assertNotIn("fish", sauce["allergens"])
        self.assertEqual(labels["sources"]["sesame_sauce"],
                         "https://kikkomanusa.com/foodservice/recipes/vegetarian-poke-bowl/")

    def test_identified_rice_corn_and_wheat_noodle_controls_remain_distinct(self):
        items = [
            {"id": "rice-corn", "string": "เส้นขนมจีนผสมแป้งข้าวเจ้าและแป้งข้าวโพด 125 กรัม",
             "allergens": [], "literal_allergens": [], "derived_allergens": [],
             "public": False, "scoring_status": "eligible"},
            {"id": "rice-wheat", "string": "เส้นขนมจีนผสมแป้งข้าวเจ้าและแป้งสาลี 125 กรัม",
             "allergens": ["gluten"], "literal_allergens": ["gluten"], "derived_allergens": [],
             "public": False, "scoring_status": "eligible"},
        ]
        # Explicit composition in these test inputs; not assumptions about packaged noodles.
        from eval.allergen_kg_eval import seeded_resolver
        for resolver in (empty_resolver(), seeded_resolver()):
            scores = score_pairs(items, resolver, False, keys=V2_KEYS, label_version=2)
            self.assertEqual(scores["by_key"]["gluten"]["literal"], {"positives": 1, "caught": 1})
            self.assertEqual(scores["flagged_negatives"], [])
            self.assertEqual(scores["n_scored_pairs"], 20)

    def test_cli_reports_versions_hashes_and_no_held_out_claim_for_development(self):
        for arguments, version, kind, keys in [
            ([], 1, "current_code_regression_on_historical_labels", HISTORICAL_KEYS),
            (["--labels", "eval/fixtures/allergen_kg_labels_v2.json"],
             2, "development_regression_not_held_out", V2_KEYS),
        ]:
            with redirect_stdout(io.StringIO()) as output:
                report = main(arguments)
            self.assertEqual(json.loads(output.getvalue()), report)
            self.assertEqual(report["label_version"], version)
            self.assertEqual(report["evaluation_kind"], kind)
            self.assertEqual(set(report["all"]["floor_only"]["by_key"]), set(keys))
            self.assertEqual(len(report["source_sha256"]["database/seed_allergen_graph.py"]), 64)
            if version == 2:
                self.assertEqual(report["all"]["n_strings"], 20)
                for arm in ("floor_only", "floor_union_kg"):
                    self.assertEqual(report["all"][arm]["n_scored_strings"], 16)
                    self.assertEqual(report["all"][arm]["n_scored_pairs"], 160)
                    self.assertEqual(report["all"][arm]["n_excluded_strings"], 4)
                    self.assertEqual(len(report["all"][arm]["excluded_items"]), 4)
                    self.assertEqual(report["without_public"][arm]["n_scored_strings"], 0)
            else:
                self.assertNotIn("excluded_items", report["all"]["floor_only"])

    def test_unfrozen_copy_still_requires_explicit_development_opt_in(self):
        labels, _, _, _ = load_labels("eval/fixtures/allergen_kg_labels_v2.json")
        labels["review_status"] = "reviewed_with_exclusions"
        with TemporaryDirectory() as directory:
            path = Path(directory) / "draft.json"
            path.write_text(json.dumps(labels), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "review"):
                load_labels(path)
            self.assertEqual(load_labels(path, allow_draft=True)[1], 2)

    def test_v2_hash_guard_rejects_label_edits_and_status_downgrade_even_with_opt_in(self):
        labels, _, _, digest = load_labels("eval/fixtures/allergen_kg_labels_v2.json")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "frozen.json"
            path.with_suffix(".sha256").write_text(digest, encoding="utf-8")
            for edit in ("label", "review_status"):
                changed = json.loads(json.dumps(labels))
                if edit == "label":
                    changed["items"][0]["allergens"] = []
                else:
                    changed["review_status"] = "reviewed_with_exclusions"
                path.write_text(json.dumps(changed), encoding="utf-8")
                for allow_draft in (False, True):
                    with self.subTest(edit=edit, allow_draft=allow_draft), self.assertRaisesRegex(ValueError, "hash"):
                        load_labels(path, allow_draft=allow_draft)
            path.write_text(json.dumps(labels), encoding="utf-8")
            self.assertEqual(load_labels(path)[3], digest)

    def test_retained_v2_report_matches_frozen_labels_and_includes_code_hashes(self):
        labels, _, _, digest = load_labels("eval/fixtures/allergen_kg_labels_v2.json")
        report_path = Path("eval/reports/allergen_kg_v2_development_2026-10-07.json")
        if not report_path.exists():
            self.skipTest("Private historical receipt is not shipped with the source-only release")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["label_sha256"], digest)
        self.assertEqual(report["label_version"], 2)
        self.assertEqual(report["review_stats"]["review_status"], "frozen")
        self.assertEqual(report["evaluation_kind"], "development_regression_not_held_out")
        self.assertEqual(report["all"]["n_strings"], len(labels["items"]))
        for arm in ("floor_only", "floor_union_kg"):
            scores = report["all"][arm]
            self.assertEqual(scores["n_scored_pairs"], 160)
            self.assertEqual(scores["n_excluded_strings"], 4)
            self.assertEqual([i["id"] for i in scores["excluded_items"]],
                             [f"v2-dev-{number:02}" for number in (5, 10, 11, 18)])
        # Historical report fingerprints need not equal future legitimately changed code.
        self.assertIn("eval/allergen_kg_eval.py", report["source_sha256"])
        self.assertIn("database/seed_allergen_graph.py", report["source_sha256"])
        for expected_hash in report["source_sha256"].values():
            self.assertEqual(len(expected_hash), 64)
            self.assertEqual(len(bytes.fromhex(expected_hash)), 32)

    def test_hash_and_key_tampering_are_rejected(self):
        labels, _, _, _ = load_labels()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "labels.json"
            path.with_suffix(".sha256").write_text("wrong")
            path.write_text(json.dumps(labels), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash"):
                load_labels(path)
            labels["key_definitions"]["sesame"] = "must not be added to v1"
            path.write_text(json.dumps(labels), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                load_labels(path)


if __name__ == "__main__":
    unittest.main()

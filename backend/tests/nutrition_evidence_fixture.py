"""In-memory test evidence, never publisher bytes or human acceptance."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from nutrition import activate_reviewed as activation
from nutrition import correct_reviewed_g4 as correction


@contextmanager
def synthetic_evidence():
    def encode(value):
        return json.dumps(value, ensure_ascii=False, allow_nan=False).encode()

    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    c2_paths = ["synthetic/c2/approval.txt", "synthetic/c2/acceptance.txt",
                "synthetic/c2/review.txt", "synthetic/c2/plan.txt",
                "synthetic/c2/N2.pdf", "synthetic/c2/N26.pdf", "synthetic/c2/A11.pdf"]
    blobs = {p: ("SYNTHETIC TEST ONLY; NOT A SOURCE DOCUMENT: " + p).encode() for p in c2_paths}
    review = {"status": "accepted", "reviewer": "synthetic-reviewer",
              "reviewed_at_utc": "2000-01-01T00:00:00Z", "receipt_ref": c2_paths[0],
              "receipt_sha256": sha(blobs[c2_paths[0]])}
    records = []
    for ref, name, preparation, aliases, macros, legacy in (
        ("N2", "กระเทียม, สด", "fresh garlic", ["กระเทียม, สด", "Garlic, fresh", "กระเทียมสด"],
         (51, 2.10, 10.40, 0.10), 50.9),
        ("N26", "พริกไทย, ดำ", "black pepper powder", ["Pepper, black, powder", "พริกไทยดำบด"],
         (364, 12.40, 62.20, 7.30), 364.1),
        ("A11", "ข้าวเจ้า, สุก", "cooked polished rice", ["ข้าวเจ้า, สุก", "Rice, polished, cooked", "ข้าวสวย"],
         (136, 2.28, 31.10, 0.24), 135.68)):
        records.append({"source": "INMU", "source_ref": ref, "ingredient_name": name,
                        "unit_basis": "100g", "preparation": preparation, "aliases": aliases,
                        "macros": dict(zip(("calories", "protein_g", "carbs_g", "fat_g"), macros)),
                        "legacy_energy": legacy, "artifact": f"synthetic/c2/{ref}.pdf",
                        "url": f"https://example.invalid/synthetic/{ref}"})
    manifest = {"schema_version": 1, "review": review,
                "artifacts": {p: sha(blobs[p]) for p in c2_paths}, "records": records}
    manifest_path = "synthetic/c2/manifest.json"
    blobs[manifest_path] = encode(manifest)

    packet = "synthetic/g4/"
    source, receipt = packet + "source.pdf", packet + "approval.txt"
    before = {"rows": [{"id": 525, "source": "INMU", "source_ref": "G4",
                        "ingredient_name": "กุ้งก้ามกราม, สด", "unit_basis": "100g",
                        "calories": 88.0, "protein_g": 17.9, "carbs_g": 0.0, "fat_g": 3.7,
                        "portion_grams": None, "derivation": {"carbs_g": "by_difference_clamped"}}],
              "aliases": [{"alias": alias, "owner": 525}
                          for alias in ("prawn, giant freshwater, raw", "กุ้ง", "กุ้งก้ามกราม, สด")]}
    g4_paths = (receipt, packet + "review.md", packet + "current-state.json",
                source, "synthetic/g4/helper.py")
    blobs.update({p: ("SYNTHETIC TEST ONLY; NOT A SOURCE DOCUMENT: " + p).encode() for p in g4_paths})
    blobs[packet + "current-state.json"] = encode({"state": before})
    artifacts = {p: sha(blobs[p]) for p in g4_paths}
    g4_review = {**review, "receipt_ref": receipt, "receipt_sha256": artifacts[receipt]}
    virtual_files = {(activation.ROOT / p).resolve(): raw for p, raw in blobs.items()}

    def read_synthetic(path):
        if path.resolve() not in virtual_files:
            raise AssertionError("Portable test attempted a read outside synthetic evidence")
        return virtual_files[path.resolve()]

    with patch.multiple(activation, MANIFEST=manifest_path, MANIFEST_SHA256=sha(blobs[manifest_path])), \
            patch.multiple(correction, PACKET=packet, SOURCE=source, RECEIPT=receipt,
                           ARTIFACTS=artifacts, BEFORE_SHA256=activation._digest(before), REVIEW=g4_review), \
            patch.object(Path, "read_bytes", new=read_synthetic):
        yield

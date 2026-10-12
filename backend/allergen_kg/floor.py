# backend/allergen_kg/floor.py
"""Hardcoded allergen floor + trigger detection shared by main.py and the KG layer.

FLOOR_BLOCKS is the safety floor: the effective block set is always
FLOOR_BLOCKS[key] ∪ KG closure, so a missing/partial seed can never remove
protection these lists already gave (design: docs/superpowers/specs/2026-09-28-allergen-kg-design.md).
"""

import re

from nutrition.text import normalize_thai


ALLERGEN_MAP = {
    "shrimp":    {"triggers": ["shrimp", "prawn", "กุ้ง", "กะปิ", "อาหารทะเล"],
                  # "กะปิ" (shrimp paste) was an interim single-entry patch
                  # (2026-09-19). It stays as part of the floor; derived
                  # ingredients in general are now covered by the allergen
                  # Knowledge Graph (allergen_kg/graph.py) when it is seeded.
                  "blocks":   ["shrimp", "prawn", "กุ้ง", "กะปิ"]},
    "peanut":    {"triggers": ["peanut", "peanuts", "ถั่วลิสง", "ถั่ว"],
                  "blocks":   ["peanut", "peanuts", "ถั่วลิสง", "เนยถั่ว"]},
    "milk":      {"triggers": ["milk", "dairy", "cream", "butter", "cheese", "ชีส", "นม", "เนย", "ครีม",
                               "แลคโตส", "แล็กโทส", "lactose", "โยเกิร์ต", "yogurt", "whey"],
                  "blocks":   ["milk", "dairy", "cream", "butter", "cheese", "ชีส", "นม", "เนย", "ครีม"]},
    "egg":       {"triggers": ["egg", "eggs", "ไข่"],
                  "blocks":   ["egg", "eggs", "ไข่"]},
    "gluten":    {"triggers": ["wheat", "flour", "gluten", "แป้งสาลี", "แป้ง",
                                "กลูเตน", "ข้าวสาลี", "บาร์เลย์", "ไรย์", "barley", "rye"],
                  "blocks":   ["wheat", "flour", "gluten", "แป้งสาลี", "แป้ง"]},
    "shellfish": {"triggers": ["crab", "lobster", "clam", "oyster", "ปู", "หอย", "กั้ง",
                                "หมึก", "squid", "octopus", "mussel", "ล็อบสเตอร์", "shellfish", "อาหารทะเล"],
                  "blocks":   ["crab", "lobster", "clam", "oyster", "ปู", "หอย", "กั้ง"]},
    "fish":      {"triggers": ["fish", "ปลา", "อาหารทะเล", "salmon", "tuna", "แซลมอน", "ทูน่า"],
                  "blocks":   ["fish", "ปลา", "น้ำปลา", "fish sauce", "ปลาร้า"]},
    # "ถั่ว" (generic Thai word, ambiguous between peanut/soy/other legumes)
    # deliberately excluded here -- kept only under "peanut" below, since
    # colloquial "แพ้ถั่ว" with no further qualifier most commonly means
    # peanut allergy. Previously listed here too, causing a false-positive
    # over-block: a soy-unrelated recipe containing "ซีอิ๊ว" (soy sauce) got
    # blocked for a user who only said "แพ้ถั่ว" (peanut allergy) -- found
    # and verified 2026-09-19 via the expanded eval fixtures.
    "soy":       {"triggers": ["soy", "ถั่วเหลือง", "เต้าหู้", "ซีอิ๊ว", "เต้าเจี้ยว", "tofu", "soya", "edamame"],
                  "blocks":   ["soy sauce", "soy", "tofu", "เต้าหู้", "ถั่วเหลือง", "ซีอิ๊ว", "ซอสถั่วเหลือง"]},
    "nut":       {"triggers": ["almond", "cashew", "walnut", "hazelnut", "อัลมอนด์", "มะม่วงหิมพานต์",
                                "พิสตาชิโอ", "pistachio", "แมคคาเดเมีย", "macadamia", "พีแคน", "pecan",
                                "วอลนัท", "เฮเซลนัท", "เกาลัด", "เม็ดมะม่วง", "ถั่วเปลือกแข็ง", "tree nut"],
                  "blocks":   ["almond", "cashew", "walnut", "hazelnut", "อัลมอนด์", "มะม่วงหิมพานต์"]},
    "sesame":    {"triggers": ["sesame", "งา", "ทาฮินี", "tahini"],
                  "blocks": ["sesame", "งา", "น้ำมันงา", "sesame oil", "ซอสงา", "sesame sauce", "ทาฮินี", "tahini"]},
}
ALLERGY_TRIGGER_KEYWORDS = ["allergic to", "allergy", "แพ้", "ห้ามใส่", "ไม่ทาน",
                             "ไม่กิน", "ห้ามกิน", "กินไม่ได้", "allergic", "intolerant"]

NO_ALLERGY_VALUES = ("", "none", "ไม่มี", "ไม่แพ้อาหาร", "no allergy", "ไม่มีข้อจำกัด", "ไม่มีอาการแพ้")

FLOOR_BLOCKS = {key: mapping["blocks"] for key, mapping in ALLERGEN_MAP.items()}

# Display labels for allergen nodes in reason strings. The schema has no label column.
ALLERGEN_LABELS = {
    "shrimp": "กุ้ง",
    "peanut": "ถั่วลิสง",
    "milk": "นม",
    "egg": "ไข่",
    "gluten": "กลูเตน",
    "shellfish": "สัตว์มีเปลือก",
    "fish": "ปลา",
    "soy": "ถั่วเหลือง",
    "nut": "ถั่วเปลือกแข็ง",
    "sesame": "งา",
}


# ponytail: reviewed compounds only; expand with composition evidence and paired
# regressions if new collisions appear, rather than guessing a Thai tokenizer.
UNRELATED_COMPOUNDS = {
    "fish": ("ปลาหมึก",),
    "milk": ("ขนม", "แหนม"),
    "egg": ("ไข่มดแดง", "ไข่ปลา"),
    "gluten": ("แป้งข้าวเจ้า", "แป้งข้าวเหนียว", "แป้งข้าวโพด", "แป้งมันสำปะหลัง", "แป้งมัน"),
    "peanut": ("ถั่วเหลือง", "ถั่วเปลือกแข็ง"),
    "sesame": ("รายงาน", "งาน", "งาม", "งาช้าง", "เงาะ"),
}

# Composition is independent of storage provenance: floor terms can be derived.
DERIVED_FLOOR_TERMS = {
    "shrimp": ("กะปิ",),
    "peanut": ("เนยถั่ว",),
    "milk": ("dairy", "cream", "butter", "cheese", "ชีส", "เนย", "ครีม"),
    "fish": ("น้ำปลา", "fish sauce", "ปลาร้า"),
    "soy": ("soy sauce", "tofu", "เต้าหู้", "ซีอิ๊ว", "ซอสถั่วเหลือง"),
    "sesame": ("น้ำมันงา", "sesame oil", "ซอสงา", "sesame sauce", "ทาฮินี", "tahini"),
}


def term_spans(text: str, term: str, key: str):
    """Offsets in normalized text, excluding unrelated compounds, not whole lines."""
    text, term = normalize_thai(text).lower(), normalize_thai(term).lower()
    if not term:
        return []
    start = r"(?<![a-z])" if term[0].isascii() and term[0].isalpha() else ""
    end = r"(?![a-z])" if term[-1].isascii() and term[-1].isalpha() else ""
    protected = [m.span() for name in UNRELATED_COMPOUNDS.get(key, ())
                 for m in re.finditer(re.escape(normalize_thai(name).lower()), text)]
    return [m.span() for m in re.finditer(start + re.escape(term) + end, text)
            if not any(a <= m.start() and m.end() <= b for a, b in protected)]


# Literal aliases are ingredient identities, regardless of KG path length.
LITERAL_KG_TERMS = {
    "shrimp": ("กุ้งแห้ง",),
    "shellfish": ("ปลาหมึก", "cuttlefish", "calamari", "scallop", "mussel", "cockle", "abalone", "เป๋าฮื้อ", "crayfish", "crawfish", "ล็อบสเตอร์"),
    "fish": ("ซาร์ดีน", "แอนโชวี่", "หูฉลาม", "sardine", "sardines", "anchovy", "anchovies", "bonito"),
    "gluten": ("ข้าวสาลี", "ข้าวบาร์เลย์", "ข้าวไรย์"),
    "nut": ("มะคาเดเมีย",),
    "sesame": ("เมล็ดงา", "sesame seeds"),
}

_NEGATIVE_PREF = ("not allergic to", "no allergy to", "ไม่แพ้")
_POSITIVE_PREF = tuple(ALLERGY_TRIGGER_KEYWORDS)
_PREF_SEPARATORS = re.compile(r"(?:\s+|[,;:/]|และ|แต่|กับ|\b(?:and|but)\b)+")
_PREF_LABELS = {}
for _key, _mapping in ALLERGEN_MAP.items():
    for _label in _mapping["triggers"]:
        _PREF_LABELS.setdefault(normalize_thai(_label).lower(), set()).add(_key)
_PREF_LABELS["ผลิตภัณฑ์จากนม"] = {"milk"}


def parse_allergy_preferences(user_prefs) -> tuple[list[str], bool]:
    """Return active keys and whether clarification is required before generation.

    Plural allergies accepts explicit declarations or bare UI labels. Singular
    allergy/plain prose keeps its keyword gate. Negative declarations have local
    scope; positive/negative contradictions are rejected, never silently erased.
    """
    parts = ((user_prefs.get("allergy", ""), True), (user_prefs.get("allergies", ""), False)) \
        if isinstance(user_prefs, dict) else ((user_prefs, True),)
    positive, negative, ambiguous = set(), set(), False
    labels = sorted(_PREF_LABELS, key=len, reverse=True)
    prefixes = sorted((*_NEGATIVE_PREF, *_POSITIVE_PREF), key=len, reverse=True)
    for value, gated in parts:
        if not value:
            continue
        if not isinstance(value, str):
            ambiguous = True
            continue
        if len(value) > 1000:
            ambiguous = True
            continue
        text = normalize_thai(value).strip().lower()
        if text in {normalize_thai(v).lower() for v in NO_ALLERGY_VALUES}:
            continue
        if gated and not any(kw in text for kw in ALLERGY_TRIGGER_KEYWORDS):
            continue
        cursor, negate, targets, needs_target = 0, False, 0, False
        while cursor < len(text):
            separator = _PREF_SEPARATORS.match(text, cursor)
            if separator:
                cursor = separator.end()
                continue
            prefix = next((p for p in prefixes if text.startswith(p, cursor)
                           and (not p[-1].isascii() or not text[cursor + len(p):cursor + len(p) + 1].isalpha())), None)
            if prefix:
                if needs_target:
                    ambiguous = True
                    break
                needs_target = True
                negate = prefix in _NEGATIVE_PREF
                cursor += len(prefix)
                continue
            label = next((t for t in labels if (cursor, cursor + len(t)) in term_spans(text, t, next(iter(_PREF_LABELS[t])))), None)
            if label is None:
                ambiguous = True
                break
            (negative if negate else positive).update(_PREF_LABELS[label])
            targets += 1
            needs_target = False
            cursor += len(label)
        if not targets or needs_target:
            ambiguous = True
    return [key for key in ALLERGEN_MAP if key in positive], ambiguous or bool(positive & negative)


def detect_flagged_allergens(user_prefs) -> list[str]:
    return parse_allergy_preferences(user_prefs)[0]

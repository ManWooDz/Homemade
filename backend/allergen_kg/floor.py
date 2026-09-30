# backend/allergen_kg/floor.py
"""Hardcoded allergen floor + trigger detection shared by main.py and the KG layer.

FLOOR_BLOCKS is the safety floor: the effective block set is always
FLOOR_BLOCKS[key] ∪ KG closure, so a missing/partial seed can never remove
protection these lists already gave (design: docs/superpowers/specs/2026-09-28-allergen-kg-design.md).
"""

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
                  "blocks":   ["fish", "ปลา"]},
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
}
ALLERGY_TRIGGER_KEYWORDS = ["allergic to", "allergy", "แพ้", "ห้ามใส่", "ไม่ทาน",
                             "ไม่กิน", "ห้ามกิน", "กินไม่ได้", "allergic", "intolerant"]

NO_ALLERGY_VALUES = ("", "none", "ไม่มี", "ไม่แพ้อาหาร", "no allergy")

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
}


def detect_flagged_allergens(user_prefs) -> list[str]:
    """Which ALLERGEN_MAP keys the user's stated allergy refers to.

    Extracted unchanged from the old check_allergy() so resolution and
    matching can never disagree about which allergens are in play.
    """
    if isinstance(user_prefs, dict):
        allergy_str = str(user_prefs.get("allergy", "") or "").lower().strip()
    else:
        allergy_str = str(user_prefs).lower()

    if not allergy_str or allergy_str in NO_ALLERGY_VALUES:
        return []
    if not any(kw in allergy_str for kw in ALLERGY_TRIGGER_KEYWORDS):
        return []
    return [
        key for key, mapping in ALLERGEN_MAP.items()
        if any(trigger in allergy_str for trigger in mapping["triggers"])
    ]

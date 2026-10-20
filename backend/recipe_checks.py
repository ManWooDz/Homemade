"""Bounded, pure recipe checks; identity is separate from pantry permission."""
import math
import re

from nutrition.text import normalize_alias
from recipe_contracts import ingredient_names, validate_generated_recipe_shape

BASIC_INGREDIENTS = ["salt", "pepper", "oil", "soy sauce", "fish sauce", "sugar", "water"]
# Deprecated compatibility export; Flavor uses the reviewed contextual rules below.
BAD_FLAVOR_PAIRS = [("milk", "fish sauce"), ("chocolate", "garlic")]

# Reviewed catalog meanings; these are not nutrition aliases or substitutions.
CATALOG_ALIASES = {
    "avocado": ("อะโวคาโด", "อโวคาโด"),
    "balsamic vinaigrette": ("น้ำสลัดบัลซามิก", "น้ำสลัดบัลซามิกวินิเกรต"),
    "bean sprouts": ("ถั่วงอก",),
    "beef steak": ("เนื้อวัวสำหรับสเต๊ก", "เนื้อสเต๊กวัว"),
    "bell pepper": ("พริกหวาน",),
    "bird's eye chilies": ("พริกขี้หนู",),
    "black pepper": ("พริกไทยดำ",),
    "butter": ("เนย", "เนยแท้"),
    "carrot": ("แครอท",),
    "cherry tomatoes": ("มะเขือเทศเชอร์รี", "มะเขือเทศเชอร์รี่"),
    "chili paste": ("น้ำพริกเผา",),
    "chives": ("กุยช่าย",),
    "cilantro": ("ผักชี",),
    "cucumber": ("แตงกวา",),
    "edamame": ("ถั่วแระญี่ปุ่น",),
    "egg": ("ไข่",),
    "feta cheese": ("ชีสเฟตา", "เฟตาชีส"),
    "fish sauce": ("น้ำปลา",),
    "galangal": ("ข่า",),
    "garlic": ("กระเทียม",),
    "green onion": ("ต้นหอม",),
    "holy basil leaves": ("ใบกะเพรา", "กะเพรา"),
    "kaffir lime leaves": ("ใบมะกรูด",),
    "kalamata olives": ("มะกอกคาลามาตา",),
    "kale": ("เคล", "ผักเคล"),
    "lemongrass": ("ตะไคร้",),
    "lime juice": ("น้ำมะนาว",),
    "minced pork": ("หมูสับ", "เนื้อหมูบด"),
    "mushrooms": ("เห็ด",),
    "nori seaweed": ("สาหร่ายโนริ", "โนริ"),
    "olive oil": ("น้ำมันมะกอก",),
    "oregano": ("ออริกาโน",),
    "oyster sauce": ("ซอสหอยนางรม", "น้ำมันหอย"),
    "palm sugar": ("น้ำตาลปาล์ม",),
    "peanuts": ("ถั่วลิสง",),
    "pork belly (chashu)": ("หมูสามชั้นชาชู", "ชาชูหมูสามชั้น"),
    "pumpkin seeds": ("เมล็ดฟักทอง",),
    "purple cabbage": ("กะหล่ำปลีม่วง",),
    "quinoa": ("คีนัว", "ควินัว"),
    "ramen noodles": ("เส้นราเมน",),
    "red onion": ("หอมหัวใหญ่แดง", "หอมหัวใหญ่สีแดง"),
    "rice noodles": ("เส้นก๋วยเตี๋ยวข้าว",),
    "rosemary": ("โรสแมรี", "โรสแมรี่"),
    "salt": ("เกลือ",),
    "sesame dressing": ("น้ำสลัดงา",),
    "shrimp": ("กุ้ง",),
    "soft-boiled egg": ("ไข่ต้มยางมะตูม",),
    "soy sauce": ("ซีอิ๊ว", "ซอสถั่วเหลือง"),
    "spinach": ("ผักปวยเล้ง", "ปวยเล้ง"),
    "sugar": ("น้ำตาล",),
    "tamarind paste": ("มะขามเปียกบด", "เนื้อมะขามเปียก"),
    "tofu": ("เต้าหู้",),
    "tonkotsu broth": ("น้ำซุปกระดูกหมูทงคตสึ",),
    "vegetable oil": ("น้ำมันพืช",),
    "yellow bell pepper": ("พริกหวานเหลือง", "พริกหวานสีเหลือง"),
}
_EXTRA_ALIASES = {
    "pepper": ("พริกไทย",), "oil": ("น้ำมัน",), "water": ("น้ำเปล่า", "น้ำ"),
    "cow milk": ("นมวัว", "cow's milk", "whole milk"),
    "milk": ("นม",), "chocolate": ("ช็อกโกแลต", "ช็อคโกแลต"),
}
_ALIASES = {
    normalize_alias(alias): key
    for key, aliases in {**CATALOG_ALIASES, **_EXTRA_ALIASES}.items()
    for alias in (key, *aliases)
}
_PANTRY = frozenset((*BASIC_INGREDIENTS, "black pepper", "vegetable oil", "olive oil", "palm sugar"))
_OILS = frozenset(("oil", "vegetable oil", "olive oil"))

# Directional references in steps/titles, never ingredient-admission aliases.
_SHORT_NAMES = {
    "minced pork": ("pork", "หมู", "เนื้อหมู"),
    "pork belly (chashu)": ("pork", "หมู", "ชาชู"),
    "beef steak": ("beef", "เนื้อวัว"),
    "soft-boiled egg": ("egg", "ไข่"),
    "ไข่ไก่": ("egg", "ไข่"),
    "holy basil leaves": ("basil",),
    "yellow bell pepper": ("bell pepper", "พริกหวาน"),
    "black pepper": ("pepper", "พริกไทย"),
    "palm sugar": ("sugar", "น้ำตาล"),
    "olive oil": ("oil", "น้ำมัน"), "vegetable oil": ("oil", "น้ำมัน"),
    "cow milk": ("milk", "นม"),
    "pork": ("หมู", "เนื้อหมู"), "chicken": ("ไก่",), "beef": ("เนื้อวัว",),
}
# Known near misses mask embedded shorter words without admitting these foods.
_DISTINCT_NAMES = ("eggplant", "ไข่ไก่", "ไข่เป็ด", "หมูสามชั้น", "thai basil", "โหระพา",
                   "garlic chives", "นมถั่วเหลือง", "นมอัลมอนด์", "นมข้าวโอ๊ต", "coconut milk",
                   "soy milk", "oat milk", "almond milk", "กะทิ", "น้ำมันงา", "น้ำมันมะพร้าว",
                   "น้ำส้มสายชู", "egg noodles", "rice", "cooked rice", "ข้าว", "ข้าวสวย", "ข้าวสาร")
_AMOUNT = r"[+\-−]?(?:\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?|nan|inf(?:inity)?)"
_AMOUNT_OR_RANGE = rf"{_AMOUNT}(?:\s*-\s*{_AMOUNT})?"
_QUANTITY = re.compile(rf"(?P<amount>{_AMOUNT})(?:\s*-\s*(?P<upper>{_AMOUNT}))?\s*(?:[a-zก-๙.]+)?", re.I)
_VAGUE = r"(?:เล็กน้อย|ตามชอบ|พอประมาณ|ตามต้องการ|to taste|as needed)"
_VAGUE_TAIL = re.compile(rf"(?:\({_VAGUE}\)|{_VAGUE})(?:\s+{_AMOUNT}\s*[a-zก-๙.]+)?", re.I)
_UNLISTED_LINE = re.compile(rf"(.+?)\s+({_AMOUNT_OR_RANGE})\s*([a-zก-๙.]+)$", re.I)
_CLAUSE_BREAK = re.compile(r"[.!?;\n]|แต่|แล้ว|จากนั้น|\b(?:but|then)\b")
_THAI_ACTION = r"ใส่|เติม|ใช้|ผสม|คลุก|ผัด|ทอด|ต้ม|โรย|เสิร์ฟ|ตั้ง|อุ่น|เจียว|คั่ว|ย่าง|อบ|หมัก|ทา"
_EN_ACTION = r"add|use|mix|combine|blend|coat|heat|fr(?:y|ying|ied)|stir[- ]fr(?:y|ying|ied)|cook|boil|serve|season|marinate|saute|sauté"
_OPERATOR = re.compile(
    rf"(?P<negative>(?:ห้าม|อย่า|ไม่ต้อง|ไม่ควร|ไม่)\s*(?:{_THAI_ACTION})?|หลีกเลี่ยง|"
    rf"\b(?:do not|don't|never|avoid)\s+(?:{_EN_ACTION})\b|\bwithout\b)"
    rf"|(?P<positive>{_THAI_ACTION}|\b(?:{_EN_ACTION})\b)"
)
_FRY = re.compile(r"ผัด|ทอด|\b(?:fry|frying|fried|stir[- ]fry|stir[- ]frying)\b")
_STIR_FRY = re.compile(r"ผัด|\b(?:stir[- ]fr(?:y|ying|ied)|saute|sauté)\b")
_NO_ADDED_OIL = re.compile(normalize_alias(
    r"หม้อทอด(?:ไร้|ไม่ใช้)น้ำมัน|หม้อทอดลมร้อน|ทอดลมร้อน|ผัดน้ำ|คั่วแห้ง|ทอดแห้ง|"
    r"เจียวมันหมู|ใช้น้ำมันจากมันหมู|\b(?:air[- ]fr(?:y|ying|ied)|air fryer|dry[- ]fr(?:y|ying)|"
    r"dry toast|water saut[eé]|render(?:ed)? fat)\b"
))
_STOCK_CLAIMS = (
    "วัตถุดิบไม่พอ", "วัตถุดิบไม่เพียงพอ", "ต้องซื้อเพิ่ม", "ต้องซื้อวัตถุดิบเพิ่ม",
    "วัตถุดิบเพียงพอ", "มีวัตถุดิบเพียงพอ", "not enough ingredients", "insufficient ingredients",
    "have enough ingredients", "enough ingredients", "ingredients are sufficient", "need to buy more",
    "needs to buy more", "must buy more", "have to buy more", "buy more ingredients",
)


def _identity(name):
    normalized = normalize_alias(name)
    return _ALIASES.get(normalized, normalized)


def _quantity_ok(tail):
    tail = tail.strip(" ,:")
    if not tail:
        return True
    if _VAGUE_TAIL.fullmatch(tail):
        numeric = re.search(rf"\s+({_AMOUNT})\s*[a-zก-๙.]+$", tail, re.I)
        return _quantity_ok(numeric[0]) if numeric else True
    match = _QUANTITY.fullmatch(tail)
    if match is None:
        return None
    try:
        values = []
        for token in (match["amount"], match["upper"]):
            if token is None:
                continue
            token = token.replace("−", "-")
            if "/" in token:
                numerator, denominator = token.split("/")
                value = float(numerator) / float(denominator)
            else:
                value = float(token)
            if not math.isfinite(value) or value <= 0:
                return False
            values.append(value)
        return values[0] <= values[-1]
    except (ValueError, OverflowError, ZeroDivisionError):
        return False


def _line(raw, selected=()):
    text = normalize_alias(raw)
    names = {**_ALIASES, **{normalize_alias(name): _identity(name) for name in selected}}
    for alias in sorted(names, key=len, reverse=True):
        if text.startswith(alias):
            valid = _quantity_ok(text[len(alias):])
            if valid is not None:
                return names[alias], valid
    match = _UNLISTED_LINE.fullmatch(text)
    if match:
        return _identity(match[1]), _quantity_ok(match[2] + match[3])
    vague = re.search(rf"\s*{_VAGUE}$", text)
    if vague:
        return _identity(text[:vague.start()]), True
    return _identity(text), True


def unknown_ingredients(recipe, user_ingredients):
    allowed = {_identity(name) for name in user_ingredients} | _PANTRY
    lines = recipe.get("adjusted_ingredients", []) if isinstance(recipe, dict) else []
    return [line for line in lines if isinstance(line, str) and _line(line, user_ingredients)[0] not in allowed]


def check_ingredients(recipe, user_ingredients):
    unknown = unknown_ingredients(recipe, user_ingredients)
    if unknown:
        return False, f"Invalid ingredient found: {unknown[0]}"
    for line in recipe["adjusted_ingredients"]:
        if not _line(line, user_ingredients)[1]:
            return False, f"Invalid ingredient quantity: {line}"
    return True, "OK"


def _declared(recipe):
    return {_line(line)[0] for line in recipe["adjusted_ingredients"]}


def _names(declared):
    # shortcut: recognized vocabulary only; expand reviewed names when coverage is measured.
    names = dict(_ALIASES)
    for key in declared:
        names[key] = key
    for aliases in _SHORT_NAMES.values():
        for alias in aliases:
            names[normalize_alias(alias)] = _identity(alias)
    for alias in _DISTINCT_NAMES:
        names[normalize_alias(alias)] = _identity(alias)
    for equipment in ("หม้อทอดไร้น้ำมัน", "หม้อทอดไม่ใช้น้ำมัน"):
        names[normalize_alias(equipment)] = None
    return names


def _mentions(text, names):
    pattern = "|".join(re.escape(name) for name in sorted(names, key=len, reverse=True) if name)
    for match in re.finditer(r"(?<![a-z0-9])(?:" + pattern + r")(?![a-z0-9])", text):
        if names[match[0]] is not None:
            yield names[match[0]], match[0], match.start(), match.end()


def _targets(key, declared):
    if key in declared:
        return {key}
    return {identity for identity in declared
            if key in {_identity(name) for name in _SHORT_NAMES.get(identity, ())}}


def _clauses(recipe, declared):
    names = _names(declared)
    for index, instruction in enumerate(recipe["instructions"], 1):
        for clause in _CLAUSE_BREAK.split(normalize_alias(instruction)):
            if re.search(r"ตัวอย่าง|\bexample\b", clause):
                continue
            operators = list(_OPERATOR.finditer(clause))
            uses = []
            for key, text, start, end in _mentions(clause, names):
                preceding = [operator for operator in operators if operator.start() < start]
                operator = preceding[-1] if preceding else next(
                    (operator for operator in operators if operator.start() >= end), None)
                if operator is not None and operator.lastgroup == "positive":
                    uses.append((key, text, _targets(key, declared)))
            yield index, clause, uses


def check_logic(recipe):
    instructions = " ".join(recipe["instructions"])
    warning = recipe.get("safety_warning", "")
    cooking_text = normalize_alias(instructions + " " + (warning if isinstance(warning, str) else ""))
    if any(normalize_alias(claim) in cooking_text for claim in _STOCK_CLAIMS):
        return False, "Prohibited stock conclusion"
    declared = _declared(recipe)
    oil_used = False
    for index, clause, uses in _clauses(recipe, declared):
        for _, text, targets in uses:
            if not targets:
                return False, f"Undeclared ingredient in step {index}: {text}; add it to adjusted_ingredients"
            if len(targets) != 1:
                return False, f"Ambiguous ingredient in step {index}: {text}; use its declared full name"
        oil_used |= any(targets & _OILS for _, _, targets in uses)
        if _FRY.search(clause) and not _NO_ADDED_OIL.search(clause):
            actions = list(_OPERATOR.finditer(clause))
            if any(action.lastgroup == "positive" and _FRY.search(action[0]) for action in actions):
                if not (declared & _OILS and oil_used):
                    return False, f"Oil-based frying in step {index} needs declared oil used at or before this step; clarify an oil-free method if intended"
    return True, "OK"


def _stir_fry_family(recipe, declared):
    title = normalize_alias(recipe["recipe_name"])
    explicit = re.search(r"ผัดไทย|ผัดกะเพรา|\b(?:pad\s?thai|pad kra\s?pao|pad krapow)\b|"
                         r"\b(?:stir[- ]fried holy basil|holy basil stir[- ]fry)\b", title)
    catalog_basil = "holy basil leaves" in declared and re.search(r"\bstir[- ]fried basil\b", title)
    return bool(explicit or catalog_basil)


def check_flavor(recipe):
    declared = _declared(recipe)
    if not _stir_fry_family(recipe, declared):
        return True, "OK (Flavor rules not applicable)"
    component = set()
    for index, clause, uses in _clauses(recipe, declared):
        separate = any(not re.search(r"(?:ไม่ต้อง|ไม่ควร|ไม่|ห้าม|อย่า|not|never)\s*$", clause[:match.start()])
                       for match in re.finditer(r"แยก|ต่างหาก|\b(?:separately|alongside)\b", clause))
        if separate:
            component = set()
            continue
        used = set().union(*(targets for _, _, targets in uses)) if uses else set()
        same_component = re.search(r"กระทะเดิม|กระทะเดียวกัน|ส่วนเดียวกัน|ผัดรวมกัน|\bsame (?:pan|stir[- ]fry|component)\b", clause)
        if same_component and component:
            component |= used
        elif any(action.lastgroup == "positive" and _STIR_FRY.search(action[0])
                 for action in _OPERATOR.finditer(clause)):
            component = used
        else:
            continue
        for rule, pair in (("F01", {"cow milk", "fish sauce"}), ("F02", {"chocolate", "garlic"})):
            if pair <= component:
                return False, f"Flavor {rule}: HomeMade Padthai/Pad kra pao rule rejects {' + '.join(sorted(pair))} in the same stir-fry (step {index}); revise this component"
    return True, "OK"


def check_nutrition(recipe):
    valid, reason = validate_generated_recipe_shape(recipe)
    if not valid:
        return False, reason
    for line in recipe["adjusted_ingredients"]:
        if not _line(line)[1]:
            return False, f"Invalid ingredient quantity: {line}"
    nutrition = recipe["nutrition"]
    if nutrition["calories"] <= 0:
        return False, "Unrealistic calories"
    # shortcut: loose project bound omits total carbs/fibre; extend only with reviewed energy metadata.
    if nutrition["calories"] + 1 < 0.5 * nutrition["protein_g"] + nutrition["fat_g"]:
        return False, "Nutrition contradiction: calories too low for stated protein/fat; check units and per-serving values"
    return True, "OK"


def check_core(recipe, user_ingredients):
    declared = {_line(line, user_ingredients)[0] for line in recipe["adjusted_ingredients"]}
    title = normalize_alias(recipe["recipe_name"])
    absent, previous_end = False, 0
    for key, text, start, end in _mentions(title, _names(declared)):
        absent = bool(re.search(r"(?:without|free from|no)\s*$|ไม่มี\s*$|ปราศจาก\s*$", title[:start])
                      or (absent and re.fullmatch(r"\s*(?:and|or|และ|หรือ|,|/)\s*", title[previous_end:start]))
                      or re.match(r"[- ]free\b", title[end:]))
        previous_end = end
        if absent:
            continue
        targets = _targets(key, declared)
        if not targets:
            return False, f"Missing named ingredient: {text}; use it in the recipe or rename the dish"
        if len(targets) != 1:
            return False, f"Ambiguous named ingredient: {text}; use its declared full name"
    return True, "OK"


def ingredient_prompt_guidance(ingredients):
    selected = ingredient_names(ingredients)
    keys = dict.fromkeys([*(_identity(name) for name in selected), *sorted(_PANTRY)])
    entries = []
    for key in keys:
        aliases = CATALOG_ALIASES.get(key, _EXTRA_ALIASES.get(key, ()))
        entries.append(" / ".join((key, *aliases)))
    return (
        "ชื่อวัตถุดิบที่ยืนยันได้สำหรับรายการนี้: " + "; ".join(entries) + "\n"
        "ทุกวัตถุดิบที่ใช้ในขั้นตอน รวมเครื่องปรุงพื้นฐาน ต้องอยู่ใน adjusted_ingredients ด้วย ห้ามลืมประกาศ\n"
        "ใช้ชื่อที่ระบุข้างต้น ถ้าไม่มีคู่ชื่อไทยให้คงชื่อต้นฉบับ ห้ามเดาวัตถุดิบต่างชนิดหรือส่วน\n"
        "ปริมาณที่ระบุเป็นตัวเลขต้องมากกว่าศูนย์ เครื่องปรุงเขียนตามชอบได้ ห้ามแต่งกรัมแทน\n"
        "หากระบุปริมาณได้ ให้ใช้ปริมาณเดียวแทนช่วง เช่น 6 เม็ด แทน 5-7 เม็ด เพื่อคำนวณโภชนาการได้ชัดเจน\n"
        "ชื่อเมนูต้องตรงกับวัตถุดิบที่ใช้จริง เปลี่ยนของหลักและชื่อได้\n"
        "กฎ Flavor ของ HomeMade เฉพาะผัดไทย/ผัดกะเพรา: ไม่ผัดนมวัวกับน้ำปลา หรือช็อกโกแลตกับกระเทียมรวมในส่วนเดียวกัน "
        "ไม่ใช่ข้อห้ามคู่ส่วนผสมสำหรับทุกเมนู\n"
        "การผัด/ทอดแบบใช้น้ำมันต้องประกาศน้ำมันและระบุการใช้ก่อนหรือขณะปรุง ถ้าใช้วิธีไร้น้ำมันให้ระบุวิธีให้ชัด"
    )

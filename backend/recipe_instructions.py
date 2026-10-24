"""Closed generation protocol; public recipes retain Thai string instructions."""
import json
import math
import re

from recipe_contracts import ingredient_names, normalize_estimated_total_time, validate_generated_recipe_shape

THAI_FIELD_PATTERN = r"^[฀-๿a-zA-Z0-9 .,()\-/%:']+$"
ENGLISH_FIELD_PATTERN = r"^[a-zA-Z0-9 .,()\-/%:']+$"
FORMAT_ERROR = "_generation_validation_error"
_PLAN = "_instruction_plan"
_PROTOCOL = "_instruction_protocol"
_SINGLE_ROLE_ACTIONS = ("rest", "drain", "set_aside")
_TARGET_ACTIONS = {"add", "season", "serve", "serve_separately", *_SINGLE_ROLE_ACTIONS}
_COOKING_ACTIONS = {"stir_fry", "fry", "boil", "simmer", "steam", "bake", "grill", "air_fry", "dry_fry", "water_saute"}
# Bounded reviewed raw identities, not a general food-safety classifier.
_REQUIRES_COOKING = {"minced pork", "beef steak", "shrimp", "egg", "ไข่ไก่"}
_ACTIONS = {
    "wash": "ล้าง{food}ให้สะอาด", "cut": "หั่น{food}",
    "chop": "สับ{food}", "slice": "ซอย{food}", "peel": "ปอกเปลือก{food}",
    "crush": "โขลก{food}", "beat": "ตี{food}ให้เข้ากัน",
    "mix": "คลุกเคล้า{food}ให้เข้ากัน", "add": "ใส่{food}ลงในส่วนผสมจากขั้นตอนก่อนหน้า",
    "season": "ปรุงรสส่วนผสมจากขั้นตอนก่อนหน้าด้วย{food}",
    "heat": "ตั้งกระทะอุ่น{food}",
    "stir_fry": "ผัด{food}ในกระทะเดิมให้สุกทั่วถึง",
    "fry": "ทอด{food}ให้สุกทั่วถึง", "boil": "ต้ม{food}ให้สุกทั่วถึง",
    "simmer": "เคี่ยว{food}ให้สุกทั่วถึง", "steam": "นึ่ง{food}ให้สุกทั่วถึง",
    "bake": "อบ{food}ให้สุกทั่วถึง", "grill": "ย่าง{food}ให้สุกทั่วถึง",
    "air_fry": "อบ{food}ด้วยหม้อทอดไร้น้ำมันให้สุกทั่วถึง",
    "dry_fry": "คั่วแห้ง{food}ให้สุกทั่วถึง", "water_saute": "ผัดน้ำ{food}ให้สุกทั่วถึง",
    "marinate": "หมัก{food}ในตู้เย็น", "drain": "สะเด็ดน้ำ{food}",
    "rest": "พัก{food}", "serve": "จัดเสิร์ฟ{food}",
    "set_aside": "ตัก{food}ขึ้นพักไว้",
    "serve_separately": "จัดเสิร์ฟ{food}แยกต่างหาก",
}


def instruction_registry(ingredients):
    from recipe_checks import _identity, _PANTRY
    keys = dict.fromkeys([*(_identity(name) for name in ingredient_names(ingredients)), *sorted(_PANTRY)])
    return {f"i{index}": name for index, name in enumerate(keys, 1)}


def _label(name):
    from recipe_checks import CATALOG_ALIASES, _EXTRA_ALIASES
    return (CATALOG_ALIASES.get(name) or _EXTRA_ALIASES.get(name) or (name,))[0]


def ingredient_declaration_pattern(ingredients):
    from recipe_checks import CATALOG_ALIASES, _EXTRA_ALIASES, _AMOUNT_OR_RANGE, _VAGUE
    names = set(ingredient_names(ingredients))
    for name in instruction_registry(ingredients).values():
        names.update((name, *CATALOG_ALIASES.get(name, _EXTRA_ALIASES.get(name, ()))))
    alternatives = "|".join(re.escape(name) for name in sorted(names, key=lambda name: (-len(name), name)))
    quantity = rf"{_AMOUNT_OR_RANGE}\s*[a-zA-Zก-๙.]*"
    # Keep unknown amounts and reviewed vague/range syntax; numeric validity stays independent.
    tail = rf"{quantity}|(?:{_VAGUE}|\({_VAGUE}\))(?:\s+{quantity})?"
    return rf"^(?:{alternatives})(?:\s*(?:{tail}))?$"


def instruction_prompt(ingredients):
    registry = instruction_registry(ingredients)
    first, second = list(registry)[:2]
    examples = [{"action": action, "ingredients": used, "targets": targets, "excluded": []}
                for action, used, targets in (
                    ("fry", [first], []), ("simmer", [first], []),
                    ("add", [second], [first]), ("season", [second], [first]),
                    ("serve", [second], [first]), ("rest", [], [first]), ("drain", [first], []),
                    ("set_aside", [], [first]))]
    return (
        "\nขั้นตอนใช้โครงสร้างเท่านั้น: instructions เป็นรายการ object ตาม response schema ไม่ใช่ประโยคข้อความ\n"
        "รหัสวัตถุดิบที่ backend กำหนด: " + "; ".join(f"{key}={name} / {_label(name)}" for key, name in registry.items()) + "\n"
        "action เลือกวิธีปรุงจาก enum; ingredients คือรหัสที่ใช้จริงในขั้นตอนนั้น และต้องประกาศชื่อเต็มพร้อมปริมาณใน adjusted_ingredients\n"
        "ทุกขั้นต้องมี targets เป็นรายการรหัส แยกจาก ingredients และ excluded; ใช้ [] เมื่อไม่ต้องมีเป้าหมาย\n"
        "add/season: targets คืออาหารหรือส่วนผสมที่รับการเติม/ปรุงรส; ingredients คือสิ่งที่เติมหรือเครื่องปรุง ห้ามใช้รหัสซ้ำระหว่างสองช่อง\n"
        "serve/serve_separately: targets คืออาหารหลักที่จัดเสิร์ฟ; ingredients คือของโรยหน้าหรือของเคียง ถ้าไม่มีให้ใช้ [] ห้ามเสิร์ฟเฉพาะของโรยหน้า\n"
        "rest/drain/set_aside ใช้ ingredients หรือ targets ระบุอาหารเพียงช่องเดียว อีกช่องต้องเป็น []; วิธีอื่นที่ไม่ใช่ add/season/serve/serve_separately ใช้ targets=[]\n"
        "set_aside คือตักอาหารขึ้นพักไว้ก่อนใช้กระทะทำส่วนถัดไป เช่น ไข่ดาว; ต้องระบุรหัสอาหารจริง ห้ามถือว่าตักขึ้นแล้วเอง\n"
        "ขั้นเตรียม/ปรุง เช่น fry/stir_fry/simmer ต้องใส่สิ่งที่ปรุงใน ingredients และ targets=[]; ห้ามคัดลอกรหัสซ้ำลง targets\n"
        "add/season ห้ามปล่อย targets ว่าง: ระบุรหัสส่วนผสมที่มีอยู่และรับการเติม เช่น รหัสน้ำในหม้อต้ม\n"
        "ตัวอย่างต่อไปนี้แสดงแต่ละบทบาทแยกกัน ไม่ใช่ลำดับสูตร ไม่ได้บังคับให้ใช้รหัสหรือเพิ่มวัตถุดิบตามตัวอย่าง\n"
        "ตัวอย่างบทบาท JSON: " + json.dumps(examples, ensure_ascii=False) + "\n"
        "หมูสับ เนื้อสเต๊ก กุ้ง ไข่ และไข่ไก่ที่ใช้ ต้องระบุรหัสใน ingredients ของขั้นปรุงให้สุก เช่น stir_fry/fry/boil ก่อนเสิร์ฟ; beat/add/heat อย่างเดียวไม่ถือว่าปรุงสุก และห้ามนับเวลาหรืออุณหภูมิแทนขั้นปรุง\n"
        "adjusted_ingredients ต้องเขียนชื่อก่อนแล้วตามด้วยปริมาณ เช่น หมูสับ 300 กรัม ไม่ใช่ 300 กรัม หมูสับ; ห้ามใส่รหัส iN หรือ (iN) ในรายการนี้ รหัสใช้เฉพาะ instructions\n"
        "excluded คือรหัสที่ไม่ใส่ ไม่ต้องประกาศใน adjusted_ingredients และห้ามซ้ำกับ ingredients ในขั้นตอนเดียวกัน\n"
        "ห้ามแต่งรหัส ห้ามส่ง text/detail หรือชื่ออาหารในขั้นตอน ใช้ minutes และ temperature_c เป็นตัวเลขบวกเมื่อจำเป็น\n"
        "ถ้า ingredients ว่างให้ระบุอาหารใน targets เมื่อวิธีรองรับ ห้ามอาศัยคำว่าขั้นก่อนหน้าเพื่อข้ามรหัสโปรตีนในขั้นปรุงสุก\n"
        "stir_fry ใช้กระทะเดิมต่อเนื่อง ก่อนเริ่มอุ่นน้ำมันรอบใหม่ต้องใช้ set_aside ตักอาหารเดิมขึ้นพัก หรือระบุ serve/serve_separately ถ้าเสิร์ฟอาหารนั้นแล้ว; ถ้าอุ่นอาหารเดิมให้ระบุรหัสอาหารนั้นใน heat ด้วย\n"
        "backend จะสร้างประโยคไทยเอง; action ที่ทำให้สุกต้องให้เวลา/อุณหภูมิเหมาะกับอาหาร ไม่ถือว่าตัวเลขรับรองความปลอดภัย\n"
        "estimated_total_time คือช่วงเวลารวมโดยประมาณของสูตรที่ปรับแล้วสำหรับ servings นี้ หน่วยนาที\n"
        "รวมเวลาเตรียม ปรุง และรอตามขั้นตอนจนพร้อมกิน โดยคำนึงถึงงานที่ทำพร้อมกันได้\n"
        "วัตถุดิบสำเร็จรูปที่ระบุถือว่าเตรียมแล้ว ไม่รวมซื้อของ ละลายน้ำแข็ง หรือเตรียมส่วนประกอบอื่น เว้นแต่สูตรระบุ\n"
        "ประเมินใหม่จากสูตรสุดท้าย ห้ามคัดลอกเวลาสูตรตั้งต้นหรือคูณเวลาตาม servings โดยตรง\n"
        "ใช้ min_minutes และ max_minutes เป็นจำนวนเต็มบวก โดย max_minutes >= min_minutes; ถ้าประเมินไม่ได้ให้ส่ง null\n"
        "เวลานี้เป็นค่าประเมินของ AI ไม่ใช่เวลาที่จับวัดหรือรับประกัน ห้ามคัดลอกตัวเลขตัวอย่างโดยไม่ประเมินสูตร\n"
    )


def generation_schema(ingredients):
    ids = list(instruction_registry(ingredients))
    refs = {"type": "array", "items": {"type": "string", "enum": ids}}
    step = {"type": "object", "additionalProperties": False, "properties": {
        "action": {"type": "string", "enum": list(_ACTIONS)},
        "ingredients": refs, "targets": refs, "excluded": refs,
        "minutes": {"type": ["number", "null"]}, "temperature_c": {"type": ["number", "null"]},
    }, "required": ["action", "ingredients", "targets", "excluded"]}
    step = {"anyOf": [
        {**step, "properties": {**step["properties"],
            "action": {"type": "string", "enum": actions},
            "ingredients": {**refs, **used_bounds}, "targets": {**refs, **target_bounds}}}
        for actions, used_bounds, target_bounds in (
            ([action for action in _ACTIONS if action not in _TARGET_ACTIONS or action in _SINGLE_ROLE_ACTIONS],
             {"minItems": 1}, {"maxItems": 0}),
            (["add", "season"], {"minItems": 1}, {"minItems": 1}),
            (["serve", "serve_separately"], {}, {"minItems": 1}),
            (list(_SINGLE_ROLE_ACTIONS), {"maxItems": 0}, {"minItems": 1}),
        )
    ]}
    properties = {
        "recipe_name": {"type": "string", "pattern": ENGLISH_FIELD_PATTERN},
        "servings": {"type": "integer"},
        "estimated_total_time": {"anyOf": [{
            "type": "object", "additionalProperties": False,
            "properties": {key: {"type": "integer", "minimum": 1, "maximum": 9_007_199_254_740_991}
                           for key in ("min_minutes", "max_minutes")},
            "required": ["min_minutes", "max_minutes"],
        }, {"type": "null"}]},
        "adjusted_ingredients": {"type": "array", "items": {"type": "string", "pattern": ingredient_declaration_pattern(ingredients)}},
        "diet_tags": {"type": "array", "items": {"type": "string", "pattern": ENGLISH_FIELD_PATTERN}},
        "nutrition": {"type": "object", "additionalProperties": False, "properties": {
            "basis": {"type": "string", "enum": ["per_serving"]},
            **{key: {"type": "number"} for key in ("calories", "protein_g", "carbs_g", "fat_g")},
        }, "required": ["basis", "calories", "protein_g", "carbs_g", "fat_g"]},
        "instructions": {"type": "array", "items": step},
        "safety_warning": {"type": "string", "pattern": THAI_FIELD_PATTERN},
    }
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}


def _render(step):
    food = " และ ".join(_label(name) for name in step["ingredients"]) or "ส่วนผสมจากขั้นตอนก่อนหน้า"
    text = _ACTIONS[step["action"]].format(food=food)
    if step["action"] in ("fry", "stir_fry"):
        from recipe_checks import _OILS
        # shortcut: only reviewed oil identities are media; extend _OILS after reviewing another oil.
        oils = [name for name in step["ingredients"] if name in _OILS]
        foods = [name for name in step["ingredients"] if name not in _OILS]
        if oils and foods:
            food = " และ ".join(_label(name) for name in foods)
            medium = " และ ".join(_label(name) for name in oils)
            text = (f"ทอด{food}ใน{medium}ให้สุกทั่วถึง" if step["action"] == "fry"
                    else f"ผัด{food}ในกระทะเดิมด้วย{medium}ให้สุกทั่วถึง")
    if "targets" in step:
        target = " และ ".join(_label(name) for name in step["targets"])
        if step["action"] == "season":
            text = f"ปรุงรส{target}ด้วย{food}"
        elif step["action"] == "add":
            text = f"ใส่{food}ลงในส่วนผสมที่มี{target}"
        elif step["action"] in ("serve", "serve_separately"):
            text = f"จัดเสิร์ฟอาหารที่มี{target}"
            if step["ingredients"]:
                text += f" พร้อม{food}"
            if step["action"] == "serve_separately":
                text += " แยกต่างหาก"
        elif target:
            text = _ACTIONS[step["action"]].format(food=target)
    if step["excluded"]:
        text += " โดยไม่ใส่" + " และ ".join(_label(name) for name in step["excluded"])
    if step.get("minutes") is not None:
        text += f" เป็นเวลา {step['minutes']:g} นาที"
    if step.get("temperature_c") is not None:
        text += f" ที่อุณหภูมิ {step['temperature_c']:g} องศาเซลเซียส"
    return text


def _validate_step(step, allowed, index):
    if not isinstance(step, dict) or set(step) - {"action", "ingredients", "targets", "excluded", "minutes", "temperature_c"}:
        raise ValueError(f"Invalid structured instruction at step {index}; no free text allowed")
    if not isinstance(step.get("action"), str) or step["action"] not in _ACTIONS:
        raise ValueError(f"Unknown cooking action at step {index}")
    for role in ("ingredients", "excluded", *(("targets",) if "targets" in step else ())):
        refs = step.get(role)
        if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in allowed for ref in refs) or len(set(refs)) != len(refs):
            raise ValueError(f"Unknown or duplicate {role} reference at step {index}")
    targets = set(step.get("targets", []))
    if (set(step["ingredients"]) & targets or (set(step["ingredients"]) | targets) & set(step["excluded"])
            or (index == 1 and not (step["ingredients"] or targets))):
        raise ValueError(f"Conflicting or empty ingredient references at step {index}")
    if targets and step["action"] not in _TARGET_ACTIONS:
        raise ValueError(f"Action {step['action']} does not accept targets at step {index}")
    if targets and step["ingredients"] and step["action"] in _SINGLE_ROLE_ACTIONS:
        raise ValueError(f"Action {step['action']} must use targets or ingredients, not both, at step {index}")
    for field in ("minutes", "temperature_c"):
        value = step.get(field)
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value <= 0):
            raise ValueError(f"Invalid {field} at step {index}")


def _validate_workflow(plan, *, check_cooking=False):
    from recipe_checks import _OILS
    cooked, used_raw = set(), set()
    pan_food = set()
    for index, step in enumerate(plan, 1):
        if "targets" not in step:
            raise ValueError(f"Missing targets field at step {index}")
        action = step["action"]
        if action in ("add", "season", "serve", "serve_separately") and not step["targets"]:
            raise ValueError(f"Action {action} needs explicit targets at step {index}")
        if action in ("add", "season") and not step["ingredients"]:
            raise ValueError(f"Action {action} needs ingredients at step {index}")
        if action in _SINGLE_ROLE_ACTIONS and not (step["targets"] or step["ingredients"]):
            raise ValueError(f"Action {action} needs explicit targets or ingredients at step {index}")
        if check_cooking:
            ingredients = set(step["ingredients"])
            if action in ("fry", "stir_fry", "dry_fry", "water_saute"):
                if action in ("fry", "stir_fry") and ingredients and ingredients <= _OILS:
                    raise ValueError(f"Oil-only frying at step {index}; use heat for the oil and name the food in the cooking step")
                pan_food.update(ingredients - _OILS)
            elif action in ("set_aside", "serve", "serve_separately"):
                pan_food.difference_update(ingredients | set(step["targets"]))
            elif action == "heat" and ingredients and ingredients <= _OILS and pan_food:
                raise ValueError(f"New oil-heating cycle at step {index} still has pan food: {', '.join(sorted(pan_food))}; use set_aside or serve explicitly, or name the food being reheated")
        used_raw |= (set(step["ingredients"]) | set(step["targets"])) & _REQUIRES_COOKING
        if action in _COOKING_ACTIONS:
            cooked.update(step["ingredients"])
        served_raw = (set(step["ingredients"]) | set(step["targets"])) & _REQUIRES_COOKING
        if check_cooking and action in ("serve", "serve_separately") and served_raw - cooked:
            raise ValueError(f"Missing explicit cooking before serving at step {index}: {', '.join(sorted(served_raw - cooked))}")
    if check_cooking and used_raw - cooked:
        raise ValueError(f"Missing explicit cooking action: {', '.join(sorted(used_raw - cooked))}")


def normalize_generated_recipe(raw, ingredients, *, require_workflow=False):
    from recipe_checks import _line
    schema = generation_schema(ingredients)
    # Timing alone is optional display metadata and must not trigger a retry.
    if not isinstance(raw, dict) or set(raw) - {"estimated_total_time"} != set(schema["required"]) - {"estimated_total_time"}:
        raise ValueError("Invalid generated recipe fields")
    registry = instruction_registry(ingredients)
    steps = raw.get("instructions")
    if not isinstance(steps, list) or not steps:
        raise ValueError("Invalid structured instructions")
    lines = raw.get("adjusted_ingredients")
    pattern = schema["properties"]["adjusted_ingredients"]["items"]["pattern"]
    if not isinstance(lines, list) or not lines or any(not isinstance(line, str) or re.fullmatch(pattern, line) is None for line in lines):
        raise ValueError("Invalid ingredient declaration format: use a permitted name then quantity, e.g. หมูสับ 300 กรัม; no IDs in adjusted_ingredients")
    declared = {_line(line, ingredients)[0] for line in raw.get("adjusted_ingredients", []) if isinstance(line, str)} if isinstance(raw.get("adjusted_ingredients"), list) else set()
    plan = []
    for index, step in enumerate(steps, 1):
        _validate_step(step, registry, index)
        resolved = {**step, **{role: [registry[ref] for ref in step[role]] for role in ("ingredients", "excluded", *(("targets",) if "targets" in step else ()))}}
        if not (set(resolved["ingredients"]) | set(resolved.get("targets", []))) <= declared:
            raise ValueError(f"Undeclared ingredient in step {index}; add all used references to adjusted_ingredients")
        plan.append(resolved)
    modern = require_workflow or any("targets" in step for step in plan)
    if modern:
        _validate_workflow(plan)
    recipe = {**raw, "instructions": [_render(step) for step in plan], _PLAN: plan,
              _PROTOCOL: 2 if modern else 1,
              "estimated_total_time": normalize_estimated_total_time(raw.get("estimated_total_time"))}
    valid, reason = validate_generated_recipe_shape(recipe)
    if not valid:
        raise ValueError(reason)
    for field, values, pattern in (
        ("recipe_name", [recipe["recipe_name"]], ENGLISH_FIELD_PATTERN),
        ("diet_tags", recipe["diet_tags"], ENGLISH_FIELD_PATTERN),
        ("adjusted_ingredients", recipe["adjusted_ingredients"], THAI_FIELD_PATTERN),
        ("safety_warning", [recipe["safety_warning"]], THAI_FIELD_PATTERN),
    ):
        if any(re.fullmatch(pattern, value) is None for value in values):
            raise ValueError(f"Invalid language or characters in {field}")
    if set(recipe["nutrition"]) != set(schema["properties"]["nutrition"]["required"]):
        raise ValueError("Invalid nutrition fields")
    return recipe


def instruction_uses(recipe):
    from recipe_checks import _declared
    plan = recipe.get(_PLAN)
    if not isinstance(plan, list) or not plan:
        raise ValueError("Missing structured instruction plan")
    declared = _declared(recipe)
    for index, step in enumerate(plan, 1):
        _validate_step(step, declared | set(step.get("excluded", [])) if isinstance(step, dict) else set(), index)
        if not (set(step["ingredients"]) | set(step.get("targets", []))) <= declared:
            raise ValueError(f"Undeclared ingredient in step {index}")
    if recipe.get(_PROTOCOL, 1) == 2:
        _validate_workflow(plan)
    if recipe.get("instructions") != [_render(step) for step in plan]:
        raise ValueError("Instructions differ from validated cooking actions")
    return [list(dict.fromkeys([*step["ingredients"], *step.get("targets", [])])) for step in plan]


def public_recipe(recipe):
    return {key: value for key, value in recipe.items() if key not in (_PLAN, _PROTOCOL, FORMAT_ERROR)}


def parse_generated_recipe(text, ingredients):
    try:
        return normalize_generated_recipe(json.loads(text), ingredients, require_workflow=True)
    except (ValueError, TypeError, OverflowError) as error:
        return {FORMAT_ERROR: str(error)}

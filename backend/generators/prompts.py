# backend/generators/prompts.py
import json

from recipe_checks import ingredient_prompt_guidance
from recipe_instructions import instruction_prompt

# Legacy training targets use prose; current generators get an ID-based example.
FEW_SHOT_EXAMPLE_RECIPE = {
    "recipe_name": "Stir-Fried Basil Chicken",
    "servings": 2,
    "adjusted_ingredients": ["อกไก่ 300 กรัม", "ใบกะเพรา 1 ถ้วย", "น้ำมัน 1 ช้อนโต๊ะ", "น้ำปลา 1 ช้อนโต๊ะ"],
    "diet_tags": ["Thai", "high_protein"],
    "nutrition": {"basis": "per_serving", "calories": 380, "protein_g": 32, "carbs_g": 8, "fat_g": 20},
    "instructions": [
        "1. ตั้งกระทะใส่น้ำมันบนไฟกลาง",
        "2. ใส่อกไก่สับผัดจนสุก",
        "3. ปรุงรสด้วยน้ำปลา ใส่ใบกะเพราผัดให้เข้ากัน",
    ],
    "safety_warning": "ตรวจสอบว่าอกไก่สุกทั่วถึงก่อนรับประทาน",
}


def build_recipe_prompt(ingredients: list, user_prefs: dict, base_recipe: dict, feedback: str | None = None, include_example: bool = False, *, structured_instructions: bool = True) -> str:
    """Shared generator prompt; only historical training opts out of structured steps."""
    example_section = ""
    language_rule_section = ""
    if include_example:
        example = {"instructions": [{"action": "cut", "ingredients": ["i1"], "targets": [], "excluded": []}]} if structured_instructions else FEW_SHOT_EXAMPLE_RECIPE
        example_json = json.dumps(example, ensure_ascii=False, indent=2)
        example_section = f"""
        ตัวอย่างที่ถูกต้อง (โครงสร้าง JSON ที่ต้องเลียนแบบ ไม่ใช่คำตอบจริงสำหรับ request นี้):
        {example_json}
        """
        # Local-model-only rule (gated behind include_example, same as the
        # few-shot example above) — never added to GeminiGenerator's prompt,
        # to keep it content-matched with main.py's production prompt.
        # Added 2026-09-18 after a real benchmark run showed Qwen3.5-4B/9B
        # repeatedly leaking non-Thai, non-English script (Greek, Chinese)
        # into fields the schema already requires to be Thai — this is not
        # about banning English (recipe_name/diet_tags are already required
        # in English by the schema below; English is fine where the schema
        # already calls for it) but about garbage scripts with no reason to
        # appear at all.
        language_rule_section = """
        7. ภาษา (Language): adjusted_ingredients และ safety_warning ต้องเป็นภาษาไทย อนุญาตชื่อวัตถุดิบอังกฤษที่ยืนยันได้ ห้ามภาษาอื่นปน; instructions ใช้ action และรหัสตาม schema เท่านั้น backend จะสร้างประโยคไทย
        8. การผัด (Stir-Frying): การผัดแบบใช้น้ำมันต้องประกาศน้ำมันและระบุการใช้ในขั้นตอนนั้นหรือก่อนหน้า วิธีที่ไม่ใช้น้ำมันต้องระบุให้ชัด
        9. การแพ้อาหาร (Allergy Enforcement): หากวัตถุดิบที่ผู้ใช้มีตรงกับสารก่อภูมิแพ้ที่ระบุไว้ ต้องตัดวัตถุดิบนั้นออกจาก adjusted_ingredients ทั้งหมด ห้ามใส่เด็ดขาดแม้จะเป็นวัตถุดิบที่ผู้ใช้มีอยู่จริงในรายการก็ตาม
        """
        if not structured_instructions:
            language_rule_section = language_rule_section.replace(
                "adjusted_ingredients และ safety_warning ต้องเป็นภาษาไทย อนุญาตชื่อวัตถุดิบอังกฤษที่ยืนยันได้ ห้ามภาษาอื่นปน; instructions ใช้ action และรหัสตาม schema เท่านั้น backend จะสร้างประโยคไทย",
                "adjusted_ingredients, instructions และ safety_warning ต้องเป็นภาษาไทย อนุญาตชื่อวัตถุดิบอังกฤษที่ยืนยันได้ ห้ามภาษาอื่นปน",
            )

    instruction_example = '[{"action": "mix", "ingredients": ["i1"], "targets": [], "excluded": []}]' if structured_instructions else '["1. ขั้นตอนแรก (IN THAI)...", "2. ขั้นตอนต่อไป (IN THAI)..."]'
    time_example = '\n            "estimated_total_time": {"min_minutes": 15, "max_minutes": 20},' if structured_instructions else ""

    feedback_section = ""
    if feedback:
        feedback_section = f"""
        ผลตรวจสอบจากรอบก่อนหน้า (MUST FIX): สูตรที่คุณสร้างในรอบก่อนไม่ผ่านการตรวจสอบ เนื่องจาก: "{feedback}"
        กรุณาแก้ไขปัญหานี้โดยเฉพาะในรอบนี้ โดยยังคงรักษาส่วนอื่นที่ถูกต้องไว้เหมือนเดิม
        """

    return f"""
        คุณคือ Executive Chef และนักโภชนาการคลินิกที่มีประสบการณ์สูง
        หน้าที่ของคุณคือการนำ "สูตรอาหารตั้งต้น" มาดัดแปลงให้เข้ากับ "วัตถุดิบที่ผู้ใช้มี" และ "เงื่อนไขโภชนาการ"
        โดยต้องคำนึงถึงความปลอดภัยทางอาหาร (Food Safety) และหลักการทำอาหารที่ถูกต้องเป็นอันดับหนึ่ง

        ข้อมูลของคุณมีดังนี้:
        1. วัตถุดิบที่ผู้ใช้มี : {ingredients}
        2. เงื่อนไขและข้อควรระวังของผู้ใช้: {user_prefs}
        3. สูตรอาหารตั้งต้น (อ้างอิงโภชนาการจากสูตรนี้): {base_recipe}
        {ingredient_prompt_guidance(ingredients)}
        รายการวัตถุดิบนี้บอกเฉพาะชนิดที่ผู้ใช้ระบุว่ามี ไม่ได้ระบุปริมาณคงเหลือจริง
        ห้ามสรุปว่าวัตถุดิบเพียงพอ ไม่เพียงพอ หรือต้องซื้อเพิ่มจากรายการนี้
        servings คือจำนวนที่เสิร์ฟของสูตรนี้
        ปริมาณใน adjusted_ingredients ต้องเป็นปริมาณรวมสำหรับทั้งสูตร ซึ่งครอบคลุมจำนวนที่เสิร์ฟตาม servings
        ค่า calories, protein_g, carbs_g และ fat_g ใน nutrition ต้องเป็นค่าต่อ 1 ที่เสิร์ฟ
        หากประมาณค่าโภชนาการเป็นค่ารวมทั้งสูตร ต้องหารด้วย servings ก่อนตอบ
        {feedback_section}
        กฎเหล็กด้านความปลอดภัยและคุณภาพ (MUST FOLLOW STRICTLY):
        1. ความปลอดภัยอาหาร (Food Safety): ห้ามแนะนำให้รับประทานเนื้อสัตว์ดิบ (ยกเว้นวัตถุดิบที่ระบุว่าทานดิบได้) ต้องระบุการทำเนื้อสัตว์ ไก่ หมู หรืออาหารทะเลให้สุกอย่างชัดเจน และห้ามมีขั้นตอนที่เสี่ยงต่อการปนเปื้อนข้าม (Cross-contamination)
        2. ข้อควรระวังการแพ้ (Allergy Risks): ต้องตรวจสอบและปฏิบัติตาม {user_prefs} อย่างเคร่งครัด หากมีการแพ้อาหาร ห้ามใส่วัตถุดิบนั้นและวัตถุดิบแฝงเด็ดขาด
        3. ปริมาณและสัดส่วน (Logical Proportions): กำหนดปริมาณวัตถุดิบและเครื่องปรุงให้อยู่ในเกณฑ์มาตรฐานที่มนุษย์ทานได้จริง ห้ามใส่เครื่องปรุงรสจัดเกินไป (เช่น เกลือ 5 ช้อนโต๊ะ หรือน้ำมัน 1 ถ้วย)
        4. ขั้นตอนสมเหตุสมผล (Logical Workflow): ระบุวิธีและลำดับการปรุงให้ชัด การผัด/ทอดแบบใช้น้ำมันต้องประกาศน้ำมันและระบุการใช้ก่อนหรือขณะปรุง วิธีไร้น้ำมันต้องบอกวิธีให้ชัดเจน
        5. ความเข้ากันของรสชาติ (Flavor Pairing): ใช้กฎของ HomeMade ตามบริบทที่ระบุด้านล่าง ไม่ตัดสินว่าคู่ส่วนผสมผิดทุกเมนูจากชื่อที่ปรากฏร่วมกัน
        6. ห้ามมโนวัตถุดิบ (No Hallucination): ใช้วัตถุดิบเฉพาะที่มีใน {ingredients} และสามารถเสริมด้วยเครื่องปรุงพื้นฐานสามัญประจำบ้าน (เกลือ, พริกไทย, น้ำมัน, น้ำปลา, ซีอิ๊ว, น้ำตาล, น้ำเปล่า) ได้เท่านั้น ห้ามคิดค้นวัตถุดิบขึ้นมาเอง
        {language_rule_section}

        คำสั่ง:
        - ปรับปรุงขั้นตอนและคำนวณโภชนาการใหม่ (Calories, Protein, Carbs, Fat) ให้ใกล้เคียงความเป็นจริงที่สุด
        - ตอบกลับมาเป็นรูปแบบ JSON เท่านั้น ห้ามมีข้อความอื่นปนเด็ดขาด โดยใช้โครงสร้างดังนี้:

        {{
            "recipe_name": "ชื่อเมนูที่สมเหตุสมผล (MUST BE IN ENGLISH)",
            "servings": 2,{time_example}
            "adjusted_ingredients": ["วัตถุดิบ 1 (พร้อมระบุปริมาณที่ถูกต้อง IN THAI)", "วัตถุดิบ 2 (IN THAI)"],
            "diet_tags": ["tag1 (MUST BE IN ENGLISH)", "tag2 (MUST BE IN ENGLISH)"],
            "nutrition": {{
                "basis": "per_serving",
                "calories": ตัวเลข,
                "protein_g": ตัวเลข,
                "carbs_g": ตัวเลข,
                "fat_g": ตัวเลข
            }},
            "instructions": {instruction_example},
            "safety_warning": "คำเตือนความปลอดภัย (IN THAI) เช่น เรื่องการแพ้อาหาร (หากไม่มีให้ใส่ข้อความว่า 'ระวังความร้อนขณะประกอบอาหาร')"
        }}
        {example_section}
        {instruction_prompt(ingredients) if structured_instructions else ""}
        """

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Recipe:
    dish_name: str
    ingredient_lines: list[str] = field(default_factory=list)
    instruction_text: str = ""


def parse_ingredient_block(raw) -> list[str]:
    """Splits the source dataset's bulleted Ingredient column text (each
    item on its own '- ...' line, blank lines between) into a clean list
    of ingredient strings with the leading bullet/whitespace stripped."""
    if not isinstance(raw, str) or not raw.strip():
        return []
    lines = []
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("-"):
            item = line.lstrip("-").strip()
            if item:  # only append non-empty items (drop bare "- " lines)
                lines.append(item)
    return lines


def load_recipes(xlsx_path: str) -> list[Recipe]:
    """Loads backend-external source data:
    pythainlp/thai_food_v1.0's thai_food_parsed.xlsx (columns
    name/text/DishName/Ingredient/Instruction, 159 rows, verified
    2026-09-20 -- see design spec §3). Falls back to parsing the
    ingredient block out of `text` when the `Ingredient` column is empty
    for a row (9/159 rows per the same verification), since `text`
    always contains the full markdown-formatted recipe."""
    df = pd.read_excel(xlsx_path)
    recipes = []
    for _, row in df.iterrows():
        dish_name = row.get("DishName")
        if not isinstance(dish_name, str) or not dish_name.strip():
            continue
        ingredient_raw = row.get("Ingredient")
        if not isinstance(ingredient_raw, str) or not ingredient_raw.strip():
            ingredient_raw = _extract_ingredient_section_from_text(row.get("text"))
        instruction_text = row.get("Instruction")
        if not isinstance(instruction_text, str) or not instruction_text.strip():
            instruction_text = _extract_instruction_section_from_text(row.get("text"))
        lines = parse_ingredient_block(ingredient_raw)
        if not lines or not isinstance(instruction_text, str) or not instruction_text.strip():
            continue  # can't build a usable training example without both
        recipes.append(
            Recipe(dish_name=dish_name.strip(), ingredient_lines=lines, instruction_text=instruction_text.strip())
        )
    return recipes


def _extract_ingredient_section_from_text(text) -> str:
    """Extracts the ingredient section from markdown-formatted recipe text
    (text after "## เครื่องปรุง" header). If the header is present, extracts
    everything after it until the next section header or end of text."""
    if not isinstance(text, str):
        return ""
    if "## เครื่องปรุง" not in text:
        return ""
    section = text.split("## เครื่องปรุง", 1)[1]
    # if there's a next section header (e.g. "## วิธีทำ"), extract up to it
    if "## วิธีทำ" in section:
        section = section.split("## วิธีทำ", 1)[0]
    return section.strip()


def _extract_instruction_section_from_text(text) -> str:
    """Extracts the instruction section from markdown-formatted recipe text
    (text after "## วิธีทำ" header). If the header is present, extracts
    everything after it."""
    if not isinstance(text, str):
        return ""
    if "## วิธีทำ" not in text:
        return ""
    return text.split("## วิธีทำ", 1)[1].strip()

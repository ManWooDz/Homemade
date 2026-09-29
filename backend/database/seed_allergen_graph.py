# backend/database/seed_allergen_graph.py
"""Seed the allergen Knowledge Graph (ingredient_nodes + allergen_edges).

Edge semantics: (A -> B) means exactly "a typical preparation of A contains B".
Not "always", not "may contain". An edge is only added when the named item
reliably implies the composition (a near-universal recipe), not when some
recipes do and some do not.

Two sources of edges:
  1. Floor edges, generated programmatically from allergen_kg.floor.FLOOR_BLOCKS
     so the KG can never be weaker than the hardcoded safety floor.
  2. Curated edges: real Thai ingredients / prepared components with genuine
     multi-hop chains (e.g. พริกแกงเผ็ด -> กะปิ -> allergen:shrimp) where real
     composition supports them.

Citations: the composition claims below are recorded as "general Thai culinary
knowledge" (or the named general reference) because that is the honest basis;
no Open Food Facts listing was re-fetched when writing this file, so none is
cited. Replace/augment a citation with a specific OFF product listing only
after actually checking that listing.

Substring safety: recipe text is matched by substring against node names, so
names are deliberately specific (no very short syllables). Known accepted
limitations are noted next to the edges concerned.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from allergen_kg.floor import FLOOR_BLOCKS
from allergen_kg.graph import ALLERGEN_NODE_PREFIX, allergen_node_name
from database.models import AllergenEdge, IngredientNode

FLOOR_CITATION = "floor: existing ALLERGEN_MAP blocks list"
GTK = "general Thai culinary knowledge"

EDGES: list[tuple[str, str, str]] = []
_SEEN: set[tuple[str, str]] = set()


def _add(sources, target: str, citation: str) -> None:
    """Append (source -> target) for each source, skipping exact duplicates."""
    if isinstance(sources, str):
        sources = [sources]
    for source in sources:
        assert source and source == source.strip(), repr(source)
        assert target and target == target.strip(), repr(target)
        assert not source.startswith(ALLERGEN_NODE_PREFIX), source
        assert source != target, source
        if (source, target) in _SEEN:
            continue
        _SEEN.add((source, target))
        EDGES.append((source, target, citation))


# ---------------------------------------------------------------------------
# 1. Floor edges (generated, never retyped)
# ---------------------------------------------------------------------------
for _key, _terms in FLOOR_BLOCKS.items():
    _add(list(_terms), allergen_node_name(_key), FLOOR_CITATION)


# ---------------------------------------------------------------------------
# 2. Curated edges
# ---------------------------------------------------------------------------

# ---- shrimp -------------------------------------------------------------
# Thai curry pastes are pounded with shrimp paste (กะปิ). กะปิ -> allergen:shrimp
# is a floor edge, so each of these is a genuine 2-hop chain whose head does
# not contain any shrimp term. Vegetarian (เจ) pastes exist and are not modeled.
_add(
    [
        "พริกแกงเผ็ด", "พริกแกงแดง", "พริกแกงเขียวหวาน", "พริกแกงส้ม",
        "พริกแกงกะหรี่", "พริกแกงเหลือง", "พริกแกงป่า", "พริกแกงมัสมั่น",
        "พริกแกงพะแนง", "พริกแกงคั่วกลิ้ง", "พริกแกงเลียง", "น้ำพริกกะปิ",
        "น้ำพริกลงเรือ",
    ],
    "กะปิ",
    f"{GTK} (Thai curry pastes and น้ำพริก are pounded with shrimp paste)",
)
# Dried shrimp (กุ้งแห้ง) is an intermediate node; it also carries the
# floor term "กุ้ง", so the link to the allergen is stated explicitly.
_add(
    ["กุ้งแห้ง"],
    "allergen:shrimp",
    f"{GTK} (dried shrimp is shrimp)",
)
_add(
    ["พริกแกงเลียง", "น้ำพริกเผา", "ซอสเอ็กซ์โอ", "xo sauce"],
    "กุ้งแห้ง",
    f"{GTK} (nam prik pao, kaeng liang paste and XO sauce contain dried shrimp)",
)

# ---- shellfish ----------------------------------------------------------
# Cephalopods and molluscs are shellfish here; the Thai word for squid
# contains the fish word but squid is NOT fish (fish boundary excludes it).
_add(
    [
        "หมึก", "ปลาหมึก", "squid", "octopus", "cuttlefish", "calamari",
        "scallop", "mussel", "cockle", "abalone", "เป๋าฮื้อ",
        "crayfish", "crawfish", "ล็อบสเตอร์",
    ],
    "allergen:shellfish",
    f"{GTK} (molluscs, cephalopods and non-shrimp crustaceans are shellfish)",
)
_add(
    ["ซอสเอ็กซ์โอ", "xo sauce"],
    "scallop",
    f"{GTK} (XO sauce is made with dried scallop and dried shrimp)",
)
# Oyster sauce: redundant with the floor term "หอย" but recorded because the
# composition (oyster extract) is real.
_add(["น้ำมันหอย", "ซอสหอยนางรม", "oyster sauce"], "oyster", f"{GTK} (oyster sauce is made from oyster extract)")

# ---- fish ---------------------------------------------------------------
_add(
    [
        "ทูน่า", "แซลมอน", "ซาร์ดีน", "แอนโชวี่", "หูฉลาม",
        "tuna", "salmon", "sardine", "sardines", "anchovy", "anchovies", "bonito",
    ],
    "allergen:fish",
    f"{GTK} (finned fish and fish products)",
)
_add(
    ["ตำลาว", "แจ่วบอง"],
    "ปลาร้า",
    f"{GTK} (Isan/Lao-style ตำลาว and แจ่วบอง are made with fermented fish, ปลาร้า)",
)
_add(["ปลาร้า"], "allergen:fish", f"{GTK} (pla ra is fermented fish)")
_add(
    ["น้ำจิ้มซีฟู้ด", "ซอสผัดไทย"],
    "น้ำปลา",
    f"{GTK} (Thai seafood dipping sauce and pad thai sauce are seasoned with fish sauce)",
)
_add(["น้ำปลา"], "allergen:fish", f"{GTK} (fish sauce is fermented fish)")
_add(
    ["น้ำยาขนมจีน"],
    "ปลา",
    f"{GTK} (traditional ขนมจีนน้ำยา sauce is fish-based)",
)
_add(
    ["worcestershire", "น้ำสลัดซีซาร์", "caesar dressing"],
    "anchovy",
    f"{GTK} (Worcestershire sauce and classic Caesar dressing contain anchovy)",
)
_add(
    ["ดาชิ", "dashi"],
    "bonito",
    f"{GTK} (dashi stock is made from dried bonito; kombu-only vegetarian dashi is not modeled)",
)

# ---- egg ----------------------------------------------------------------
_add(
    ["มายองเนส", "ไมโยเนส", "mayonnaise", "meringue", "เมอแรงก์"],
    "allergen:egg",
    f"{GTK} (mayonnaise and meringue are made from egg)",
)
_add(
    ["ซอสทาร์ทาร์", "tartar sauce", "น้ำสลัดซีซาร์", "caesar dressing"],
    "มายองเนส",
    f"{GTK} (tartar sauce is mayonnaise-based; classic Caesar dressing uses egg yolk/mayonnaise)",
)
_add(
    ["สังขยา", "ฝอยทอง", "ทองหยอด", "ทองหยิบ", "ขนมหม้อแกง", "ทิรามิสุ", "tiramisu", "hollandaise", "ฮอลแลนเดส"],
    "ไข่",
    f"{GTK} (traditional Thai egg-yolk sweets and custards; tiramisu and hollandaise use egg yolk)",
)

# ---- milk ---------------------------------------------------------------
_add(
    ["โยเกิร์ต", "yogurt", "yoghurt", "whey", "casein", "เคซีน", "เวย์โปรตีน"],
    "allergen:milk",
    f"{GTK} (yogurt is fermented milk; whey and casein are milk proteins)",
)
_add(
    ["มอสซาเรลลา", "มอสซาเรลล่า", "พาร์เมซาน", "ปาร์เมซาน", "เชดดาร์", "ริคอตต้า", "มาสคาร์โปเน"],
    "ชีส",
    f"{GTK} (named cheeses)",
)
_add(
    ["mozzarella", "parmesan", "parmigiano", "cheddar", "ricotta", "mascarpone"],
    "cheese",
    f"{GTK} (named cheeses)",
)
_add(["ทิรามิสุ", "tiramisu"], "มาสคาร์โปเน", f"{GTK} (tiramisu is layered with mascarpone)")
_add(["เพสโต้", "pesto"], "parmesan", f"{GTK} (classic basil pesto contains parmesan/pecorino)")
_add(["น้ำสลัดซีซาร์", "caesar dressing"], "parmesan", f"{GTK} (classic Caesar dressing contains parmesan)")
_add(["ghee"], "butter", f"{GTK} (ghee is clarified butter)")
_add(["hollandaise", "ฮอลแลนเดส"], "เนย", f"{GTK} (hollandaise is an emulsion of egg yolk and butter)")
_add(
    ["เบชาเมล", "เบซาเมล", "bechamel"],
    "นม",
    f"{GTK} (béchamel is a roux thickened with milk)",
)

# ---- gluten -------------------------------------------------------------
_add(
    [
        "ข้าวสาลี", "ข้าวบาร์เลย์", "ข้าวไรย์", "barley", "rye", "semolina", "เซโมลินา",
        "couscous", "คูสคูส", "bulgur", "seitan", "เซตัน",
    ],
    "allergen:gluten",
    f"{GTK} (wheat, barley, rye and their direct derivatives)",
)
_add(
    [
        "บะหมี่", "แผ่นเกี๊ยว", "ราเมน", "อุด้ง", "udon", "พาสต้า", "pasta",
        "สปาเก็ตตี้", "สปาเกตตี้", "spaghetti", "มักกะโรนี", "macaroni",
        "ขนมปัง", "เกล็ดขนมปัง", "breadcrumb", "แครกเกอร์", "cracker",
    ],
    "แป้งสาลี",
    f"{GTK} (wheat noodles, pasta, bread and crackers are wheat-flour products; gluten-free variants not modeled)",
)
_add(
    ["ซีอิ๊ว", "ซอสถั่วเหลือง", "ซอสปรุงรส", "เบชาเมล", "เบซาเมล", "bechamel"],
    "แป้งสาลี",
    f"{GTK} (conventional brewed soy sauce and seasoning sauce use wheat; béchamel is a wheat-flour roux; tamari/gluten-free soy sauce not modeled)",
)
_add(["soy sauce"], "wheat", f"{GTK} (conventional brewed soy sauce uses wheat; tamari not modeled)")
_add(["เบียร์"], "barley", f"{GTK} (beer is brewed from barley malt)")
_add(["malt extract"], "barley", f"{GTK} (malt extract is made from barley)")

# ---- soy ----------------------------------------------------------------
_add(
    ["เต้าเจี้ยว", "มิโซะ", "miso", "เทมเป้", "tempeh", "นัตโตะ", "natto", "เอดามาเมะ", "edamame", "ฮอยซิน", "hoisin", "ซอสปรุงรส"],
    "ถั่วเหลือง",
    f"{GTK} (fermented soybean pastes, tempeh, natto, edamame, hoisin and seasoning sauce are soybean products)",
)
_add(
    ["เทริยากิ", "เทอริยากิ", "teriyaki"],
    "ซีอิ๊ว",
    f"{GTK} (teriyaki sauce is soy sauce, mirin and sugar)",
)

# ---- peanut -------------------------------------------------------------
_add(
    ["ซอสสะเต๊ะ", "น้ำจิ้มสะเต๊ะ", "satay sauce", "ถั่วตัด"],
    "ถั่วลิสง",
    f"{GTK} (Thai satay sauce and ถั่วตัด are made from peanuts)",
)

# ---- nut (tree nuts) ----------------------------------------------------
# "chestnut" (English) is deliberately NOT a node: it is a substring of
# "water chestnut", which is excluded from the nut key. Thai เกาลัด only.
_add(
    ["พิสตาชิโอ", "pistachio", "พีแคน", "pecan", "วอลนัท", "เฮเซลนัท", "แมคคาเดเมีย", "มะคาเดเมีย", "macadamia", "เกาลัด"],
    "allergen:nut",
    f"{GTK} (tree nuts)",
)
_add(["เม็ดมะม่วง"], "มะม่วงหิมพานต์", f"{GTK} (เม็ดมะม่วง is the colloquial name for cashew nuts)")
_add(["มาร์ซิปัน", "marzipan"], "almond", f"{GTK} (marzipan is almond paste)")
_add(["นูเทลล่า", "นูเทลลา", "nutella"], "hazelnut", "general knowledge of Nutella's published ingredient list (hazelnuts); Open Food Facts listing not re-fetched here")
_add(["นูเทลล่า", "นูเทลลา", "nutella"], "นม", "general knowledge of Nutella's published ingredient list (skimmed milk powder); Open Food Facts listing not re-fetched here")


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------
def _node_type(name: str) -> str:
    return "allergen" if name.startswith(ALLERGEN_NODE_PREFIX) else "ingredient"


def seed_allergen_graph(db: Session) -> dict:
    """Idempotently create missing nodes and edges. Returns counts added."""
    wanted: list[str] = [allergen_node_name(key) for key in FLOOR_BLOCKS]
    seen_names = set(wanted)
    for source, target, _citation in EDGES:
        for name in (source, target):
            if name not in seen_names:
                seen_names.add(name)
                wanted.append(name)

    existing = {name: node_id for name, node_id in db.execute(select(IngredientNode.name, IngredientNode.id)).all()}
    nodes_added = 0
    for name in wanted:
        if name not in existing:
            node = IngredientNode(name=name, node_type=_node_type(name))
            db.add(node)
            nodes_added += 1
    db.flush()
    existing = {name: node_id for name, node_id in db.execute(select(IngredientNode.name, IngredientNode.id)).all()}

    existing_edges = set(db.execute(select(AllergenEdge.ingredient_id, AllergenEdge.implies_id)).all())
    edges_added = 0
    for source, target, _citation in EDGES:
        pair = (existing[source], existing[target])
        if pair in existing_edges:
            continue
        existing_edges.add(pair)
        db.add(AllergenEdge(ingredient_id=pair[0], implies_id=pair[1]))
        edges_added += 1

    db.commit()
    return {"nodes_added": nodes_added, "edges_added": edges_added}


if __name__ == "__main__":
    from database.db import SessionLocal

    if SessionLocal is None:
        raise SystemExit("No database configured (SessionLocal is None).")
    session = SessionLocal()
    try:
        print(seed_allergen_graph(session))
    finally:
        session.close()

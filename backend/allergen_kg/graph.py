"""Reverse-closure traversal over the allergen Knowledge Graph.

Walks backward from allergen:<key> along implies_id edges with a recursive
CTE. Portable across SQLite (tests) and Postgres: the visited path is a
'|id|id|' TEXT string (no ARRAY type), every string expression is CAST to
TEXT in both CTE terms (Postgres rejects varchar-vs-text disagreement between
the anchor and recursive terms), and integer literals are rendered inline so
Postgres never infers smallint for a bind parameter.
"""
from dataclasses import dataclass

from sqlalchemy import Integer, Text, cast, literal, literal_column, not_, select
from sqlalchemy.orm import Session, aliased

from database.models import AllergenEdge, IngredientNode

ALLERGEN_NODE_PREFIX = "allergen:"


def allergen_node_name(key: str) -> str:
    return f"{ALLERGEN_NODE_PREFIX}{key}"


@dataclass(frozen=True)
class ClosureEntry:
    name: str
    path: tuple[str, ...]


def _text(expr):
    return cast(expr, Text)


def get_allergen_closure(db: Session, allergen_key: str, max_depth: int = 6) -> list[ClosureEntry]:
    allergen_id = db.execute(
        select(IngredientNode.id).where(
            IngredientNode.name == allergen_node_name(allergen_key),
            IngredientNode.node_type == "allergen",
        )
    ).scalar_one_or_none()
    if allergen_id is None:
        return []

    sep = _text(literal("|"))
    anchor = select(
        AllergenEdge.ingredient_id.label("node_id"),
        literal_column("1", Integer).label("depth"),
        _text(_text(literal(f"|{allergen_id}|")) + _text(AllergenEdge.ingredient_id) + sep).label("path"),
    ).where(AllergenEdge.implies_id == allergen_id)
    walk = anchor.cte(name="allergen_walk", recursive=True)

    edge = aliased(AllergenEdge)
    step = select(
        edge.ingredient_id,
        walk.c.depth + literal_column("1", Integer),
        _text(walk.c.path + _text(edge.ingredient_id) + sep),
    ).where(
        edge.implies_id == walk.c.node_id,
        walk.c.depth < max_depth,
        not_(walk.c.path.like(_text(literal("%|")) + _text(edge.ingredient_id) + _text(literal("|%")))),
    )
    walk = walk.union_all(step)

    rows = db.execute(
        select(walk.c.node_id, walk.c.depth, walk.c.path).order_by(walk.c.depth, walk.c.path)
    ).all()

    shortest: dict[int, list[int]] = {}
    for node_id, _depth, path in rows:
        if node_id in shortest:
            continue
        ids = [int(part) for part in path.strip("|").split("|")]
        shortest[node_id] = ids[1:]  # drop the allergen id; order: nearest-to-allergen ... head

    if not shortest:
        return []

    all_ids = {i for ids in shortest.values() for i in ids}
    nodes = {
        node_id: (name, node_type)
        for node_id, name, node_type in db.execute(
            select(IngredientNode.id, IngredientNode.name, IngredientNode.node_type).where(IngredientNode.id.in_(all_ids))
        ).all()
    }

    entries = []
    for head_id, ids in shortest.items():
        name, node_type = nodes[head_id]
        if node_type != "ingredient":
            continue
        entries.append(ClosureEntry(name=name, path=tuple(nodes[i][0] for i in reversed(ids))))
    return sorted(entries, key=lambda e: e.name)

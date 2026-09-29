"""In-memory SQLite graph builder for tests and the evaluation scripts."""
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from allergen_kg.graph import ALLERGEN_NODE_PREFIX
from database.models import AllergenEdge, Base, IngredientNode


def make_memory_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[IngredientNode.__table__, AllergenEdge.__table__])
    return Session(engine)


def _node(db: Session, name: str) -> IngredientNode:
    existing = db.execute(select(IngredientNode).where(IngredientNode.name == name)).scalar_one_or_none()
    if existing is not None:
        return existing
    node_type = "allergen" if name.startswith(ALLERGEN_NODE_PREFIX) else "ingredient"
    node = IngredientNode(name=name, node_type=node_type)
    db.add(node)
    db.flush()
    return node


def add_edges(db: Session, edges: list[tuple[str, str]]) -> None:
    for source, target in edges:
        db.add(AllergenEdge(ingredient_id=_node(db, source).id, implies_id=_node(db, target).id))
    db.commit()

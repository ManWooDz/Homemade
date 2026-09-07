"""SQLAlchemy models for PostgreSQL migration.

Not wired into main.py yet — models only. See docs/postgres-migration-prep.md
for the migration sequence and spec.md for the schema decisions this file
implements.
"""

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # nullable: additive Google OAuth later without a schema change (spec.md:17)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserIngredient(Base):
    __tablename__ = "user_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, default="Other")
    # nullable: "presence" tracking, not quantity tracking — a new row is
    # inserted with quantity=None on purpose (see fridge_repository.py)
    quantity: Mapped[str | None] = mapped_column(String, nullable=True)
    image: Mapped[str | None] = mapped_column(String, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BaseRecipe(Base):
    """Mirrors backend/database/setup_db.py's mock-recipe shape."""

    __tablename__ = "base_recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String, nullable=True)
    ratings: Mapped[float | None] = mapped_column(Float, nullable=True)
    review: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    ingredients: Mapped[list] = mapped_column(JSONB, default=list)
    nutrition: Mapped[dict] = mapped_column(JSONB, default=dict)
    instructions: Mapped[list] = mapped_column(JSONB, default=list)


class IngredientNutrition(Base):
    """Nutrition Engine lookup table (spec.md contribution #1). Not the
    allergen graph — see IngredientNode for that."""

    __tablename__ = "ingredient_nutrition"

    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    unit_basis: Mapped[str] = mapped_column(String, default="100g")
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    # "INMU" or "USDA" fallback (spec.md:32) — lets the demo show which source answered
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecipeIngredientImage(Base):
    """Name -> local image path lookup for rendering base_recipes ingredient
    lists (backend/database/setup_ingredients.py's old table). Presentation
    data, not nutrition data — kept out of ingredient_nutrition on purpose,
    same reasoning as keeping allergen_edges out of it (see IngredientNode).
    """

    __tablename__ = "recipe_ingredient_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    image: Mapped[str] = mapped_column(String, nullable=False)


class IngredientNode(Base):
    """Graph node for the allergen Knowledge Graph (spec.md:33-36).

    Kept separate from ingredient_nutrition: allergen categories (e.g.
    "shellfish") and composite dishes (e.g. "น้ำพริกกะปิ") are valid nodes
    here but have no nutrition macros, so they don't belong in the
    nutrition-lookup table.
    """

    __tablename__ = "ingredient_nodes"
    __table_args__ = (
        CheckConstraint("node_type IN ('ingredient', 'allergen')", name="ck_ingredient_nodes_node_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    node_type: Mapped[str] = mapped_column(String, nullable=False)


class AllergenEdge(Base):
    """Edge in the allergen Knowledge Graph — traversed with a recursive
    CTE (spec.md:35), not a flat JSONB tag. Curated data must include
    genuine 2-hop+ chains (spec.md:36), e.g.
    น้ำพริกกะปิ -> กะปิ -> shrimp.
    """

    __tablename__ = "allergen_edges"
    __table_args__ = (
        UniqueConstraint("ingredient_id", "implies_id", name="uq_allergen_edges_pair"),
        CheckConstraint("ingredient_id <> implies_id", name="ck_allergen_edges_no_self_loop"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient_nodes.id"), nullable=False)
    implies_id: Mapped[int] = mapped_column(ForeignKey("ingredient_nodes.id"), nullable=False)


class GenerateHistory(Base):
    """Unified history for both base-menu selections and free-form
    generation (source distinguishes them) — avoids a polymorphic FK from
    favorites/ratings pointing at either base_recipes or a generated
    recipe."""

    __tablename__ = "generate_history"
    __table_args__ = (
        CheckConstraint("source IN ('base', 'generated')", name="ck_generate_history_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    base_recipe_id: Mapped[int | None] = mapped_column(ForeignKey("base_recipes.id"), nullable=True)
    recipe_name: Mapped[str] = mapped_column(String, nullable=False)
    # real Postgres arrays, not JSONB — spec.md:49-50 queries these with unnest()
    adjusted_ingredients: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    diet_tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    instructions: Mapped[list] = mapped_column(JSONB, default=list)
    nutrition: Mapped[dict] = mapped_column(JSONB, default=dict)
    # verified dimension (spec.md RAG section) — must pass output_dimensionality=768
    # to embed_content() or this column gets a dimension mismatch on insert
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "generate_history_id", name="uq_favorites_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    generate_history_id: Mapped[int] = mapped_column(ForeignKey("generate_history.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "generate_history_id", name="uq_ratings_pair"),
        CheckConstraint("stars BETWEEN 1 AND 5", name="ck_ratings_stars_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    generate_history_id: Mapped[int] = mapped_column(ForeignKey("generate_history.id"), nullable=False)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    """Rotating refresh-token store — see
    docs/superpowers/specs/2026-09-08-auth-phase1-cookie-jwt-design.md.
    token_hash is sha256(raw JWT) — the raw token itself is never stored.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

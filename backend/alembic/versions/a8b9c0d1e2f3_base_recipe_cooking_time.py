"""Add reviewed approximate total-time ranges for the existing base menus.

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
"""
import hashlib
import json
import logging

from alembic import op
import sqlalchemy as sa

revision = "a8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None

# Pin the procedures these estimates describe; matching a name alone is insufficient.
ESTIMATES = (
    ("Superfood Veggie", 25, 35, "a9a4dd8e43e78a54a8180c9120c3f408dc2ed6ed53f7deed2b26ddbac178d341"),
    ("Fresh Power Salad", 10, 15, "0c2069c04e7ed3c289bd62d520ce2ec2b85403c5aa0c6b3e8f973a8493097810"),
    ("Rainbow Healthy", 15, 20, "2b50449b9ca39b6b46ee28c59b395bd04916db6e7787871c97d40ff8d9a660f1"),
    ("Chashu Ramen", 15, 20, "88a0d3e7ff84d4cd04345d0e7327a660870ebbeb928b57c2db5461e319feff07"),
    ("Padthai with shrimps", 30, 45, "38f590359c221a98cadf368992b683318615428918f7bf91994e7f87e6d05d40"),
    ("Stir-Fried Basil with pork", 15, 25, "685e8ae66af9d8f0cb2c649d5b02200b99496e106f8d6ca55406406083584a6f"),
    ("Greek Salad", 10, 15, "07bab7b6ca3d8a8f7e1c019ff55634cf760a9b261575906ffd0434f6c48bdc17"),
    ("Grilled Steak", 20, 30, "eea054959a41661b9a2c3b176490994872a12232dc713a112dc84318f6a4a77b"),
    ("Tom Yum Kung", 25, 35, "1b86e6c291e7542b503ef5b82126472c78c8c08c0e7992d4f56652e741faf45d"),
)


def upgrade():
    op.add_column("base_recipes", sa.Column("total_time_min_minutes", sa.Integer(), nullable=True))
    op.add_column("base_recipes", sa.Column("total_time_max_minutes", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_base_recipes_total_time", "base_recipes",
        "(total_time_min_minutes IS NULL AND total_time_max_minutes IS NULL) OR "
        "(total_time_min_minutes IS NOT NULL AND total_time_max_minutes IS NOT NULL "
        "AND total_time_min_minutes > 0 AND total_time_max_minutes >= total_time_min_minutes)",
    )
    recipes = sa.table(
        "base_recipes", sa.column("id", sa.Integer()), sa.column("name", sa.String()),
        sa.column("ingredients", sa.JSON()), sa.column("instructions", sa.JSON()),
        sa.column("servings", sa.Integer()), sa.column("total_time_min_minutes", sa.Integer()),
        sa.column("total_time_max_minutes", sa.Integer()),
    )
    conn = op.get_bind()
    rows = conn.execute(sa.select(recipes)).mappings().all()
    matched = 0
    for name, minimum, maximum, expected_digest in ESTIMATES:
        for row in rows:
            if row["name"] != name:
                continue
            inputs = {key: row[key] for key in ("ingredients", "instructions", "servings")}
            digest = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if digest != expected_digest:
                logging.getLogger("alembic.runtime.migration").warning("Time estimate skipped: changed recipe %s", name)
                continue
            result = conn.execute(
                recipes.update().where(
                    recipes.c.id == row["id"], recipes.c.total_time_min_minutes.is_(None),
                    recipes.c.total_time_max_minutes.is_(None),
                ).values(total_time_min_minutes=minimum, total_time_max_minutes=maximum)
            )
            matched += result.rowcount
    logging.getLogger("alembic.runtime.migration").info("Time ranges filled for %s base-menu rows", matched)


def downgrade():
    raise RuntimeError("Cooking-time downgrade discards data; retain additive columns or use reviewed recovery")

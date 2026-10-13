import unittest
import hashlib
import importlib.util
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import Column, Integer, JSON, MetaData, String, Table, create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import (
    Base,
    BaseRecipe,
    IngredientNutrition,
    IngredientNutritionAlias,
    RecipeIngredientImage,
    User,
)
from database.seed_postgres import DEV_USER_EMAIL, MOCK_RECIPES, image_path, seed


class IngredientImagePathTests(unittest.TestCase):
    def test_prepared_ingredient_aliases_use_existing_assets(self):
        for name, filename in (
            ("pork belly (chashu)", "chashu.png"),
            ("soft-boiled egg", "egg.png"),
        ):
            with self.subTest(name=name):
                self.assertEqual(image_path(name), f"images/ingredients/{filename}")
                self.assertEqual(image_path(name.upper()), image_path(name))

    def test_every_catalog_ingredient_resolves_to_an_existing_file(self):
        backend_dir = Path(__file__).resolve().parents[1]
        for name in {name for recipe in MOCK_RECIPES for name in recipe["ingredients"]}:
            with self.subTest(name=name):
                self.assertTrue((backend_dir / image_path(name)).is_file(), image_path(name))


class MockRecipesHaveQuantitiesTests(unittest.TestCase):
    def test_every_recipe_has_the_approved_integer_time_range(self):
        expected = [(25, 35), (10, 15), (15, 20), (15, 20), (30, 45), (15, 25), (10, 15), (20, 30), (25, 35)]
        self.assertEqual(len(MOCK_RECIPES), len(expected))
        for recipe, (minimum, maximum) in zip(MOCK_RECIPES, expected, strict=True):
            self.assertEqual(type(recipe["total_time_min_minutes"]), int)
            self.assertEqual(type(recipe["total_time_max_minutes"]), int)
            self.assertEqual((recipe["total_time_min_minutes"], recipe["total_time_max_minutes"]), (minimum, maximum))

    def test_every_recipe_has_servings_and_matching_quantity_names(self):
        for recipe in MOCK_RECIPES:
            self.assertIsInstance(recipe.get("servings"), int)
            quantity_names = [q["name"] for q in recipe.get("ingredient_quantities", [])]
            self.assertEqual(quantity_names, recipe["ingredients"], f"{recipe['name']}: must be parallel to ingredients")


class CookingTimeBackfillTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "alembic/versions/a8b9c0d1e2f3_base_recipe_cooking_time.py"
        spec = importlib.util.spec_from_file_location("cooking_time_migration", path)
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)
        self.engine = create_engine("sqlite://")
        self.addCleanup(self.engine.dispose)
        self.table = Table("base_recipes", MetaData(), Column("id", Integer, primary_key=True),
                           Column("name", String), Column("ingredients", JSON), Column("instructions", JSON),
                           Column("servings", Integer), Column("nutrition", JSON),
                           Column("total_time_min_minutes", Integer), Column("total_time_max_minutes", Integer))
        self.table.metadata.create_all(self.engine)

    def run_backfill(self, conn):
        with patch.object(self.migration.op, "get_bind", return_value=conn), \
                patch.object(self.migration.op, "add_column") as add, \
                patch.object(self.migration.op, "create_check_constraint") as check:
            self.migration.upgrade()
        self.assertEqual([call.args[1].name for call in add.call_args_list],
                         ["total_time_min_minutes", "total_time_max_minutes"])
        self.assertEqual(check.call_args.args[:2], ("ck_base_recipes_total_time", "base_recipes"))

    def test_backfill_pins_current_procedures_and_changes_only_time(self):
        with self.engine.begin() as conn:
            for recipe in MOCK_RECIPES:
                conn.execute(self.table.insert().values(**{key: recipe[key] for key in
                    ("name", "ingredients", "instructions", "servings", "nutrition")}))
            before = [dict(row) for row in conn.execute(select(self.table)).mappings()]
            self.run_backfill(conn)
            after = [dict(row) for row in conn.execute(select(self.table)).mappings()]
            for old, new, (name, minimum, maximum, digest) in zip(before, after, self.migration.ESTIMATES, strict=True):
                inputs = {key: old[key] for key in ("ingredients", "instructions", "servings")}
                self.assertEqual(hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), digest)
                self.assertEqual(new, {**old, "total_time_min_minutes": minimum, "total_time_max_minutes": maximum})
                self.assertEqual(new["name"], name)
            self.run_backfill(conn)
            self.assertEqual([dict(row) for row in conn.execute(select(self.table)).mappings()], after)

    def test_changed_inputs_unknown_menus_and_existing_times_are_preserved(self):
        recipe = MOCK_RECIPES[0]
        base = {key: recipe[key] for key in ("name", "ingredients", "instructions", "servings", "nutrition")}
        cases = [{**base, "instructions": ["Different procedure"]}, {**base, "ingredients": ["different"]},
                 {**base, "servings": 2}, {**base, "name": "Unknown menu"},
                 {**base, "total_time_min_minutes": 40, "total_time_max_minutes": 50}]
        with self.engine.begin() as conn:
            for values in cases:
                conn.execute(self.table.insert().values(**values))
            before = [dict(row) for row in conn.execute(select(self.table)).mappings()]
            self.run_backfill(conn)
            self.assertEqual([dict(row) for row in conn.execute(select(self.table)).mappings()], before)


class SeedResilienceTests(unittest.TestCase):
    """seed() against in-memory SQLite (no live Postgres available)."""

    def setUp(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(
            engine,
            tables=[t.__table__ for t in (User, BaseRecipe, RecipeIngredientImage, IngredientNutrition, IngredientNutritionAlias)],
        )
        self.Session = sessionmaker(bind=engine)
        patcher = patch("database.seed_postgres.SessionLocal", self.Session)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _computed(self, name):
        return {"basis": "per_serving", "calories": float(len(name)), "protein_g": 1.0, "carbs_g": 1.0, "fat_g": 1.0}

    def test_seed_persists_times_and_only_fills_matching_empty_ranges(self):
        with patch("database.seed_postgres.compute_from_quantities", return_value=self._computed("x")), redirect_stdout(StringIO()):
            seed()
            with self.Session() as db:
                rows = db.query(BaseRecipe).order_by(BaseRecipe.id).all()
                self.assertEqual([(r.total_time_min_minutes, r.total_time_max_minutes) for r in rows],
                                 [(r["total_time_min_minutes"], r["total_time_max_minutes"]) for r in MOCK_RECIPES])
                rows[0].total_time_min_minutes = rows[0].total_time_max_minutes = None
                rows[1].total_time_min_minutes, rows[1].total_time_max_minutes = 40, 50
                rows[2].instructions = ["Changed procedure"]
                rows[2].total_time_min_minutes = rows[2].total_time_max_minutes = None
                db.commit()
            seed()
        with self.Session() as db:
            rows = db.query(BaseRecipe).order_by(BaseRecipe.id).all()
            self.assertEqual((rows[0].total_time_min_minutes, rows[0].total_time_max_minutes), (25, 35))
            self.assertEqual((rows[1].total_time_min_minutes, rows[1].total_time_max_minutes), (40, 50))
            self.assertIsNone(rows[2].total_time_min_minutes)
            self.assertEqual(rows[2].instructions, ["Changed procedure"])

    def test_one_failing_recipe_falls_back_to_hand_typed_nutrition_and_others_are_computed(self):
        failing_name = MOCK_RECIPES[0]["name"]
        names_by_quantities = {id(r["ingredient_quantities"]): r["name"] for r in MOCK_RECIPES}

        def fake_compute(db, quantities, servings):
            name = names_by_quantities[id(quantities)]
            if name == failing_name:
                raise ValueError("base-recipe ingredient(s) not found in ingredient_nutrition: ['kale']")
            return self._computed(name)

        out = StringIO()
        with patch("database.seed_postgres.compute_from_quantities", side_effect=fake_compute), redirect_stdout(out):
            seed()

        self.assertIn(f"could not compute nutrition for '{failing_name}'", out.getvalue())
        self.assertIn("falling back to the hand-typed nutrition dict", out.getvalue())

        with self.Session() as db:
            rows = {row.name: row for row in db.query(BaseRecipe).all()}
            self.assertEqual(len(rows), len(MOCK_RECIPES))
            self.assertEqual(rows[failing_name].nutrition, MOCK_RECIPES[0]["nutrition"])
            for recipe in MOCK_RECIPES[1:]:
                self.assertEqual(rows[recipe["name"]].nutrition, self._computed(recipe["name"]))
            self.assertIsNotNone(db.query(User).filter_by(email=DEV_USER_EMAIL).first())
            self.assertGreater(db.query(RecipeIngredientImage).count(), 0)

    def test_dev_user_survives_a_later_failure(self):
        with patch("database.seed_postgres.compute_from_quantities", return_value=self._computed("x")), \
                patch("database.seed_postgres.image_path", side_effect=RuntimeError("disk gone")), \
                redirect_stdout(StringIO()):
            with self.assertRaises(RuntimeError):
                seed()

        with self.Session() as db:
            self.assertIsNotNone(db.query(User).filter_by(email=DEV_USER_EMAIL).first())
            self.assertEqual(db.query(BaseRecipe).count(), 0)


if __name__ == "__main__":
    unittest.main()

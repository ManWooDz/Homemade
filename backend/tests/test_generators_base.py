import unittest

from generators.base import RecipeGenerator


class RecipeGeneratorInterfaceTests(unittest.TestCase):
    def test_cannot_instantiate_abstract_base_directly(self):
        with self.assertRaises(TypeError):
            RecipeGenerator()

    def test_subclass_must_implement_generate(self):
        class Incomplete(RecipeGenerator):
            pass

        with self.assertRaises(TypeError):
            Incomplete()

    def test_subclass_with_generate_can_be_instantiated_and_called(self):
        class Fake(RecipeGenerator):
            def generate(self, ingredients, user_prefs, base_recipe, feedback=None):
                return {"ingredients": ingredients, "feedback": feedback}

        instance = Fake()
        result = instance.generate(["egg"], {}, {}, feedback="fix nutrition")
        self.assertEqual(result, {"ingredients": ["egg"], "feedback": "fix nutrition"})

    def test_generate_defaults_feedback_to_none(self):
        class Fake(RecipeGenerator):
            def generate(self, ingredients, user_prefs, base_recipe, feedback=None):
                return feedback

        self.assertIsNone(Fake().generate([], {}, {}))


if __name__ == "__main__":
    unittest.main()

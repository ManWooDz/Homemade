from abc import ABC, abstractmethod


class RecipeGenerator(ABC):
    """Common interface for anything that turns (ingredients, prefs, a base
    recipe, optional prior-attempt feedback) into a recipe dict shaped like
    the existing call_agentic_llm() output. Implementations: GeminiGenerator,
    LocalLLMGenerator."""

    @abstractmethod
    def generate(self, ingredients: list, user_prefs: dict, base_recipe: dict, feedback: str | None = None) -> dict:
        raise NotImplementedError

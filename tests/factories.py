import factory
from factory.faker import Faker

from app.models import Ingredient, Recipe
from app.schemas import IngredientCreate, RecipeCreate


class IngredientFactory(factory.Factory):
    """Фабрика для создания ингредиентов"""

    class Meta:
        model = Ingredient

    name = Faker("word")


class RecipeFactory(factory.Factory):
    """Фабрика для создания рецептов"""

    class Meta:
        model = Recipe

    dish_name = Faker("sentence", nb_words=3)
    description = Faker("text", max_nb_chars=200)
    cooking_time = Faker("random_int", min=5, max=120)
    count_views = 0


class IngredientCreateFactory(factory.Factory):
    """Фабрика для создания данных ингредиента"""

    class Meta:
        model = IngredientCreate

    name = Faker("word")


class RecipeCreateFactory(factory.Factory):
    """Фабрика для создания данных для создания рецепта"""

    class Meta:
        model = RecipeCreate

    dish_name = Faker("sentence", nb_words=3)
    description = Faker("text", max_nb_chars=200)
    cooking_time = Faker("random_int", min=5, max=120)

    @factory.post_generation
    def ingredients(self, create, extracted, **kwargs):
        """Создает список ингредиентов после генерации основного объекта"""
        if not extracted:
            # Создаем ингредиенты по умолчанию
            self.ingredients = [
                IngredientCreate(name=Faker("word").evaluate(None, None, {"locale": None})),
                IngredientCreate(name=Faker("word").evaluate(None, None, {"locale": None})),
                IngredientCreate(name=Faker("word").evaluate(None, None, {"locale": None})),
            ]
        else:
            self.ingredients = extracted

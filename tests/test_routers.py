from typing import List

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Ingredient, Recipe
from .factories import RecipeCreateFactory


"""Тесты приложения"""


class TestGetRecipes:
    """Тесты для эндпоинта GET /recipes/"""

    async def test_get_recipes_empty(self, client: AsyncClient):
        """Тест получения пустого списка рецептов"""
        response = await client.get("/recipes/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_get_recipes_with_data(
            self, client: AsyncClient, sample_recipe: Recipe
    ):
        """Тест получения списка рецептов с данными"""
        response = await client.get("/recipes/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1

        recipe = data[0]
        assert recipe["id"] == sample_recipe.id
        assert recipe["dish_name"] == sample_recipe.dish_name
        assert recipe["cooking_time"] == sample_recipe.cooking_time
        assert recipe["count_views"] == 0

    async def test_get_recipes_ordered_by_views(
            self, client: AsyncClient, test_session: AsyncSession
    ):
        """Тест сортировки рецептов по просмотрам"""
        # Создаем рецепты с разным количеством просмотров
        recipes = [
            Recipe(dish_name="Recipe 1", cooking_time=10, count_views=5),
            Recipe(dish_name="Recipe 2", cooking_time=15, count_views=10),
            Recipe(dish_name="Recipe 3", cooking_time=20, count_views=3),
        ]

        for recipe in recipes:
            test_session.add(recipe)
        await test_session.commit()

        response = await client.get("/recipes/")
        data = response.json()

        # Проверяем сортировку по убыванию просмотров
        assert data[0]["count_views"] == 10  # Recipe 2
        assert data[1]["count_views"] == 5  # Recipe 1
        assert data[2]["count_views"] == 3  # Recipe 3


class TestGetRecipe:
    """Тесты для эндпоинта GET /recipes/{recipe_id}"""

    async def test_get_recipe_not_found(self, client: AsyncClient):
        """Тест получения несуществующего рецепта"""
        response = await client.get("/recipes/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    async def test_get_recipe_success(
            self, client: AsyncClient, sample_recipe: Recipe
    ):
        """Тест успешного получения рецепта"""
        response = await client.get(f"/recipes/{sample_recipe.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == sample_recipe.id
        assert data["dish_name"] == sample_recipe.dish_name
        assert data["description"] == sample_recipe.description
        assert data["cooking_time"] == sample_recipe.cooking_time
        assert data["count_views"] == 1  # Просмотры увеличились на 1

    async def test_get_recipe_increments_views(
            self, client: AsyncClient, sample_recipe: Recipe, test_session: AsyncSession
    ):
        """Тест увеличения счетчика просмотров"""
        initial_views = sample_recipe.count_views

        # Получаем рецепт
        await client.get(f"/recipes/{sample_recipe.id}")

        # Проверяем, что просмотры увеличились в базе
        await test_session.refresh(sample_recipe)
        assert sample_recipe.count_views == initial_views + 1

    async def test_get_recipe_with_ingredients(
            self, client: AsyncClient, test_session: AsyncSession, sample_ingredients: List[Ingredient]
    ):
        """Тест получения рецепта с ингредиентами"""
        # Создаем рецепт с ингредиентами
        recipe = Recipe(
            dish_name="Салат с ингредиентами",
            cooking_time=10,
            count_views=0
        )
        recipe.ingredients = sample_ingredients

        test_session.add(recipe)
        await test_session.commit()
        await test_session.refresh(recipe, attribute_names=["ingredients"])

        response = await client.get(f"/recipes/{recipe.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "ingredients" in data
        assert len(data["ingredients"]) == len(sample_ingredients)

        # Проверяем, что ингредиенты правильно сериализованы
        ingredient_names = {i["name"] for i in data["ingredients"]}
        expected_names = {i.name for i in sample_ingredients}
        assert ingredient_names == expected_names


class TestCreateRecipe:
    """Тесты для эндпоинта POST /recipes/"""

    async def test_create_recipe_minimal(self, client: AsyncClient):
        """Тест создания рецепта с минимальными данными"""
        recipe_data = {
            "dish_name": "Простой рецепт",
            "cooking_time": 20,
            "ingredients": [
                {"name": "Ингредиент 1"},
                {"name": "Ингредиент 2"},
            ]
        }

        response = await client.post("/recipes/", json=recipe_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["dish_name"] == recipe_data["dish_name"]
        assert data["cooking_time"] == recipe_data["cooking_time"]
        assert data["count_views"] == 0
        assert "id" in data
        assert len(data["ingredients"]) == 2

    async def test_create_recipe_with_description(self, client: AsyncClient):
        """Тест создания рецепта с описанием"""
        recipe_data = {
            "dish_name": "Сложный рецепт",
            "description": "Подробное описание приготовления",
            "cooking_time": 45,
            "ingredients": [
                {"name": "Ингредиент 1"},
                {"name": "Ингредиент 2"},
                {"name": "Ингредиент 3"},
            ]
        }

        response = await client.post("/recipes/", json=recipe_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["dish_name"] == recipe_data["dish_name"]
        assert data["description"] == recipe_data["description"]
        assert data["cooking_time"] == recipe_data["cooking_time"]
        assert len(data["ingredients"]) == 3

    async def test_create_recipe_with_existing_ingredients(
            self, client: AsyncClient, sample_ingredients: List[Ingredient]
    ):
        """Тест создания рецепта с существующими ингредиентами"""
        recipe_data = {
            "dish_name": "Рецепт с существующими ингредиентами",
            "cooking_time": 30,
            "ingredients": [
                {"name": sample_ingredients[0].name},
                {"name": sample_ingredients[1].name},
                {"name": "Новый ингредиент"},
            ]
        }

        response = await client.post("/recipes/", json=recipe_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Проверяем, что существующие ингредиенты использованы повторно
        ingredient_names = {i["name"] for i in data["ingredients"]}
        assert sample_ingredients[0].name in ingredient_names
        assert sample_ingredients[1].name in ingredient_names
        assert "Новый ингредиент" in ingredient_names

    async def test_create_recipe_without_ingredients(self, client: AsyncClient):
        """Тест создания рецепта без ингредиентов (должен вернуть ошибку)"""
        recipe_data = {
            "dish_name": "Рецепт без ингредиентов",
            "cooking_time": 15,
            "ingredients": []
        }

        response = await client.post("/recipes/", json=recipe_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_create_recipe_invalid_data(self, client: AsyncClient):
        """Тест создания рецепта с невалидными данными"""
        # Нет обязательного поля dish_name
        recipe_data = {
            "cooking_time": 15,
            "ingredients": [{"name": "Ингредиент"}]
        }

        response = await client.post("/recipes/", json=recipe_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_create_recipe_duplicate_name(self, client: AsyncClient):
        """Тест создания рецепта с дублирующимся именем (должно работать)"""
        # Создаем первый рецепт
        recipe_data_1 = {
            "dish_name": "Уникальный рецепт",
            "cooking_time": 20,
            "ingredients": [{"name": "Ингредиент"}]
        }

        response1 = await client.post("/recipes/", json=recipe_data_1)
        assert response1.status_code == status.HTTP_201_CREATED

        # Создаем второй рецепт с таким же именем
        recipe_data_2 = {
            "dish_name": "Уникальный рецепт",
            "cooking_time": 30,
            "ingredients": [{"name": "Другой ингредиент"}]
        }

        response2 = await client.post("/recipes/", json=recipe_data_2)
        assert response2.status_code == status.HTTP_201_CREATED
        assert response2.json()["dish_name"] == "Уникальный рецепт"


@pytest.mark.integration
class TestIntegration:
    """Интеграционные тесты для проверки полного цикла работы"""

    async def test_full_recipe_workflow(
            self, client: AsyncClient, test_session: AsyncSession
    ):
        """Тест полного цикла: создание, получение списка, получение деталей"""

        # 1. Создаем рецепт
        recipe_data = {
            "dish_name": "Интеграционный тест",
            "description": "Тестовый рецепт",
            "cooking_time": 25,
            "ingredients": [
                {"name": "Ингредиент A"},
                {"name": "Ингредиент B"},
            ]
        }

        create_response = await client.post("/recipes/", json=recipe_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        created_recipe = create_response.json()
        recipe_id = created_recipe["id"]

        # 2. Получаем список рецептов
        list_response = await client.get("/recipes/")
        assert list_response.status_code == status.HTTP_200_OK
        recipes = list_response.json()
        assert len(recipes) >= 1
        assert any(r["id"] == recipe_id for r in recipes)

        # 3. Получаем детали рецепта
        detail_response = await client.get(f"/recipes/{recipe_id}")
        assert detail_response.status_code == status.HTTP_200_OK
        recipe_detail = detail_response.json()

        assert recipe_detail["id"] == recipe_id
        assert recipe_detail["dish_name"] == recipe_data["dish_name"]
        assert recipe_detail["description"] == recipe_data["description"]
        assert recipe_detail["cooking_time"] == recipe_data["cooking_time"]
        assert len(recipe_detail["ingredients"]) == 2

        # 4. Проверяем, что просмотры увеличились
        assert recipe_detail["count_views"] == 1

        # 5. Проверяем данные в базе
        result = await test_session.execute(
            select(Recipe).filter(Recipe.id == recipe_id)
        )
        db_recipe = result.scalars().first()
        assert db_recipe is not None
        assert db_recipe.count_views == 1

import asyncio
from typing import AsyncGenerator, Generator, List

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_session
from app.models import Ingredient, Recipe
from app.routers import app as fastapi_app

# Тестовая база данных
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_recipes.db"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Создает event loop для сессии тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Создает тестовый движок базы данных"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Удаляем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Создает тестовую сессию базы данных"""
    async_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest_asyncio.fixture(scope="function")
async def test_app(test_session: AsyncSession) -> FastAPI:
    """Создает тестовое приложение с переопределенной зависимостью сессии"""

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    fastapi_app.dependency_overrides[get_session] = override_get_session
    return fastapi_app


@pytest_asyncio.fixture(scope="function")
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Создает тестовый клиент с использованием правильного транспорта"""
    # Используем ASGITransport для тестирования ASGI приложений
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Очищаем dependency overrides после теста
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def sample_ingredients(test_session: AsyncSession) -> List[Ingredient]:
    """Создает тестовые ингредиенты"""
    ingredients = [
        Ingredient(name="Огурец"),
        Ingredient(name="Помидор"),
        Ingredient(name="Соль"),
    ]

    for ingredient in ingredients:
        test_session.add(ingredient)

    await test_session.commit()

    # Обновляем объекты, чтобы получить ID
    for ingredient in ingredients:
        await test_session.refresh(ingredient)

    return ingredients


@pytest_asyncio.fixture(scope="function")
async def sample_recipe(test_session: AsyncSession, sample_ingredients: List[Ingredient]) -> Recipe:
    """Создает тестовый рецепт"""
    recipe = Recipe(
        dish_name="Тестовый салат",
        description="Описание тестового салата",
        cooking_time=15,
        count_views=0,
    )

    test_session.add(recipe)
    await test_session.commit()
    await test_session.refresh(recipe)

    # Вместо прямого присвоения через прокси, создаем связи через ассоциативную таблицу
    # Получаем доступ к recipe_ingredients напрямую
    from app.database import RecipeIngredient

    for ingredient in sample_ingredients:
        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity="по вкусу",  # или любое значение по умолчанию
        )
        test_session.add(recipe_ingredient)

    await test_session.commit()

    # Обновляем рецепт, чтобы загрузить ингредиенты
    await test_session.refresh(recipe, attribute_names=["ingredients"])

    return recipe

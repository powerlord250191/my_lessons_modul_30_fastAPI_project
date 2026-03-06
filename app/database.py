from typing import AsyncGenerator, List, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass



class RecipeIngredient(Base):
    """Ассоциативная таблица для связи многие-ко-многим с дополнительными данными"""

    __tablename__ = "recipe_ingredient"

    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id"), primary_key=True
    )
    quantity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Связи с родительскими таблицами
    recipe: Mapped["Recipe"] = relationship(back_populates="recipe_ingredients")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="recipe_ingredients")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )

    # Связь через ассоциативную таблицу
    recipe_ingredients: Mapped[List["RecipeIngredient"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan"
    )

    # Прокси для прямого доступа к рецептам
    recipes: AssociationProxy[List["Recipe"]] = association_proxy(
        "recipe_ingredients",
        "recipe",
        creator=lambda recipe_obj: RecipeIngredient(recipe=recipe_obj),
    )


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    dish_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cooking_time: Mapped[int] = mapped_column(nullable=False)  # время в минутах
    count_views: Mapped[int] = mapped_column(default=0)  # количество просмотров

    # Связь через ассоциативную таблицу
    recipe_ingredients: Mapped[List["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )

    # Прокси для прямого доступа к ингредиентам
    ingredients: AssociationProxy[List["Ingredient"]] = association_proxy(
        "recipe_ingredients",
        "ingredient",
        creator=lambda ingredient_obj: RecipeIngredient(ingredient=ingredient_obj),
    )


# Создаем движок и фабрику сессий
DATABASE_URL = "sqlite+aiosqlite:///./recipes.db"
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionFactory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор для получения сессии БД.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()


async def fill_db(eng):
    from sqlalchemy.future import select

    async with AsyncSessionFactory() as session:
        # Проверяем, есть ли уже данные
        res = await session.execute(select(Recipe))
        if res.first():
            return

        # Создаем ингредиенты
        ingredients_data = [
            Ingredient(name="Огурец"),
            Ingredient(name="Помидор"),
            Ingredient(name="Соль"),
            Ingredient(name="Пельмени"),
            Ingredient(name="Сливочное масло"),
            Ingredient(name="Овсяные хлопья"),
            Ingredient(name="Молоко"),
        ]

        # Создаем рецепты
        recipes_data = [
            Recipe(
                dish_name="Салат с огурцом и помидором",
                cooking_time=7,
                description="Огурец, помидор, лук помыть "
                "и порезать средними кусками."
                " Добавить майонез, соль, перемешать.",
                count_views=0,
            ),
            Recipe(
                dish_name="Жареные пельмени",
                cooking_time=15,
                description="Замороженные пельмени выложить на сковороду,"
                " смазанную сливочным маслом."
                " Жарить 15 минут с обеих сторон на среднем огне.",
                count_views=0,
            ),
            Recipe(
                dish_name="Каша овсяная",
                cooking_time=25,
                description="В кастрюлю положить овсянку с молоком в соотношении 1:3,"
                " варить 20 мин на слабом огне. Выключить огонь, "
                "дать постоять 5 минут под крышкой. Добавить кусок масла.",
                count_views=0,
            ),
        ]

        # Добавляем все объекты в сессию
        session.add_all(ingredients_data)

        await session.flush()  # Получаем ID

        # Рецепт 1: Салат
        salad = recipes_data[0]
        salad.recipe_ingredients = [
            RecipeIngredient(ingredient=ingredients_data[0], quantity="2 шт"),  # Огурец
            RecipeIngredient(
                ingredient=ingredients_data[1], quantity="3 шт"
            ),  # Помидор
            RecipeIngredient(
                ingredient=ingredients_data[2], quantity="щепотка"
            ),  # Соль
        ]

        # Рецепт 2: Пельмени
        pelmeni_recipe = recipes_data[1]
        pelmeni_recipe.recipe_ingredients = [
            RecipeIngredient(
                ingredient=ingredients_data[3], quantity="500г"
            ),  # Пельмени
            RecipeIngredient(ingredient=ingredients_data[4], quantity="50г"),  # Масло
        ]

        # Рецепт 3: Каша
        porridge = recipes_data[2]
        porridge.recipe_ingredients = [
            RecipeIngredient(ingredient=ingredients_data[5], quantity="100г"),  # Хлопья
            RecipeIngredient(
                ingredient=ingredients_data[6], quantity="300мл"
            ),  # Молоко
            RecipeIngredient(ingredient=ingredients_data[4], quantity="20г"),  # Масло
        ]

        session.add_all(recipes_data)
        await session.commit()


async def create_tables():
    """Создание всех таблиц в базе данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

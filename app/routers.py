from contextlib import asynccontextmanager

from typing import Sequence

from app.database import Base, engine, fill_db, get_session
from fastapi import Depends, FastAPI, HTTPException, status
from app.models import Ingredient, Recipe
from app.schemas import RecipeCreate, RecipeDetails, RecipeMain
from sqlalchemy.engine import Result, ScalarResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

app = FastAPI()
get_session_dependency = Depends(get_session)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan контекст для startup/shutdown событий"""
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await fill_db(engine)

    yield


@app.get(
    "/recipes/",
    response_model=list[RecipeMain],
    tags=["Recipes"],
    summary="Return list of recipes",
)
async def get_recipes(
        session: AsyncSession = get_session_dependency,
) -> Sequence[Recipe]:
    res: Result = await session.execute(
        select(Recipe).order_by(Recipe.count_views.desc(), Recipe.cooking_time)
    )
    recipes_scalars: ScalarResult[Recipe] = res.scalars()
    return recipes_scalars.all()


@app.get(
    "/recipes/{recipe_id}",
    response_model=RecipeDetails,
    tags=["Recipes"],
    summary="Return one recipe",
)
async def get_recipe(
        recipe_id: int, session: AsyncSession = get_session_dependency
) -> Recipe:
    execution = await session.execute(
        select(Recipe)
        .filter(Recipe.id == recipe_id)
        .options(selectinload(Recipe.ingredients))
    )
    recipe = execution.scalars().first()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id {recipe_id} not found",
        )

    recipe.count_views += 1
    await session.commit()

    return recipe


@app.post(
    "/recipes/",
    response_model=RecipeDetails,
    tags=["Recipes"],
    summary="Create new recipe",
    status_code=status.HTTP_201_CREATED,
)
async def create_recipe(
        recipe_data: RecipeCreate, session: AsyncSession = get_session_dependency
) -> Recipe:
    """
    Create a new recipe with ingredients.

    - **dish_name**: Name of the dish (required)
    - **description**: Description of the recipe
    - **cooking_time**: Cooking time in minutes (required)
    - **ingredients**: List of ingredients with names (required)
    """
    try:
        # Создаем новый рецепт
        new_recipe = Recipe(
            dish_name=recipe_data.dish_name,
            description=recipe_data.description,
            cooking_time=recipe_data.cooking_time,
            count_views=0,
        )

        # Обрабатываем ингредиенты
        ingredients_list = []
        for ingredient_data in recipe_data.ingredients:
            # Проверяем, существует ли ингредиент
            result = await session.execute(
                select(Ingredient).filter(Ingredient.name == ingredient_data.name)
            )
            existing_ingredient = result.scalars().first()

            if existing_ingredient:
                # Используем существующий ингредиент
                ingredients_list.append(existing_ingredient)
            else:
                # Создаем новый ингредиент
                new_ingredient = Ingredient(name=ingredient_data.name)
                session.add(new_ingredient)
                await session.flush()  # Получаем ID нового ингредиента
                ingredients_list.append(new_ingredient)

        # Добавляем ингредиенты к рецепту
        new_recipe.ingredients = ingredients_list

        # Сохраняем рецепт в базе данных
        session.add(new_recipe)
        await session.commit()

        # Обновляем объект, чтобы получить все связи
        await session.refresh(new_recipe, attribute_names=["ingredients"])

        return new_recipe

    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating recipe: {str(e)}",
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )

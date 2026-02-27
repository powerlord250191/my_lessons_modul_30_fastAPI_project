from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


# Схемы для ингредиентов
class IngredientBase(BaseModel):
    name: str


class IngredientResponse(IngredientBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class IngredientCreate(IngredientBase):
    pass


# Схемы для рецептов
class RecipeIngredientResponse(BaseModel):
    id: int
    name: str
    quantity: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RecipeBase(BaseModel):
    dish_name: str
    description: Optional[str] = None
    cooking_time: int


class RecipeMain(RecipeBase):
    id: int
    count_views: int = 0

    model_config = ConfigDict(from_attributes=True)


class RecipeDetails(RecipeMain):
    ingredients: List[IngredientResponse]

    model_config = ConfigDict(from_attributes=True)


class RecipeCreate(RecipeBase):
    ingredients: List[IngredientCreate] = Field(
        ...,
        min_items=1,
        description="List of ingredients"
    )

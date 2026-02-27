from sqlalchemy import Integer, String, ForeignKey, Table, Column
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column

Base = declarative_base()

# Ассоциативная таблица для связи многие-ко-многим
recipe_ingredient = Table(
    'recipe_ingredient',
    Base.metadata,
    Column('recipe_id', Integer, ForeignKey('recipes.id'), primary_key=True),
    Column('ingredient_id', Integer, ForeignKey('ingredients.id'), primary_key=True),
    Column('quantity', String(50), nullable=True)  # количество ингредиента
)


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Связь с рецептами
    recipes = relationship(
        "Recipe",
        secondary=recipe_ingredient,
        back_populates="ingredients"
    )


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dish_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(nullable=True)
    cooking_time: Mapped[int] = mapped_column(nullable=False)  # время в минутах
    count_views: Mapped[int] = mapped_column(default=0)  # количество просмотров

    # Связь с ингредиентами через ассоциативную таблицу
    ingredients = relationship(
        "Ingredient",
        secondary=recipe_ingredient,
        back_populates="recipes"
    )

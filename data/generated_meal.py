import sqlalchemy
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


class GeneratedMeal(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'generate_meal'

    """Модель для сгенерированных блюд в планировщике"""
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
    date = sqlalchemy.Column(sqlalchemy.Date, nullable=False)
    meal_type = sqlalchemy.Column(sqlalchemy.String(20), nullable=False)  # breakfast, lunch, dinner, snack
    food_name = sqlalchemy.Column(sqlalchemy.String(200), nullable=False)
    calories = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    protein = sqlalchemy.Column(sqlalchemy.Float, default=0)
    carbs = sqlalchemy.Column(sqlalchemy.Float, default=0)
    fat = sqlalchemy.Column(sqlalchemy.Float, default=0)
    is_eaten = sqlalchemy.Column(sqlalchemy.Boolean, default=False)  # отмечено ли как съеденное
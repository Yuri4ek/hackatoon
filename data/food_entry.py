import sqlalchemy
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


class FoodEntry(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'food_entry'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
    date = sqlalchemy.Column(sqlalchemy.Date, nullable=False)
    food_name = sqlalchemy.Column(sqlalchemy.String(200), nullable=False)
    calories = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    protein = sqlalchemy.Column(sqlalchemy.Float, default=0)
    carbs = sqlalchemy.Column(sqlalchemy.Float, default=0)
    fat = sqlalchemy.Column(sqlalchemy.Float, default=0)
    meal_type = sqlalchemy.Column(sqlalchemy.String(20), nullable=False)

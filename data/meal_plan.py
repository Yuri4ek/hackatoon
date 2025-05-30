from datetime import datetime

import sqlalchemy
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


class MealPlan(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'user_queries'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
    date = sqlalchemy.Column(sqlalchemy.Date, nullable=False)
    meal_type = sqlalchemy.Column(sqlalchemy.String(20), nullable=False)  # breakfast, lunch, dinner, snack
    food_name = sqlalchemy.Column(sqlalchemy.String(200), nullable=False)
    calories = sqlalchemy.Column(sqlalchemy.Float)
    protein = sqlalchemy.Column(sqlalchemy.Float)
    carbs = sqlalchemy.Column(sqlalchemy.Float)
    fat = sqlalchemy.Column(sqlalchemy.Float)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.utcnow)

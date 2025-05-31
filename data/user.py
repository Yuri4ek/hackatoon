import sqlalchemy
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    # telegram_id = sqlalchemy.Column(sqlalchemy.String(50), unique=True) в случае интеграции с тг-ботом
    name = sqlalchemy.Column(sqlalchemy.String(100))
    age = sqlalchemy.Column(sqlalchemy.Integer)
    gender = sqlalchemy.Column(sqlalchemy.String(10))  # 'male', 'female'
    weight = sqlalchemy.Column(sqlalchemy.Float)
    height = sqlalchemy.Column(sqlalchemy.Float)
    activity_level = sqlalchemy.Column(sqlalchemy.String(20))  # 'sedentary', 'light', 'moderate', 'active', 'very_active'
    goal = sqlalchemy.Column(sqlalchemy.String(20))  # 'weight_loss', 'muscle_gain', 'maintenance'
    dietary_restrictions = sqlalchemy.Column(sqlalchemy.String(200))  # JSON string with restrictions

    email = sqlalchemy.Column(sqlalchemy.String, index=True, unique=True, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)
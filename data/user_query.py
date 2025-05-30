import sqlalchemy
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


class User_Query(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'user_queries'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    query_text = sqlalchemy.Column(sqlalchemy.Text)
    response_text = sqlalchemy.Column(sqlalchemy.Text)

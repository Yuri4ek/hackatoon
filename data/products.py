from sqlalchemy import Column, Integer, String, Float
from data.db_session import SqlAlchemyBase

class Product(SqlAlchemyBase):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    proteins = Column(Float)
    fats = Column(Float)
    carbohydrates = Column(Float)
    calories = Column(Integer)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base de todas las entidades ORM del proyecto (equivalente a las @Entity de JPA)"""

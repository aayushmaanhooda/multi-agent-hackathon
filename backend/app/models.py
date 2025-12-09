"""
Database models for ROSTER AI - SQLAlchemy 2.0 style
"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, Float, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default='employee')
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


# class EmploymentType(Base):
#     __tablename__ = 'employment_types'
    
#     id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
#     name: Mapped[str] = mapped_column(String(50), nullable=False)  # FT, PT, CASUAL
#     min_hours: Mapped[float] = mapped_column(Float, nullable=False)
#     max_hours: Mapped[float] = mapped_column(Float, nullable=False)
    
#     employees: Mapped[list['Employee']] = relationship(back_populates='employment_type_obj', cascade='all, delete-orphan')


# class Station(Base):
#     __tablename__ = 'stations'
    
#     id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
#     name: Mapped[str] = mapped_column(String(100), nullable=False)  # kitchen, counter, delivery
#     description: Mapped[Optional[str]] = mapped_column(String(255))
    
#     employees: Mapped[list['Employee']] = relationship(back_populates='station_obj', cascade='all, delete-orphan')


# class Employee(Base):
#     __tablename__ = 'employees'
    
#     id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
#     user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
#     employment_type_id: Mapped[UUID] = mapped_column(ForeignKey('employment_types.id'), nullable=False)
#     station_id: Mapped[UUID] = mapped_column(ForeignKey('stations.id'), nullable=False)
#     availability: Mapped[Optional[dict]] = mapped_column(default={})  # 14-day availability as JSON
#     created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
#     # user: Mapped[User] = relationship(back_populates='employees')
#     employment_type_obj: Mapped[EmploymentType] = relationship(back_populates='employees')
#     station_obj: Mapped[Station] = relationship(back_populates='employees')
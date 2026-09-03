"""Base repository with common CRUD operations."""

import uuid
from typing import TypeVar, Generic, Sequence

from sqlalchemy import select, func, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelT = TypeVar("ModelT", bound=DeclarativeBase)


class BaseRepository(Generic[ModelT]):
    """Generic repository providing common CRUD for any SQLAlchemy model."""

    def __init__(self, model: type[ModelT], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelT | None:
        result = await self.db.execute(select(self.model).where(self.model.id == entity_id))
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelT]:
        result = await self.db.execute(
            select(self.model).order_by(asc(self.model.created_at)).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        result = await self.db.execute(select(func.count(self.model.id)))
        return result.scalar_one()

    async def create(self, **kwargs) -> ModelT:
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **kwargs) -> ModelT:
        for key, value in kwargs.items():
            if value is not None and hasattr(instance, key):
                setattr(instance, key, value)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.db.delete(instance)
        await self.db.flush()

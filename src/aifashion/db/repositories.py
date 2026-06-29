"""Реализации портов на SQLAlchemy. Каждый метод фильтрует по user_id (§10)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aifashion.core.models import (
    ItemStatus,
    PhotoRole,
    SilhouetteHints,
    UserProfile,
    WardrobeItem,
    WardrobeItemAttrs,
)
from aifashion.db.models import PhotoORM, User, WardrobeItemORM


def _to_profile(u: User) -> UserProfile:
    silhouette = (
        SilhouetteHints.model_validate_json(u.silhouette_json) if u.silhouette_json else None
    )
    return UserProfile(
        id=u.id,
        language=u.language,
        color_type=u.color_type,
        contrast=u.contrast,
        silhouette=silhouette,
        sex=u.sex,
        age=u.age,
        height_cm=u.height_cm,
        lifestyle=u.lifestyle,
        dress_code=u.dress_code,
        lat=u.lat,
        lon=u.lon,
    )


def _to_item(o: WardrobeItemORM) -> WardrobeItem:
    return WardrobeItem(
        id=o.id,
        user_id=o.user_id,
        attrs=WardrobeItemAttrs(
            category=o.category,
            color=o.color,
            material=o.material,
            seasonality=o.seasonality,
            style=o.style,
            brand=o.brand,
            price=o.price,
        ),
        status=ItemStatus(o.status),
        photo_key=o.photo_key,
        last_seen_at=o.last_seen_at,
    )


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_or_create(self, telegram_id: int, language: str | None = None) -> UserProfile:
        u = await self._s.get(User, telegram_id)
        if u is None:
            u = User(id=telegram_id, language=language)
            self._s.add(u)
            await self._s.flush()
        elif language and not u.language:
            u.language = language
        return _to_profile(u)

    async def save(self, profile: UserProfile) -> UserProfile:
        u = await self._s.get(User, profile.id)
        if u is None:
            u = User(id=profile.id)
            self._s.add(u)
        u.language = profile.language
        u.color_type = profile.color_type
        u.contrast = profile.contrast
        u.silhouette_json = profile.silhouette.model_dump_json() if profile.silhouette else None
        u.sex = profile.sex
        u.age = profile.age
        u.height_cm = profile.height_cm
        u.lifestyle = profile.lifestyle
        u.dress_code = profile.dress_code
        u.lat = profile.lat
        u.lon = profile.lon
        await self._s.flush()
        return _to_profile(u)

    async def set_location(self, user_id: int, lat: float, lon: float) -> None:
        u = await self._s.get(User, user_id)
        if u is not None:
            u.lat, u.lon = lat, lon
            await self._s.flush()

    async def delete_all(self, user_id: int) -> list[str]:
        keys = list(
            (await self._s.scalars(select(PhotoORM.blob_key).where(PhotoORM.user_id == user_id))).all()
        )
        keys += list(
            (
                await self._s.scalars(
                    select(WardrobeItemORM.photo_key).where(
                        WardrobeItemORM.user_id == user_id,
                        WardrobeItemORM.photo_key.is_not(None),
                    )
                )
            ).all()
        )
        await self._s.execute(delete(User).where(User.id == user_id))  # каскад снесёт остальное
        await self._s.flush()
        return [k for k in keys if k]


class SqlWardrobeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add_item(
        self,
        user_id: int,
        attrs: WardrobeItemAttrs,
        *,
        photo_key: str | None = None,
        embedding: list[float] | None = None,
        status: ItemStatus = ItemStatus.active,
    ) -> WardrobeItem:
        o = WardrobeItemORM(
            user_id=user_id,
            category=attrs.category,
            color=attrs.color,
            material=attrs.material,
            seasonality=attrs.seasonality,
            style=attrs.style,
            brand=attrs.brand,
            price=attrs.price,
            status=status.value,
            photo_key=photo_key,
            embedding=embedding,
        )
        self._s.add(o)
        await self._s.flush()
        return _to_item(o)

    async def list_items(self, user_id: int, *, only_active: bool = True) -> list[WardrobeItem]:
        stmt = select(WardrobeItemORM).where(WardrobeItemORM.user_id == user_id)
        if only_active:
            stmt = stmt.where(WardrobeItemORM.status == ItemStatus.active.value)
        rows = (await self._s.scalars(stmt)).all()
        return [_to_item(o) for o in rows]

    async def touch_seen(self, item_id: int) -> None:
        o = await self._s.get(WardrobeItemORM, item_id)
        if o is not None:
            o.last_seen_at = datetime.now(timezone.utc)
            await self._s.flush()

    async def set_status(self, item_id: int, status: ItemStatus) -> None:
        o = await self._s.get(WardrobeItemORM, item_id)
        if o is not None:
            o.status = status.value
            await self._s.flush()

    async def find_similar(
        self, user_id: int, embedding: list[float], *, limit: int = 5
    ) -> list[WardrobeItem]:
        stmt = (
            select(WardrobeItemORM)
            .where(
                WardrobeItemORM.user_id == user_id,
                WardrobeItemORM.embedding.is_not(None),
            )
            .order_by(WardrobeItemORM.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        rows = (await self._s.scalars(stmt)).all()
        return [_to_item(o) for o in rows]

    async def stale_items(
        self, user_id: int, *, days: int = 60, limit: int = 5
    ) -> list[WardrobeItem]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(WardrobeItemORM)
            .where(
                WardrobeItemORM.user_id == user_id,
                WardrobeItemORM.status == ItemStatus.active.value,
                (WardrobeItemORM.last_seen_at.is_(None))
                | (WardrobeItemORM.last_seen_at < cutoff),
            )
            .order_by(WardrobeItemORM.last_seen_at.asc().nulls_first())
            .limit(limit)
        )
        rows = (await self._s.scalars(stmt)).all()
        return [_to_item(o) for o in rows]


class SqlPhotoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, user_id: int, role: PhotoRole, blob_key: str) -> int:
        o = PhotoORM(user_id=user_id, role=role.value, blob_key=blob_key)
        self._s.add(o)
        await self._s.flush()
        return o.id

    async def selfie_count(self, user_id: int) -> int:
        return int(
            await self._s.scalar(
                select(func.count())
                .select_from(PhotoORM)
                .where(PhotoORM.user_id == user_id, PhotoORM.role == PhotoRole.selfie.value)
            )
            or 0
        )

    async def evictable_selfie_keys(self, user_id: int, *, keep: int = 5) -> list[str]:
        stmt = (
            select(PhotoORM.blob_key)
            .where(PhotoORM.user_id == user_id, PhotoORM.role == PhotoRole.selfie.value)
            .order_by(PhotoORM.created_at.desc())
            .offset(keep)
        )
        return list((await self._s.scalars(stmt)).all())

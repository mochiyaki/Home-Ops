"""Postgres layer: engine, session, and the ORM models.

The house lives here so the homeowner assistant has a server-side record that
does not depend on the browser. Calls, their transcripts and their extracted
fields live here too, so a restart no longer loses call history.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func, select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, Session, mapped_column, relationship,
    sessionmaker as sync_maker,
)

from app.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSONB, list[Any]: JSONB}


class House(Base):
    __tablename__ = "houses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True,
                                      default="default")
    address: Mapped[str] = mapped_column(String(512), default="")
    homeowner: Mapped[str] = mapped_column(String(256), default="")
    # Rooms, drawings and free-form details stay document-shaped: the frontend
    # owns their exact schema and we do not want a migration per UI tweak.
    rooms: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    drawings: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    details: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    contractors: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    maintenance: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    projects: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=utcnow, onupdate=utcnow)

    assets: Mapped[list["Asset"]] = relationship(
        back_populates="house", cascade="all, delete-orphan", lazy="selectin"
    )


class Asset(Base):
    """An appliance or fixture. First-class because Ops looks these up by name."""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    house_id: Mapped[str] = mapped_column(ForeignKey("houses.id", ondelete="CASCADE"),
                                          index=True)
    room_id: Mapped[str] = mapped_column(String(64), default="")
    category: Mapped[str] = mapped_column(String(64), default="appliance")
    brand: Mapped[str] = mapped_column(String(128), default="")
    model: Mapped[str] = mapped_column(String(128), default="")
    serial: Mapped[str] = mapped_column(String(128), default="")
    warranty_until: Mapped[str] = mapped_column(String(64), default="")
    purchased: Mapped[str] = mapped_column(String(64), default="")
    manual_summary: Mapped[str] = mapped_column(Text, default="")
    manual_url: Mapped[str] = mapped_column(String(1024), default="")
    image_url: Mapped[str] = mapped_column(String(1024), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=utcnow)

    house: Mapped[House] = relationship(back_populates="assets")


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(32), default="guava")
    provider_call_id: Mapped[str | None] = mapped_column(String(128), index=True,
                                                         nullable=True)
    state: Mapped[str] = mapped_column(String(32), default="dialing", index=True)
    shop_name: Mapped[str] = mapped_column(String(256), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    dialed: Mapped[str] = mapped_column(String(64), default="")
    brief: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Structured result straight off the Guava checklist, not regex-scraped.
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote: Mapped[str | None] = mapped_column(String(512), nullable=True)
    booked: Mapped[bool] = mapped_column(Boolean, default=False)
    mock: Mapped[bool] = mapped_column(Boolean, default=False)
    termination_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=utcnow, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                      nullable=True)

    turns: Mapped[list["Turn"]] = relationship(
        back_populates="call", cascade="all, delete-orphan",
        order_by="Turn.seq", lazy="selectin",
    )

    @property
    def duration_seconds(self) -> int | None:
        if not self.ended_at:
            return None
        return int((self.ended_at - self.created_at).total_seconds())


class Turn(Base):
    """One utterance. Written live as the call happens."""

    __tablename__ = "turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    call_id: Mapped[str] = mapped_column(ForeignKey("calls.id", ondelete="CASCADE"),
                                         index=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    speaker: Mapped[str] = mapped_column(String(16))  # "agent" | "shop"
    text: Mapped[str] = mapped_column(Text)
    interrupted: Mapped[bool] = mapped_column(Boolean, default=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    call: Mapped["Call"] = relationship(back_populates="turns")


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None
_sync_engine = None
_sync_sessionmaker = None


def sync_url() -> str:
    """Same database, blocking driver.

    Guava invokes its handlers on plain threads with no event loop, and an
    asyncpg pool is bound to the loop that created it. Rather than smuggle a
    loop into those threads, the agent side gets its own psycopg engine.
    """
    return get_settings().database_url.replace("+asyncpg", "+psycopg")


def engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_settings().database_url, pool_pre_ping=True, future=True
        )
    return _engine


def sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(engine(), expire_on_commit=False)
    return _sessionmaker


def sync_engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(sync_url(), pool_pre_ping=True, future=True)
    return _sync_engine


def sync_session() -> Session:
    global _sync_sessionmaker
    if _sync_sessionmaker is None:
        _sync_sessionmaker = sync_maker(sync_engine(), expire_on_commit=False)
    return _sync_sessionmaker()


async def init_db() -> None:
    async with engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def session() -> AsyncSession:
    """FastAPI dependency."""
    async with sessionmaker()() as s:
        yield s

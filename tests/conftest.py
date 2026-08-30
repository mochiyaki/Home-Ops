"""Test fixtures.

Two things matter here:

  * Tests run against a throwaway `homeops_test` database, never `homeops`.
  * Tests must NEVER place a real call. Every vendor key is blanked in the
    environment (env vars beat the .env file in pydantic-settings), and a
    session-scoped guard asserts it before anything runs.
"""

from __future__ import annotations

import os

TEST_URL = "postgresql+asyncpg://homeops:homeops@localhost:5434/homeops_test"

os.environ["DATABASE_URL"] = TEST_URL
os.environ["HOMEOPS_MOCK"] = "1"
# Blank every credential so the suite cannot reach a vendor, whatever is in .env.
for _var in (
    "GUAVA_API_KEY", "GUAVA_AGENT_NUMBER", "GUAVA_WEBRTC_CODE",
    "HOMEOPS_DEV_SHOP_PHONE", "EXA_API_KEY", "APIFY_TOKEN",
    "GEMINI_API_KEY", "OPENAI_API_KEY",
):
    os.environ[_var] = ""

# A flag, not a credential - blanking it to "" fails boolean parsing.
os.environ["HOMEOPS_ALLOW_REAL_CALLS"] = "0"

import asyncio  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _isolated():
    get_settings.cache_clear()
    s = get_settings()
    assert s.database_url == TEST_URL, f"refusing to test against {s.database_url}"
    assert not s.guava_api_key, "tests must not hold a live Guava key"
    assert not s.homeops_dev_shop_phone, "tests must not reach a real number"
    return s


@pytest.fixture(scope="session", autouse=True)
def _schema(_isolated):
    from app import db

    asyncio.run(db.init_db())
    # asyncpg pools bind to the loop that created them. Drop this one so the
    # TestClient's loop builds its own.
    asyncio.run(db.engine().dispose())
    db._engine = None
    db._sessionmaker = None
    yield
    db._engine = None
    db._sessionmaker = None
    asyncio.run(_drop())


async def _drop():
    from app import db

    async with db.engine().begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)


@pytest.fixture(scope="session")
def client(_schema):
    """One client, one event loop, for the whole session."""
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clean(_schema):
    """Every test starts with empty calls and no house."""
    from app.db import Call, House, sync_session

    with sync_session() as s:
        s.query(Call).delete()
        s.query(House).delete()
        s.commit()
    yield


@pytest.fixture
def brief():
    return {
        "address": "1428 Folsom St, SF",
        "problem": "dishwasher leaking under the kitchen sink",
        "trade": "plumber",
        "homeowner": "Jordan Chen",
        "budget": "$300",
        "availability": "weekday mornings",
    }

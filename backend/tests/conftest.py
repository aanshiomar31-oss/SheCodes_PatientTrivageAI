"""
tests/conftest.py
===================

Shared pytest fixtures. Tests run against an isolated in-memory SQLite
database (never the development `patient_triage.db` file), so the test
suite is hermetic and safe to run repeatedly.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture()
def test_client() -> Iterator[TestClient]:
    """
    Provide a `TestClient` wired to a fresh in-memory SQLite database.

    The `get_db` dependency is overridden for the duration of the test so
    no test ever touches the real on-disk development database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Iterator:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

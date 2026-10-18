from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.seed import seed_database  # noqa: E402
from src.indexes import create_indexes  # noqa: E402

TEST_DB = os.getenv("MONGO_TEST_DB", "student_accounting_test")


@pytest.fixture(scope="module")
def db():
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    database = client[TEST_DB]
    client.drop_database(TEST_DB)
    create_indexes(database)
    seed_database(database, drop=False)
    yield database
    client.drop_database(TEST_DB)
    client.close()
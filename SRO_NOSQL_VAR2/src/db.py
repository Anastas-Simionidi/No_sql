"""Подключение к MongoDB. Конфигурация — через переменные окружения."""
from __future__ import annotations

import os
from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    return MongoClient(uri, serverSelectionTimeoutMS=5000, tz_aware=False)


def get_db(name: str | None = None) -> Database:
    """Возвращает БД: явно указанную, из MONGO_DB или дефолтную."""
    return get_client()[name or os.getenv("MONGO_DB", "student_accounting")]
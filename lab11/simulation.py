import hashlib
import random
from collections import Counter

# Фиксированный seed для воспроизводимости результатов
random.seed(42)

N, Q, SHARDS = 12000, 30000, 3

# Генерация датасета для варианта 5 (Библиотека)
# reader_id: 1250 уникальных значений (> 1000 по требованиям)
# genre_id: низкокардинальный ключ (5 жанров)
# event_id: последовательный идентификатор выдачи
rows = [
    {
        "reader_id": i % 1250,
        "genre_id": i % 5,
        "event_id": i,
    }
    for i in range(N)
]


def stable_hash(value):
  digest = hashlib.sha256(str(value).encode()).digest()
  return int.from_bytes(digest[:8], "big")


# Стратегии распределения по шардам (на 3 шарда)
def low_card(row):
  # Низкокардинальный ключ по жанру (genre_id)
  return row["genre_id"] % SHARDS


def hashed_reader(row):
  # Хешированный высококардинальный ключ читателя (reader_id)
  return stable_hash(row["reader_id"]) % SHARDS


def range_event(row):
  # Диапазонное разбиение по event_id
  return min(row["event_id"] // (N // SHARDS), SHARDS - 1)


def describe(name, assign, requests):
  docs = Counter(assign(r) for r in rows)
  load = Counter(assign(r) for r in requests)
  d = [docs[i] for i in range(SHARDS)]
  q = [load[i] for i in range(SHARDS)]
  print(
      f"{name:22} docs={d} queries={q} "
      f"doc_max_mean={round(max(d)/(sum(d)/SHARDS), 2)} "
      f"query_max_mean={round(max(q)/(sum(q)/SHARDS), 2)}"
  )


# 1. Равномерный набор запросов (Uniform)
uniform = random.choices(rows, k=Q)

# 2. Горячий набор запросов (Hot): 60% запросов идут к одной конкретной категории/жанру (genre_id == 0)
hot_rows = [r for r in rows if r["genre_id"] == 0]
hot = [
    random.choice(hot_rows) if random.random() < 0.6 else random.choice(rows)
    for _ in range(Q)
]

# Запуск симуляции для всех комбинаций ключей и режимов нагрузки
print("--- РЕЗУЛЬТАТЫ СИМУЛЯЦИИ (ВАРИАНТ 5: БИБЛИОТЕКА) ---")
for name, fn in [
    ("genre_low_card", low_card),
    ("hashed_reader", hashed_reader),
    ("range_event", range_event),
]:
  describe(name + "/uniform", fn, uniform)
  describe(name + "/hot", fn, hot)
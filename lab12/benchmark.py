from concurrent.futures import ThreadPoolExecutor
import csv
import math
import os
from time import perf_counter
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)
coll = client.nosql_lab12.courses
QUERY = {"departmentId": 10, "semester": 5}

def one():
    start = perf_counter()
    try:
        list(coll.find(QUERY).limit(100))
        return ((perf_counter() - start) * 1000, True)
    except Exception:
        return ((perf_counter() - start) * 1000, False)

def percentile(v, p):
    v = sorted(v)
    if not v:
        return float("nan")
    idx = (len(v) - 1) * p / 100
    lo, hi = math.floor(idx), math.ceil(idx)
    return v[lo] + (v[hi] - v[lo]) * (idx - lo)

def run(workers=4, n=400):
    for _ in range(40):
        one()  # Прогрев (warm-up)
    t0 = perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda _: one(), range(n)))
    seconds = perf_counter() - t0
    lat = [ms for ms, ok in results if ok]
    success = len(lat)
    return {
        "workers": workers,
        "success": success,
        "errors": n - success,
        "rps": round(success / seconds, 2),
        "p50": round(percentile(lat, 50), 3),
        "p95": round(percentile(lat, 95), 3),
        "p99": round(percentile(lat, 99), 3),
        "duration_sec": round(seconds, 3),
    }

def main(mode_name):
    file_exists = os.path.isfile("results.csv")
    with open("results.csv", "a", newline="", encoding="utf-8") as f:
        fieldnames = ["mode", "workers", "repeat", "rps", "p50", "p95", "p99","success", "errors", "duration_sec"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for workers in (1, 4, 8):
            for repeat in range(1, 4):
                res = run(workers=workers, n=400)
                res["mode"] = mode_name
                res["repeat"] = repeat
                writer.writerow(res)
                print(f"[{mode_name}] workers={workers}, repeat={repeat} -> {res}")

if __name__ == "__main__":
    # Поменяйте на "with_index" перед вторым запуском
    main("with_index")

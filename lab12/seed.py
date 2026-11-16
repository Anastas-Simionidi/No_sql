import random
from pymongo import MongoClient

random.seed(42)
client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)
db = client.nosql_lab12
coll = db.courses
coll.drop()

rows = [
    {
        "departmentId": random.randint(1, 20),
        "semester": random.randint(1, 8),
        "title": f"Course {i}",
        "credits": random.randint(2, 6),
        "teacherId": random.randint(1, 150),
    }
    for i in range(5000)
]
coll.insert_many(rows)
print("Версия MongoDB:", client.server_info()["version"])
print("Документов в коллекции:", coll.count_documents({}))


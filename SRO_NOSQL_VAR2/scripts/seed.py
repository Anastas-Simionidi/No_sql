"""Детерминированное заполнение БД синтетическими данными.

Запуск:  python -m scripts.seed
Создаёт: 6 преподавателей, 8 дисциплин, 20 студентов, ~80 регистраций.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from bson import ObjectId
from pymongo.database import Database

from src.db import get_db
from src.indexes import create_indexes

SEMESTER = "2024-Spring"
NOW = datetime(2025, 2, 1, 9, 0, 0)

# ---------------------------------------------------------------- справочники

TEACHERS = [
    {"full_name": "Иванов Пётр Сергеевич", "department": "Кафедра ИС", "email": "p.ivanov@univ.local", "degree": "к.т.н."},
    {"full_name": "Смирнова Анна Викторовна", "department": "Кафедра ИС", "email": "a.smirnova@univ.local", "degree": "д.т.н."},
    {"full_name": "Кузнецов Дмитрий Олегович", "department": "Кафедра ПМ", "email": "d.kuznetsov@univ.local", "degree": "к.ф.-м.н."},
    {"full_name": "Попова Елена Андреевна", "department": "Кафедра ИС", "email": "e.popova@univ.local", "degree": "к.т.н."},
    {"full_name": "Соколов Максим Игоревич", "department": "Кафедра ИВТ", "email": "m.sokolov@univ.local", "degree": "к.т.н."},
    {"full_name": "Морозова Ольга Николаевна", "department": "Кафедра ПМ", "email": "o.morozova@univ.local", "degree": "д.ф.-м.н."},
]

COURSES = [
    {"code": "IS-101", "title": "Базы данных", "credits": 5, "department": "Кафедра ИС",
     "teacher_idxs": [0], "capacity": 30,
     "schedule": [{"weekday": "Mon", "time": "10:00-11:30", "room": "A-312"},
                  {"weekday": "Wed", "time": "12:00-13:30", "room": "A-312"}]},
    {"code": "IS-102", "title": "Операционные системы", "credits": 4, "department": "Кафедра ИС",
     "teacher_idxs": [3], "capacity": 30,
     "schedule": [{"weekday": "Tue", "time": "10:00-11:30", "room": "A-210"},
                  {"weekday": "Thu", "time": "10:00-11:30", "room": "A-210"}]},
    {"code": "IS-103", "title": "Алгоритмы и структуры данных", "credits": 5, "department": "Кафедра ПМ",
     "teacher_idxs": [2], "capacity": 25,
     "schedule": [{"weekday": "Mon", "time": "14:00-15:30", "room": "B-105"},
                  {"weekday": "Fri", "time": "14:00-15:30", "room": "B-105"}]},
    {"code": "IS-201", "title": "NoSQL-технологии", "credits": 4, "department": "Кафедра ИС",
     "teacher_idxs": [1], "capacity": 30,
     "schedule": [{"weekday": "Tue", "time": "12:00-13:30", "room": "B-101"},
                  {"weekday": "Thu", "time": "12:00-13:30", "room": "B-101"}]},
    {"code": "IS-202", "title": "Веб-разработка", "credits": 4, "department": "Кафедра ИВТ",
     "teacher_idxs": [4], "capacity": 28,
     "schedule": [{"weekday": "Wed", "time": "10:00-11:30", "room": "C-204"},
                  {"weekday": "Fri", "time": "10:00-11:30", "room": "C-204"}]},
    {"code": "IS-203", "title": "Сетевые технологии", "credits": 3, "department": "Кафедра ИВТ",
     "teacher_idxs": [4], "capacity": 30,
     "schedule": [{"weekday": "Mon", "time": "16:00-17:30", "room": "C-301"},
                  {"weekday": "Thu", "time": "16:00-17:30", "room": "C-301"}]},
    {"code": "IS-301", "title": "Машинное обучение", "credits": 5, "department": "Кафедра ПМ",
     "teacher_idxs": [5], "capacity": 20,
     "schedule": [{"weekday": "Tue", "time": "16:00-17:30", "room": "B-210"},
                  {"weekday": "Fri", "time": "16:00-17:30", "room": "B-210"}]},
    {"code": "IS-302", "title": "Проектирование информационных систем", "credits": 4,
     "department": "Кафедра ИС", "teacher_idxs": [1], "capacity": 30,
     "schedule": [{"weekday": "Wed", "time": "14:00-15:30", "room": "A-401"},
                  {"weekday": "Sat", "time": "10:00-11:30", "room": "A-401"}]},
]

LAST_NAMES = [
    "Алексеев", "Борисова", "Волков", "Григорьева", "Дмитриев",
    "Егорова", "Жуков", "Зайцева", "Ильин", "Кириллова",
    "Лебедев", "Макарова", "Никитин", "Орлова", "Павлов",
    "Романова", "Сидоров", "Тихонова", "Ушаков", "Фёдорова",
]
FIRST_NAMES_M = ["Артём", "Борис", "Виктор", "Глеб", "Даниил",
                 "Егор", "Иван", "Кирилл", "Лев", "Марк"]
FIRST_NAMES_F = ["Анна", "Белла", "Вера", "Галина", "Дарья",
                 "Елена", "Жанна", "Ирина", "Ксения", "Людмила"]


def grade_to_letter(grade: int) -> tuple[str, float]:
    if grade >= 90:
        return "A", 4.0
    if grade >= 85:
        return "B+", 3.5
    if grade >= 80:
        return "B", 3.0
    if grade >= 75:
        return "C+", 2.5
    if grade >= 70:
        return "C", 2.0
    if grade >= 65:
        return "D+", 1.5
    if grade >= 60:
        return "D", 1.0
    return "F", 0.0


# ---------------------------------------------------------------- построение

def build_dataset() -> dict[str, list[dict]]:
    rnd = random.Random(42)

    teacher_ids = [ObjectId() for _ in TEACHERS]
    course_ids = [ObjectId() for _ in COURSES]

    teachers = [{**t, "_id": tid, "created_at": NOW}
                for tid, t in zip(teacher_ids, TEACHERS)]

    courses = []
    for cid, c in zip(course_ids, COURSES):
        courses.append({
            "_id": cid,
            "code": c["code"],
            "title": c["title"],
            "credits": c["credits"],
            "department": c["department"],
            "semester": SEMESTER,
            "capacity": c["capacity"],
            "teacher_ids": [teacher_ids[i] for i in c["teacher_idxs"]],
            "schedule": c["schedule"],
            "created_at": NOW,
        })

    students = []
    for i in range(20):
        last = LAST_NAMES[i]
        is_male = i % 2 == 0
        first = (FIRST_NAMES_M if is_male else FIRST_NAMES_F)[i // 2]
        students.append({
            "_id": ObjectId(),
            "student_no": f"IS-{2022 + (i % 3)}-{i + 1:03d}",
            "full_name": f"{last} {first}",
            "email": f"student{i + 1:02d}@univ.local",
            "phone": f"+7-900-{100 + i:03d}-{10 + i % 60:02d}-{i % 100:02d}",
            "birth_date": datetime(2003 + i % 3, (i % 12) + 1, (i % 27) + 1),
            "program": "Информационные системы",
            "year": 2 if i < 10 else 3,
            "status": "active" if i % 9 else "academic_leave",
            "contacts": {
                "address": f"г. Москва, ул. Примерная, д. {i + 1}",
                "emergency_contact": {
                    "name": f"{last} {first[:1]}.",
                    "phone": f"+7-900-{200 + i:03d}-00-00",
                },
            },
            "created_at": NOW,
        })

    enrollments = []
    for idx, student in enumerate(students):
        n_courses = rnd.randint(3, 5)
        for ci in sorted(rnd.sample(range(len(courses)), n_courses)):
            course = courses[ci]
            graded = rnd.random() > 0.15
            grade = rnd.randint(45, 100) if graded else None
            letter, points = grade_to_letter(grade) if graded else (None, None)
            enrollments.append({
                "_id": ObjectId(),
                "student_id": student["_id"],
                "course_id": course["_id"],
                "semester": course["semester"],
                "status": "completed" if graded else "enrolled",
                "grade": grade,
                "letter": letter,
                "grade_points": points,
                "attendance_pct": round(rnd.uniform(55.0, 100.0), 1),
                "enrolled_at": datetime(2025, 2, 3, 9, 0, 0) + timedelta(days=ci),
                "graded_at": datetime(2025, 6, 15, 12, 0, 0) if graded else None,
                "student_snapshot": {
                    "student_no": student["student_no"],
                    "full_name": student["full_name"],
                },
                "course_snapshot": {
                    "code": course["code"],
                    "title": course["title"],
                    "credits": course["credits"],
                },
            })

    return {
        "teachers": teachers,
        "courses": courses,
        "students": students,
        "enrollments": enrollments,
    }


def seed_database(db: Database, drop: bool = True) -> dict[str, int]:
    """Заполняет БД и возвращает количество вставленных документов по коллекциям."""
    if drop:
        db.client.drop_database(db.name)

    data = build_dataset()
    counts: dict[str, int] = {}
    for name, docs in data.items():
        if docs:
            db[name].insert_many(docs)
        counts[name] = len(docs)
    return counts


def main() -> None:
    db = get_db()
    create_indexes(db)
    counts = seed_database(db, drop=True)
    total = sum(counts.values())
    print(f"База: {db.name}")
    for name, n in counts.items():
        print(f"  {name:<12} {n:>4}")
    print(f"  {'ВСЕГО':<12} {total:>4}  (требование: >= 30)")


if __name__ == "__main__":
    main()
"""10 демонстрационных запросов к БД (8 обязательных + 2 бонусных).

Каждая функция соответствует Access Pattern из docs/ADR.md.
"""
from __future__ import annotations

import re
from typing import Any

from pymongo.database import Database

# ---------------------------------------------------------------- простые

def get_student_profile(db: Database, student_no: str) -> dict[str, Any] | None:
    """AP-1. Профиль студента по номеру зачётки (unique index)."""
    return db.students.find_one({"student_no": student_no}, {"_id": 0})


def get_transcript(db: Database, student_no: str,
                   semester: str | None = None) -> dict[str, Any]:
    """AP-2. Транскрипт студента; один find по ix_enr_student_sem."""
    student = db.students.find_one(
        {"student_no": student_no},
        {"_id": 1, "student_no": 1, "full_name": 1, "program": 1, "year": 1},
    )
    if not student:
        return {}

    flt: dict[str, Any] = {"student_id": student["_id"]}
    if semester:
        flt["semester"] = semester

    rows = list(
        db.enrollments.find(flt, {"_id": 0, "student_id": 0, "course_id": 0})
        .sort([("semester", 1), ("course_snapshot.code", 1)])
    )
    return {"student": student, "semester": semester, "courses": rows}


def get_course_roster(db: Database, course_code: str,
                      semester: str | None = None) -> dict[str, Any]:
    """AP-3. Список группы по дисциплине (ix_enr_course_sem)."""
    course = db.courses.find_one(
        {"code": course_code},
        {"_id": 1, "code": 1, "title": 1, "credits": 1, "semester": 1, "teacher_ids": 1},
    )
    if not course:
        return {}

    flt: dict[str, Any] = {"course_id": course["_id"]}
    if semester:
        flt["semester"] = semester

    rows = list(
        db.enrollments.find(flt, {"_id": 0, "course_id": 0})
        .sort([("student_snapshot.full_name", 1)])
    )
    return {"course": course, "students": rows}


def find_courses(db: Database, department: str | None = None,
                 min_credits: int | None = None,
                 semester: str | None = None) -> list[dict]:
    """AP-4. Каталог дисциплин с фильтрами (ix_course_dept_sem)."""
    flt: dict[str, Any] = {}
    if department:
        flt["department"] = department
    if semester:
        flt["semester"] = semester
    if min_credits:
        flt["credits"] = {"$gte": min_credits}
    return list(db.courses.find(flt, {"_id": 0}).sort([("department", 1), ("code", 1)]))


def search_students(db: Database, name_prefix: str, limit: int = 10) -> list[dict]:
    """AP-5. Поиск по префиксу ФИО (anchored regex использует ix_student_name)."""
    pattern = "^" + re.escape(name_prefix)
    return list(
        db.students.find(
            {"full_name": {"$regex": pattern, "$options": "i"}},
            {"_id": 0, "student_no": 1, "full_name": 1, "program": 1, "year": 1},
        ).limit(limit)
    )


# ---------------------------------------------------------------- агрегации

def course_grade_stats(db: Database, course_code: str) -> dict[str, Any]:
    """AP-6 (нетривиальный). Статистика по дисциплине: $facet + $bucket + $round."""
    pipeline = [
        {"$match": {"course_snapshot.code": course_code}},
        {"$facet": {
            "summary": [
                {"$match": {"grade": {"$ne": None}}},
                {"$group": {
                    "_id": None,
                    "graded": {"$sum": 1},
                    "avg_grade": {"$avg": "$grade"},
                    "min_grade": {"$min": "$grade"},
                    "max_grade": {"$max": "$grade"},
                    "passed": {"$sum": {"$cond": [{"$gte": ["$grade", 60]}, 1, 0]}},
                }},
                {"$project": {
                    "_id": 0,
                    "graded": 1,
                    "min_grade": 1,
                    "max_grade": 1,
                    "avg_grade": {"$round": ["$avg_grade", 2]},
                    "pass_rate": {"$round": [
                        {"$multiply": [{"$divide": ["$passed", "$graded"]}, 100]}, 1
                    ]},
                }},
            ],
            "distribution": [
                {"$match": {"grade": {"$ne": None}}},
                {"$bucket": {
                    "groupBy": "$grade",
                    "boundaries": [0, 60, 70, 80, 90, 101],
                    "default": "other",
                    "output": {"count": {"$sum": 1}},
                }},
            ],
            "total_enrolled": [{"$count": "n"}],
        }},
    ]
    res = list(db.enrollments.aggregate(pipeline))
    if not res:
        return {}
    facet = res[0]
    summary = facet["summary"][0] if facet["summary"] else None
    total = facet["total_enrolled"][0]["n"] if facet["total_enrolled"] else 0
    return {
        "course_code": course_code,
        "total_enrolled": total,
        "summary": summary,
        "distribution": facet["distribution"],
    }


def students_gpa(db: Database, min_gpa: float = 0.0) -> list[dict]:
    """AP-7 (нетривиальный). GPA, взвешенный по кредитам, из snapshot-полей."""
    pipeline = [
        {"$match": {"grade": {"$ne": None}}},
        {"$group": {
            "_id": "$student_id",
            "student_no": {"$first": "$student_snapshot.student_no"},
            "full_name": {"$first": "$student_snapshot.full_name"},
            "courses": {"$sum": 1},
            "total_credits": {"$sum": "$course_snapshot.credits"},
            "weighted_points": {"$sum": {"$multiply": ["$grade_points", "$course_snapshot.credits"]}},
        }},
        {"$addFields": {
            "gpa": {"$round": [{"$divide": ["$weighted_points", "$total_credits"]}, 2]}
        }},
        {"$match": {"gpa": {"$gte": min_gpa}}},
        {"$sort": {"gpa": -1, "student_no": 1}},
        {"$project": {
            "_id": 0, "student_no": 1, "full_name": 1,
            "gpa": 1, "courses": 1, "total_credits": 1,
        }},
    ]
    return list(db.enrollments.aggregate(pipeline))


def top_courses_by_enrollment(db: Database, n: int = 5) -> list[dict]:
    """AP-8. Топ-N дисциплин по числу регистраций."""
    pipeline = [
        {"$group": {
            "_id": "$course_snapshot.code",
            "title": {"$first": "$course_snapshot.title"},
            "enrolled": {"$sum": 1},
            "graded": {"$sum": {"$cond": [{"$ne": ["$grade", None]}, 1, 0]}},
        }},
        {"$addFields": {
            "graded_pct": {"$round": [
                {"$multiply": [{"$divide": ["$graded", "$enrolled"]}, 100]}, 1
            ]}
        }},
        {"$sort": {"enrolled": -1, "_id": 1}},
        {"$limit": n},
        {"$project": {"_id": 0, "code": "$_id", "title": 1,
                      "enrolled": 1, "graded": 1, "graded_pct": 1}},
    ]
    return list(db.enrollments.aggregate(pipeline))


def students_with_failing_grades(db: Database) -> list[dict]:
    """AP-9. Задолженности (grade < 60) с подтягиванием актуального ФИО ($lookup)."""
    pipeline = [
        {"$match": {"grade": {"$lt": 60}}},
        {"$lookup": {
            "from": "students",
            "localField": "student_id",
            "foreignField": "_id",
            "as": "student",
        }},
        {"$unwind": "$student"},
        {"$project": {
            "_id": 0,
            "student_no": "$student.student_no",
            "full_name": "$student.full_name",
            "course_code": "$course_snapshot.code",
            "course_title": "$course_snapshot.title",
            "semester": 1,
            "grade": 1,
        }},
        {"$sort": {"grade": 1, "full_name": 1}},
    ]
    return list(db.enrollments.aggregate(pipeline))


def teacher_workload(db: Database) -> list[dict]:
    """AP-10. Нагрузка преподавателей ($unwind + $group + $lookup)."""
    pipeline = [
        {"$unwind": "$teacher_ids"},
        {"$group": {
            "_id": "$teacher_ids",
            "courses": {"$push": {"code": "$code", "title": "$title", "credits": "$credits"}},
            "total_credits": {"$sum": "$credits"},
        }},
        {"$lookup": {
            "from": "teachers",
            "localField": "_id",
            "foreignField": "_id",
            "as": "teacher",
        }},
        {"$unwind": "$teacher"},
        {"$project": {
            "_id": 0,
            "teacher": "$teacher.full_name",
            "department": "$teacher.department",
            "course_count": {"$size": "$courses"},
            "total_credits": 1,
            "courses": 1,
        }},
        {"$sort": {"total_credits": -1, "teacher": 1}},
    ]
    return list(db.courses.aggregate(pipeline))
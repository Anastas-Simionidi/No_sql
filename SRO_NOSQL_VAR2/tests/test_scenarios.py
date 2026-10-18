"""Тестовые сценарии мини-проекта «Учёт студентов и дисциплин»."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pymongo.errors import DuplicateKeyError

from src import queries


# ---------------------------------------------------------------- сценарий 1
def test_seed_volume_and_uniqueness(db):
    """Сценарий 1: объём данных >= 30 документов и работа уникальных индексов."""
    total = sum(db[c].count_documents({}) for c in
                ("students", "courses", "teachers", "enrollments"))
    assert total >= 30
    assert db.students.count_documents({}) == 20
    assert db.courses.count_documents({}) == 8
    assert db.enrollments.count_documents({}) >= 60

    with pytest.raises(DuplicateKeyError):
        db.students.insert_one({
            "student_no": "IS-2022-001",  # уже существует
            "full_name": "Дубликат Дубликатович",
        })


# ---------------------------------------------------------------- сценарий 2
def test_crud_lifecycle(db):
    """Сценарий 2: create → read → update → enroll → grade → delete."""
    student_no = "IS-2099-999"
    sid = db.students.insert_one({
        "student_no": student_no,
        "full_name": "Тестов Тест Тестович",
        "email": "test.student@univ.local",
        "phone": "+7-000-000-00-00",
        "birth_date": datetime(2004, 5, 17),
        "program": "Информационные системы",
        "year": 1,
        "status": "active",
        "contacts": {"address": "г. Москва, ул. Тестовая, д. 1",
                     "emergency_contact": {"name": "Тестов Т.", "phone": "+7-000-000-00-01"}},
        "created_at": datetime.utcnow(),
    }).inserted_id

    # READ
    profile = queries.get_student_profile(db, student_no)
    assert profile is not None and profile["year"] == 1

    # UPDATE
    db.students.update_one({"_id": sid}, {"$set": {"year": 2, "status": "academic_leave"}})
    assert queries.get_student_profile(db, student_no)["status"] == "academic_leave"

    # ENROLL
    course = db.courses.find_one({"code": "IS-201"})
    eid = db.enrollments.insert_one({
        "student_id": sid,
        "course_id": course["_id"],
        "semester": course["semester"],
        "status": "enrolled",
        "grade": None, "letter": None, "grade_points": None,
        "attendance_pct": 100.0,
        "enrolled_at": datetime.utcnow(),
        "graded_at": None,
        "student_snapshot": {"student_no": student_no, "full_name": "Тестов Тест Тестович"},
        "course_snapshot": {"code": course["code"], "title": course["title"],
                            "credits": course["credits"]},
    }).inserted_id

    transcript = queries.get_transcript(db, student_no)
    assert len(transcript["courses"]) == 1
    assert transcript["courses"][0]["status"] == "enrolled"

    # GRADE
    db.enrollments.update_one(
        {"_id": eid},
        {"$set": {"status": "completed", "grade": 92, "letter": "A",
                  "grade_points": 4.0, "graded_at": datetime.utcnow()}},
    )
    gpa = {r["student_no"]: r["gpa"] for r in queries.students_gpa(db)}
    assert gpa[student_no] == 4.0

    # DELETE
    db.enrollments.delete_one({"_id": eid})
    db.students.delete_one({"_id": sid})
    assert queries.get_student_profile(db, student_no) is None
    assert student_no not in {r["student_no"] for r in queries.students_gpa(db)}


# ---------------------------------------------------------------- сценарий 3
def test_gpa_matches_manual_calculation(db):
    """Сценарий 3: агрегация GPA совпадает с ручным расчётом по документам."""
    aggregated = {r["student_no"]: r for r in queries.students_gpa(db)}
    assert aggregated, "агрегация GPA вернула пустой результат"

    for student in db.students.find({}, {"student_no": 1}):
        no = student["student_no"]
        rows = list(db.enrollments.find(
            {"student_id": student["_id"], "grade": {"$ne": None}},
            {"grade_points": 1, "course_snapshot.credits": 1},
        ))
        if not rows:
            assert no not in aggregated
            continue

        credits = sum(r["course_snapshot"]["credits"] for r in rows)
        points = sum(r["grade_points"] * r["course_snapshot"]["credits"] for r in rows)
        expected = round(points / credits, 2)
        assert aggregated[no]["gpa"] == expected, f"GPA mismatch у {no}"


# ---------------------------------------------------------------- сценарий 4
def test_snapshot_isolation_and_index_usage(db):
    """Сценарий 4: snapshot не «плывёт» + индекс реально используется."""
    original = db.courses.find_one({"code": "IS-101"}, {"title": 1})["title"]

    db.courses.update_one({"code": "IS-101"}, {"$set": {"title": "Базы данных (v2)"}})
    transcript = queries.get_transcript(db, "IS-2022-001")
    snap_titles = {c["course_snapshot"]["title"] for c in transcript["courses"]}
    assert "Базы данных (v2)" not in snap_titles      # историчность сохранена
    assert original in snap_titles

    db.courses.update_one({"code": "IS-101"}, {"$set": {"title": original}})

    import json
    plan = db.students.find({"student_no": "IS-2022-001"}).explain()
    plan_str = json.dumps(plan, default=str)
    assert "IXSCAN" in plan_str, "запрос по student_no должен идти по индексу"
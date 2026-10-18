"""Создание индексов, покрывающих Access Patterns из docs/ADR.md."""
from __future__ import annotations

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database


def create_indexes(db: Database) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {}

    created["students"] = [
        db.students.create_index([("student_no", ASCENDING)], unique=True, name="uq_student_no"),
        db.students.create_index([("full_name", ASCENDING)], name="ix_student_name"),
        db.students.create_index([("program", ASCENDING), ("year", ASCENDING)], name="ix_program_year"),
        db.students.create_index([("status", ASCENDING)], name="ix_student_status"),
    ]

    created["courses"] = [
        db.courses.create_index([("code", ASCENDING)], unique=True, name="uq_course_code"),
        db.courses.create_index([("department", ASCENDING), ("semester", ASCENDING)], name="ix_course_dept_sem"),
        db.courses.create_index([("teacher_ids", ASCENDING)], name="ix_course_teachers"),
    ]

    created["enrollments"] = [
        db.enrollments.create_index(
            [("student_id", ASCENDING), ("semester", DESCENDING)], name="ix_enr_student_sem"
        ),
        db.enrollments.create_index(
            [("course_id", ASCENDING), ("semester", ASCENDING)], name="ix_enr_course_sem"
        ),
        db.enrollments.create_index(
            [("student_id", ASCENDING), ("course_id", ASCENDING), ("semester", ASCENDING)],
            unique=True,
            name="uq_enr_student_course_sem",
        ),
        db.enrollments.create_index([("grade", ASCENDING)], name="ix_enr_grade"),
    ]

    created["teachers"] = [
        db.teachers.create_index([("email", ASCENDING)], unique=True, name="uq_teacher_email"),
        db.teachers.create_index([("department", ASCENDING)], name="ix_teacher_dept"),
    ]

    return created
"""Демонстрация 10 запросов + сравнение планов с индексом и без.

Запуск:  python -m src.demo
"""
from __future__ import annotations

import json

from src import queries
from src.db import get_db


def dump(title: str, payload) -> None:
    print("=" * 78)
    print(title)
    print("-" * 78)
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def plan_contains(plan: dict, stage: str) -> bool:
    if not isinstance(plan, dict):
        return False
    if plan.get("stage") == stage:
        return True
    return any(plan_contains(v, stage) for v in plan.values())


def main() -> None:
    db = get_db()

    dump("AP-1. Профиль студента IS-2022-001",
         queries.get_student_profile(db, "IS-2022-001"))

    dump("AP-2. Транскрипт студента IS-2022-001",
         queries.get_transcript(db, "IS-2022-001"))

    dump("AP-3. Список группы по дисциплине IS-201",
         queries.get_course_roster(db, "IS-201"))

    dump("AP-4. Дисциплины кафедры ИС, >= 4 кредитов",
         queries.find_courses(db, department="Кафедра ИС", min_credits=4))

    dump("AP-5. Поиск студентов по префиксу 'Ал'",
         queries.search_students(db, "Ал"))

    dump("AP-6. Статистика по дисциплине IS-101 ($facet/$bucket)",
         queries.course_grade_stats(db, "IS-101"))

    dump("AP-7. GPA по студентам (взвешенный по кредитам)",
         queries.students_gpa(db)[:5])

    dump("AP-8. Топ-5 дисциплин по числу регистраций",
         queries.top_courses_by_enrollment(db, 5))

    dump("AP-9. Задолженности (grade < 60)",
         queries.students_with_failing_grades(db)[:5])

    dump("AP-10. Нагрузка преподавателей",
         queries.teacher_workload(db))

    # --- сравнение планов: индекс vs отсутствие индекса ---------------------
    print("=" * 78)
    print("Сравнение планов выполнения")
    print("-" * 78)
    indexed = db.students.find({"student_no": "IS-2022-001"}).explain()
    print("student_no (uq_student_no):",
          "IXSCAN" if plan_contains(indexed, "IXSCAN") else "COLLSCAN")

    unindexed = db.students.find({"email": "student01@univ.local"}).explain()
    print("email (без индекса):       ",
          "IXSCAN" if plan_contains(unindexed, "IXSCAN") else "COLLSCAN")


if __name__ == "__main__":
    main()
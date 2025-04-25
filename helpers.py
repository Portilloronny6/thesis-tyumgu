"""Вспомогательные функции для генерации конфигураций."""

from typing import Dict, List
import csv
import json
from pathlib import Path
from collections import defaultdict

from nbgrader.api import SubmittedNotebook
from nbgrader.apps import GenerateAssignmentApp, ReleaseAssignmentApp


def _parse_csv(csv_path: Path):
    """Разбирает CSV-файл и возвращает пользователей и курсы."""
    users: Dict[str, Dict] = {}
    courses = defaultdict(lambda: dict(instructors=[], graders=[], students=[]))

    with csv_path.open(newline="") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            username = row["username"].strip()
            role = row["role"].strip().lower()
            course_ids = [
                c.strip().replace(" ", "").replace("-", "").replace("_", "")
                for c in row["courses"].split(";")
                if c.strip()
            ]
            users[username] = dict(role=role, courses=course_ids)

            for cid in course_ids:
                bucket = (
                    "students"
                    if role == "student"
                    else "instructors"
                    if role == "instructor"
                    else None
                )
                if bucket:
                    courses[cid][bucket].append(username)

    for cid in courses:
        guser = f"grader-{cid}"
        if guser not in users:
            users[guser] = dict(role="grader", courses=[cid])
        courses[cid]["graders"].append(guser)

    return users, courses


def _bash_array(name: str, elements: List[str]) -> str:
    """Формирует bash-массив из элементов."""
    quoted = " ".join(json.dumps(e) for e in elements)
    return f"{name}=({quoted})"

ReleaseAssignmentApp.initialize
SubmittedNotebook
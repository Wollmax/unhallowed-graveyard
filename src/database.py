"""Модуль работы с базой данных SQLite для UniVault.
Содержит только SQLite запросы, схему и модели данных согласно SPEC.md.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


# Статусы практических/лабораторных работ
STATUS_NOT_STARTED = "NOT_STARTED"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_REPORTING = "REPORTING"
STATUS_WAIT_DEFENSE = "WAIT_DEFENSE"
STATUS_REWORK = "REWORK"
STATUS_COMPLETED = "COMPLETED"

STATUS_LABELS: Dict[str, str] = {
    STATUS_NOT_STARTED: "Не начато",
    STATUS_IN_PROGRESS: "В работе",
    STATUS_REPORTING: "Оформление отчета",
    STATUS_WAIT_DEFENSE: "Ждет защиты",
    STATUS_REWORK: "На доработке",
    STATUS_COMPLETED: "Сдано",
}

STATUS_DEFAULT_PROGRESS: Dict[str, int] = {
    STATUS_NOT_STARTED: 0,
    STATUS_IN_PROGRESS: 30,
    STATUS_REPORTING: 60,
    STATUS_WAIT_DEFENSE: 85,
    STATUS_REWORK: 50,
    STATUS_COMPLETED: 100,
}

TASK_TYPES = [
    "Практическая",
    "Лабораторная",
    "Курсовая",
    "Реферат",
]

EXAM_TYPES = [
    "Экзамен",
    "Зачет",
    "Диф. зачет",
]


@dataclass
class Subject:
    id: int
    name: str
    short_name: Optional[str]
    teacher_name: Optional[str]
    exam_type: Optional[str]
    folder_path: str
    color_hex: str
    total_tasks: int = 0
    completed_tasks: int = 0


@dataclass
class Task:
    id: int
    subject_id: int
    number: int
    type: str
    title: str
    variant: Optional[str]
    status: str
    progress_percent: int
    deadline_date: Optional[str]
    completed_date: Optional[str]
    score: Optional[float]
    notes: Optional[str]
    folder_path: str
    subject_name: Optional[str] = None
    subject_color: Optional[str] = None


class Database:
    """Менеджер базы данных SQLite."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Создает подключение с включенными foreign keys и закрывает его при выходе."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Инициализация таблиц согласно спецификации."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Таблица настроек
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                """
            )

            # Таблица предметов
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    short_name TEXT,
                    teacher_name TEXT,
                    exam_type TEXT,
                    folder_path TEXT NOT NULL,
                    color_hex TEXT DEFAULT '#4F46E5'
                );
                """
            )

            # Таблица практических / лабораторных работ
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER NOT NULL,
                    number INTEGER DEFAULT 1,
                    type TEXT DEFAULT 'Практическая',
                    title TEXT NOT NULL,
                    variant TEXT,
                    status TEXT NOT NULL DEFAULT 'NOT_STARTED',
                    progress_percent INTEGER DEFAULT 0,
                    deadline_date TEXT,
                    completed_date TEXT,
                    score REAL,
                    notes TEXT,
                    folder_path TEXT NOT NULL,
                    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
                );
                """
            )

            # Таблица чек-листа внутри работы
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS subtasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    is_done INTEGER DEFAULT 0,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                );
                """
            )

            conn.commit()

    # --- Настройки ---

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?;", (key,)
            ).fetchone()
            if row:
                return row["value"]
            return default

    def set_setting(self, key: str, value: str) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
                """,
                (key, str(value)),
            )
            conn.commit()

    def get_all_settings(self) -> Dict[str, str]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings;").fetchall()
            return {row["key"]: row["value"] for row in rows}

    # --- Предметы ---

    def add_subject(
        self,
        name: str,
        short_name: Optional[str],
        teacher_name: Optional[str],
        exam_type: Optional[str],
        folder_path: str,
        color_hex: str = "#4F46E5",
    ) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO subjects (name, short_name, teacher_name, exam_type, folder_path, color_hex)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (name.strip(), short_name.strip() if short_name else None,
                 teacher_name.strip() if teacher_name else None,
                 exam_type, folder_path.strip(), color_hex),
            )
            conn.commit()
            return cursor.lastrowid

    def update_subject(
        self,
        subject_id: int,
        name: str,
        short_name: Optional[str],
        teacher_name: Optional[str],
        exam_type: Optional[str],
        color_hex: str,
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE subjects
                SET name = ?, short_name = ?, teacher_name = ?, exam_type = ?, color_hex = ?
                WHERE id = ?;
                """,
                (name.strip(), short_name.strip() if short_name else None,
                 teacher_name.strip() if teacher_name else None,
                 exam_type, color_hex, subject_id),
            )
            conn.commit()

    def delete_subject(self, subject_id: int) -> None:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM subjects WHERE id = ?;", (subject_id,))
            conn.commit()

    def get_subject(self, subject_id: int) -> Optional[Subject]:
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT s.*,
                       COUNT(t.id) AS total_tasks,
                       SUM(CASE WHEN t.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_tasks
                FROM subjects s
                LEFT JOIN tasks t ON t.subject_id = s.id
                WHERE s.id = ?
                GROUP BY s.id;
                """,
                (subject_id,),
            ).fetchone()
            if not row:
                return None
            return Subject(
                id=row["id"],
                name=row["name"],
                short_name=row["short_name"],
                teacher_name=row["teacher_name"],
                exam_type=row["exam_type"],
                folder_path=row["folder_path"],
                color_hex=row["color_hex"] or "#4F46E5",
                total_tasks=row["total_tasks"] or 0,
                completed_tasks=row["completed_tasks"] or 0,
            )

    def get_subjects(self) -> List[Subject]:
        """Возвращает список предметов с количеством задач и сданных работ."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.*,
                       COUNT(t.id) AS total_tasks,
                       SUM(CASE WHEN t.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_tasks
                FROM subjects s
                LEFT JOIN tasks t ON t.subject_id = s.id
                GROUP BY s.id
                ORDER BY s.name COLLATE NOCASE ASC;
                """
            ).fetchall()
            return [
                Subject(
                    id=row["id"],
                    name=row["name"],
                    short_name=row["short_name"],
                    teacher_name=row["teacher_name"],
                    exam_type=row["exam_type"],
                    folder_path=row["folder_path"],
                    color_hex=row["color_hex"] or "#4F46E5",
                    total_tasks=row["total_tasks"] or 0,
                    completed_tasks=row["completed_tasks"] or 0,
                )
                for row in rows
            ]

    # --- Задачи (Практические / Лабораторные) ---

    def add_task(
        self,
        subject_id: int,
        number: int,
        task_type: str,
        title: str,
        variant: Optional[str],
        status: str,
        progress_percent: int,
        deadline_date: Optional[str],
        notes: Optional[str],
        folder_path: str,
        score: Optional[float] = None,
    ) -> int:
        completed_date = (
            datetime.now().strftime("%Y-%m-%d %H:%M")
            if status == STATUS_COMPLETED
            else None
        )
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tasks (
                    subject_id, number, type, title, variant,
                    status, progress_percent, deadline_date,
                    completed_date, score, notes, folder_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    subject_id,
                    number,
                    task_type,
                    title.strip(),
                    variant.strip() if variant else None,
                    status,
                    progress_percent,
                    deadline_date,
                    completed_date,
                    score,
                    notes.strip() if notes else None,
                    folder_path.strip(),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def update_task(
        self,
        task_id: int,
        number: int,
        task_type: str,
        title: str,
        variant: Optional[str],
        status: str,
        progress_percent: int,
        deadline_date: Optional[str],
        notes: Optional[str],
        score: Optional[float] = None,
    ) -> None:
        completed_date = None
        if status == STATUS_COMPLETED:
            completed_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET number = ?, type = ?, title = ?, variant = ?,
                    status = ?, progress_percent = ?, deadline_date = ?,
                    completed_date = COALESCE(?, completed_date),
                    score = ?, notes = ?
                WHERE id = ?;
                """,
                (
                    number,
                    task_type,
                    title.strip(),
                    variant.strip() if variant else None,
                    status,
                    progress_percent,
                    deadline_date,
                    completed_date,
                    score,
                    notes.strip() if notes else None,
                    task_id,
                ),
            )
            conn.commit()

    def update_task_status(
        self,
        task_id: int,
        new_status: str,
        progress_percent: Optional[int] = None,
    ) -> None:
        """Быстрое обновление статуса (например, прямо из выпадающего списка на карточке)."""
        if progress_percent is None:
            progress_percent = STATUS_DEFAULT_PROGRESS.get(new_status, 0)

        completed_date = (
            datetime.now().strftime("%Y-%m-%d %H:%M")
            if new_status == STATUS_COMPLETED
            else None
        )

        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?,
                    progress_percent = ?,
                    completed_date = CASE
                        WHEN ? = 'COMPLETED' THEN ?
                        ELSE NULL
                    END
                WHERE id = ?;
                """,
                (new_status, progress_percent, new_status, completed_date, task_id),
            )
            conn.commit()

    def update_task_progress(self, task_id: int, progress_percent: int) -> None:
        """Обновляет процент выполнения работы."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE tasks SET progress_percent = ? WHERE id = ?;",
                (progress_percent, task_id),
            )
            conn.commit()

    def update_task_deadline(self, task_id: int, deadline_date: Optional[str]) -> None:
        """Обновляет дату дедлайна работы."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE tasks SET deadline_date = ? WHERE id = ?;",
                (deadline_date, task_id),
            )
            conn.commit()

    def update_task_notes(self, task_id: int, notes: Optional[str]) -> None:
        """Обновляет заметки преподавателя/студента для работы."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE tasks SET notes = ? WHERE id = ?;",
                (notes.strip() if notes else None, task_id),
            )
            conn.commit()

    def delete_task(self, task_id: int) -> None:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
            conn.commit()

    def get_task(self, task_id: int) -> Optional[Task]:
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT t.*, s.name AS subject_name, s.color_hex AS subject_color
                FROM tasks t
                JOIN subjects s ON s.id = t.subject_id
                WHERE t.id = ?;
                """,
                (task_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def get_tasks(
        self,
        subject_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[Task]:
        """Возвращает список работ с поддержкой фильтрации по предмету, статусу и поиску."""
        query = """
            SELECT t.*, s.name AS subject_name, s.color_hex AS subject_color
            FROM tasks t
            JOIN subjects s ON s.id = t.subject_id
            WHERE 1=1
        """
        params: List[Any] = []

        if subject_id is not None:
            query += " AND t.subject_id = ?"
            params.append(subject_id)

        if status_filter:
            if status_filter == "ACTIVE":
                query += " AND t.status != 'COMPLETED'"
            elif status_filter == "COMPLETED":
                query += " AND t.status = 'COMPLETED'"
            elif status_filter in STATUS_LABELS:
                query += " AND t.status = ?"
                params.append(status_filter)

        if search_query:
            query += " AND (t.title LIKE ? OR s.name LIKE ? OR t.variant LIKE ?)"
            wildcard = f"%{search_query.strip()}%"
            params.extend([wildcard, wildcard, wildcard])

        query += " ORDER BY t.number ASC, t.deadline_date ASC;"

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_task(r) for r in rows]

    def get_next_task_number(self, subject_id: int, task_type: str = "Практическая") -> int:
        """Определяет следующий порядковый номер для нового задания."""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT MAX(number) as max_num
                FROM tasks
                WHERE subject_id = ? AND type = ?;
                """,
                (subject_id, task_type),
            ).fetchone()
            if row and row["max_num"] is not None:
                return int(row["max_num"]) + 1
            return 1

    # --- Подзадачи (чек-лист) ---

    def get_subtasks(self, task_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM subtasks WHERE task_id = ? ORDER BY id ASC;",
                (task_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def add_subtask(self, task_id: int, title: str, is_done: int = 0) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO subtasks (task_id, title, is_done) VALUES (?, ?, ?);",
                (task_id, title.strip(), 1 if is_done else 0),
            )
            conn.commit()
            return cursor.lastrowid

    def set_subtask_done(self, subtask_id: int, is_done: bool) -> None:
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE subtasks SET is_done = ? WHERE id = ?;",
                (1 if is_done else 0, subtask_id),
            )
            conn.commit()

    def delete_subtask(self, subtask_id: int) -> None:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM subtasks WHERE id = ?;", (subtask_id,))
            conn.commit()

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            subject_id=row["subject_id"],
            number=row["number"],
            type=row["type"],
            title=row["title"],
            variant=row["variant"],
            status=row["status"],
            progress_percent=row["progress_percent"] or 0,
            deadline_date=row["deadline_date"],
            completed_date=row["completed_date"],
            score=row["score"],
            notes=row["notes"],
            folder_path=row["folder_path"],
            subject_name=row["subject_name"] if "subject_name" in row.keys() else None,
            subject_color=row["subject_color"] if "subject_color" in row.keys() else None,
        )

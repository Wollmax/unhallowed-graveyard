"""Тестовый скрипт проверки Шага 1 и Шага 2:
- Инициализация SQLite базы данных
- CRUD операции с предметами и практическими работами
- Создание структуры директорий (01_Task, 02_Workspace, 03_Submission)
"""

import shutil
import tempfile
from pathlib import Path

from src.database import (
    Database,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_NOT_STARTED,
)
from src.fs_manager import FSManager, sanitize_folder_name


def test_fs_sanitizer():
    raw_name = 'Тест / Недопустимые: * ? " < > | символы...'
    cleaned = sanitize_folder_name(raw_name)
    assert "/" not in cleaned
    assert ":" not in cleaned
    assert "*" not in cleaned
    assert "?" not in cleaned
    assert '"' not in cleaned
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "|" not in cleaned
    assert not cleaned.endswith(".")
    print("[OK] Test sanitizer passed:", cleaned)


def test_core_flow():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test_univault.db"
        workspace_path = tmp_path / "Workspace"

        # 1. Инициализация DB и FSManager
        db = Database(db_path)
        fs = FSManager(workspace_path)

        assert (workspace_path / "_Templates").exists(), "Папка _Templates не создана"
        print("[OK] Workspace and _Templates created")

        # 2. Добавление предмета
        subject_name = "Структуры и алгоритмы данных"
        short_name = "СИАОД"
        folder_name = fs.create_subject_folder(subject_name, short_name)

        subject_dir = workspace_path / folder_name
        assert subject_dir.exists(), "Папка предмета не создана"
        assert (subject_dir / "_Materials").exists(), "Папка _Materials не создана"

        subj_id = db.add_subject(
            name=subject_name,
            short_name=short_name,
            teacher_name="Профессор Смирнов",
            exam_type="Экзамен",
            folder_path=folder_name,
            color_hex="#6366F1",
        )
        assert subj_id > 0, "ID предмета некорректен"
        print(f"[OK] Subject added (ID={subj_id}) -> {folder_name}")

        # 3. Добавление практической работы
        task_title = "Хеш-таблицы и разрешение коллизий"
        task_folder = fs.create_task_folders(
            subject_folder=folder_name,
            number=1,
            task_type="Практическая",
            title=task_title,
        )

        task_dir = workspace_path / folder_name / task_folder
        assert task_dir.exists(), "Папка задания не создана"
        assert (task_dir / "01_Task").exists(), "01_Task не создана"
        assert (task_dir / "02_Workspace").exists(), "02_Workspace не создана"
        assert (task_dir / "03_Submission").exists(), "03_Submission не создана"
        print(f"[OK] Task subfolders created: {task_folder}")

        task_id = db.add_task(
            subject_id=subj_id,
            number=1,
            task_type="Практическая",
            title=task_title,
            variant="Вариант 5",
            status=STATUS_NOT_STARTED,
            progress_percent=0,
            deadline_date="2026-11-15 23:59",
            notes="Использовать метод цепочек",
            folder_path=task_folder,
        )
        assert task_id > 0, "ID работы некорректен"
        print(f"[OK] Task added (ID={task_id})")

        # 4. Проверка получения задач и обновления статуса
        tasks = db.get_tasks(subject_id=subj_id)
        assert len(tasks) == 1
        assert tasks[0].title == task_title
        assert tasks[0].status == STATUS_NOT_STARTED

        # Обновляем статус
        db.update_task_status(task_id, STATUS_IN_PROGRESS, progress_percent=40)
        task_updated = db.get_task(task_id)
        assert task_updated.status == STATUS_IN_PROGRESS
        assert task_updated.progress_percent == 40
        print("[OK] Task status updated to IN_PROGRESS (40%)")

        # Завершаем задачу
        db.update_task_status(task_id, STATUS_COMPLETED)
        task_completed = db.get_task(task_id)
        assert task_completed.status == STATUS_COMPLETED
        assert task_completed.progress_percent == 100
        assert task_completed.completed_date is not None
        print("[OK] Task status updated to COMPLETED (100%)")

        # Проверка статистики предмета
        subjects = db.get_subjects()
        assert len(subjects) == 1
        assert subjects[0].total_tasks == 1
        assert subjects[0].completed_tasks == 1
        print("[OK] Subject statistics verified (1 of 1 completed)")

        # 5. Проверка добавления подзадач (чек-лист)
        st_id1 = db.add_subtask(task_id, "Написать код хеш-таблицы")
        st_id2 = db.add_subtask(task_id, "Оформить отчет в docx")
        subtasks = db.get_subtasks(task_id)
        assert len(subtasks) == 2
        db.set_subtask_done(st_id1, True)
        subtasks_updated = db.get_subtasks(task_id)
        assert subtasks_updated[0]["is_done"] == 1
        print("[OK] Checklist subtasks verified")

        # 6. Проверка списка файлов в подпапках
        sample_task_file = task_dir / "01_Task" / "metodichka.pdf"
        sample_task_file.write_text("dummy pdf", encoding="utf-8")
        files = fs.list_task_files(folder_name, task_folder)
        assert len(files["task"]) == 1
        assert files["task"][0].name == "metodichka.pdf"
        print("[OK] Task subfolder file scan (01_Task) verified")

    print("\n[SUCCESS] All Step 1 Core tests passed successfully!")


if __name__ == "__main__":
    test_fs_sanitizer()
    test_core_flow()

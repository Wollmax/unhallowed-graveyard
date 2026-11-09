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
    STATUS_WAIT_DEFENSE,
    parse_deadline_datetime,
    is_deadline_hot,
)
from src.ui.theme import get_md3_urgency
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

        # 7. Проверка Шага 5: Горящие дедлайны и статистика
        from datetime import datetime, timedelta

        # Проверка parse_deadline_datetime
        assert parse_deadline_datetime(None) is None
        assert parse_deadline_datetime("") is None
        assert parse_deadline_datetime("invalid-date-format") is None
        iso_t = parse_deadline_datetime("2026-11-20T18:30")
        assert iso_t is not None and iso_t.year == 2026 and iso_t.hour == 18 and iso_t.minute == 30
        iso_sec = parse_deadline_datetime("2026-11-20T18:30:45")
        assert iso_sec is not None and iso_sec.second == 45
        date_only = parse_deadline_datetime("2026-11-20")
        assert date_only is not None and date_only.hour == 23 and date_only.minute == 59 and date_only.second == 59
        ru_date = parse_deadline_datetime("20.11.2026")
        assert ru_date is not None and ru_date.hour == 23 and ru_date.minute == 59 and ru_date.second == 59
        ru_dt = parse_deadline_datetime("20.11.2026 14:15")
        assert ru_dt is not None and ru_dt.hour == 14 and ru_dt.minute == 15
        print("[OK] Step 5: parse_deadline_datetime edge cases verified")

        now = datetime.now()
        overdue_str = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
        crit_str = (now + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M")
        crit_iso_str = (now + timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M")
        warn_str = (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
        future_str = (now + timedelta(days=10)).strftime("%Y-%m-%d %H:%M")

        # Проверка функции is_deadline_hot
        assert is_deadline_hot(overdue_str, STATUS_IN_PROGRESS) is True
        assert is_deadline_hot(crit_str, STATUS_NOT_STARTED) is True
        assert is_deadline_hot(crit_iso_str, STATUS_NOT_STARTED) is True
        assert is_deadline_hot(warn_str, STATUS_IN_PROGRESS) is True
        assert is_deadline_hot(future_str, STATUS_IN_PROGRESS) is False
        assert is_deadline_hot(overdue_str, STATUS_COMPLETED) is False
        assert is_deadline_hot(overdue_str, STATUS_WAIT_DEFENSE) is False
        assert is_deadline_hot(crit_str, STATUS_WAIT_DEFENSE) is False
        assert is_deadline_hot(None, STATUS_IN_PROGRESS) is False
        print("[OK] Step 5: is_deadline_hot validation passed")

        # Проверка get_md3_urgency с учетом статуса и форматов дат
        assert get_md3_urgency(overdue_str, status=STATUS_IN_PROGRESS)[0] == "OVERDUE"
        assert get_md3_urgency(overdue_str, status=STATUS_COMPLETED)[0] == "COMPLETED"
        assert get_md3_urgency(overdue_str, status=STATUS_WAIT_DEFENSE)[0] == "WAIT_DEFENSE"
        assert get_md3_urgency(crit_str, status=STATUS_IN_PROGRESS)[0] == "CRITICAL"
        assert get_md3_urgency(crit_iso_str, status=STATUS_IN_PROGRESS)[0] == "CRITICAL"
        assert get_md3_urgency(warn_str, status=STATUS_IN_PROGRESS)[0] == "WARNING"
        assert get_md3_urgency(future_str, status=STATUS_IN_PROGRESS)[0] == "NORMAL"
        print("[OK] Step 5: get_md3_urgency tiers and neutral statuses verified")

        # Добавляем задачи с разными сроками
        t_overdue = db.add_task(
            subject_id=subj_id,
            number=2,
            task_type="Лабораторная",
            title="Просроченная работа",
            variant="Вар 1",
            status=STATUS_IN_PROGRESS,
            progress_percent=30,
            deadline_date=overdue_str,
            notes=None,
            folder_path="task_2",
        )
        t_crit = db.add_task(
            subject_id=subj_id,
            number=3,
            task_type="Практическая",
            title="Критическая работа <24ч",
            variant=None,
            status=STATUS_NOT_STARTED,
            progress_percent=0,
            deadline_date=crit_str,
            notes=None,
            folder_path="task_3",
        )
        t_future = db.add_task(
            subject_id=subj_id,
            number=4,
            task_type="Практическая",
            title="Далекая работа",
            variant=None,
            status=STATUS_IN_PROGRESS,
            progress_percent=20,
            deadline_date=future_str,
            notes=None,
            folder_path="task_4",
        )
        t_defense = db.add_task(
            subject_id=subj_id,
            number=5,
            task_type="Лабораторная",
            title="Работа на проверке (дедлайн прошел)",
            variant=None,
            status=STATUS_WAIT_DEFENSE,
            progress_percent=85,
            deadline_date=overdue_str,
            notes=None,
            folder_path="task_5",
        )
        t_no_deadline = db.add_task(
            subject_id=subj_id,
            number=6,
            task_type="Реферат",
            title="Реферат без срока",
            variant=None,
            status=STATUS_NOT_STARTED,
            progress_percent=0,
            deadline_date=None,
            notes=None,
            folder_path="task_6",
        )

        # Проверка get_hot_tasks и сортировки по дедлайну
        hot_tasks = db.get_hot_tasks()
        assert len(hot_tasks) == 2  # t_overdue and t_crit (t_defense исключен)
        assert hot_tasks[0].id == t_overdue  # Просроченная должна идти первой
        assert hot_tasks[1].id == t_crit
        print("[OK] Step 5: get_hot_tasks verified and ordered by urgency")

        # Проверка get_deadline_stats
        stats = db.get_deadline_stats()
        assert stats["overdue"] == 1
        assert stats["critical_24h"] == 1
        assert stats["warning_3d"] == 0
        assert stats["normal"] == 2  # t_future + t_defense
        assert stats["no_deadline"] == 1  # t_no_deadline
        assert stats["hot_count"] == 2
        assert stats["total_active"] == (
            stats["overdue"] + stats["critical_24h"] + stats["warning_3d"] + stats["normal"] + stats["no_deadline"]
        )
        print(f"[OK] Step 5: get_deadline_stats verified: {stats}")

        # Проверка краевых случаев Step 5:
        # А) Полночь 00:00 и секунды в русском формате
        dt_midnight = parse_deadline_datetime("2026-11-20 00:00")
        assert dt_midnight is not None and dt_midnight.hour == 0 and dt_midnight.minute == 0
        dt_ru_sec = parse_deadline_datetime("20.11.2026 14:15:30")
        assert dt_ru_sec is not None and dt_ru_sec.second == 30
        print("[OK] Step 5: midnight and Russian seconds parsing verified")

        # Б) Хронологическая сортировка разных форматов дат (Русский vs ISO)
        t_early_iso = db.add_task(
            subject_id=subj_id,
            number=7,
            task_type="Практическая",
            title="Ранняя задача ISO (5 ноября)",
            variant=None,
            status=STATUS_IN_PROGRESS,
            progress_percent=10,
            deadline_date="2026-11-05 12:00",
            notes=None,
            folder_path="task_7",
        )
        t_late_ru = db.add_task(
            subject_id=subj_id,
            number=8,
            task_type="Практическая",
            title="Поздняя задача RU (20 ноября)",
            variant=None,
            status=STATUS_IN_PROGRESS,
            progress_percent=10,
            deadline_date="20.11.2026 12:00",
            notes=None,
            folder_path="task_8",
        )
        all_ordered = db.get_tasks(order_by_deadline=True)
        task_ids_ordered = [t.id for t in all_ordered]
        assert task_ids_ordered.index(t_early_iso) < task_ids_ordered.index(t_late_ru)
        print("[OK] Step 5: Mixed date format chronological ordering verified")

        # В) WAIT_DEFENSE без дедлайна строго учитывается в no_deadline
        t_defense_no_dl = db.add_task(
            subject_id=subj_id,
            number=9,
            task_type="Лабораторная",
            title="Защита без срока",
            variant=None,
            status=STATUS_WAIT_DEFENSE,
            progress_percent=90,
            deadline_date=None,
            notes=None,
            folder_path="task_9",
        )
        stats2 = db.get_deadline_stats()
        assert stats2["no_deadline"] == 2
        print("[OK] Step 5: WAIT_DEFENSE without deadline properly attributed to no_deadline")

    print("\n[SUCCESS] All Step 1 & Step 5 Core tests passed successfully!")


if __name__ == "__main__":
    test_fs_sanitizer()
    test_core_flow()

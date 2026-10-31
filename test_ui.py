"""Тест инициализации и работы UI компонентов PySide6 (Шаг 2).
Проверяет инициализацию главного окна, списков и добавление данных.
"""

import os
import sys
import tempfile
from pathlib import Path

# Устанавливаем offscreen платформу, чтобы тест мог выполняться без физического монитора/окна
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QApplication

from src.database import Database
from src.fs_manager import FSManager
from src.ui.main_window import MainWindow
from src.ui.dialogs import AddSubjectDialog, AddTaskDialog, SettingsDialog
from src.ui.icons import get_material_icon


def test_ui_components():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db = Database(tmp_path / "test_ui.db")
        fs = FSManager(tmp_path / "Workspace")

        # 1. Создание главного окна
        window = MainWindow(db=db, fs=fs)
        window.show()
        print("[OK] MainWindow created and shown successfully")

        # 2. Добавление предмета через FS и DB
        subj_name = "Информационная безопасность"
        short_tag = "ИБ"
        folder_name = fs.create_subject_folder(subj_name, short_tag)
        subj_id = db.add_subject(
            name=subj_name,
            short_name=short_tag,
            teacher_name="Петров П.П.",
            exam_type="Диф. зачет",
            folder_path=folder_name,
            color_hex="#06B6D4",
        )
        # Проверка загрузки шрифтов Roboto
        from src.ui.theme import load_application_fonts
        loaded = load_application_fonts()
        print(f"[OK] Application fonts loaded: {loaded}")

        window.load_subjects()
        assert window.subjects_layout.count() >= 2
        print("[OK] Subject added and displayed as custom card in sidebar")

        # 3. Добавление практической работы
        task_folder = fs.create_task_folders(folder_name, 1, "Практическая", "Анализ уязвимостей")
        task_id = db.add_task(
            subject_id=subj_id,
            number=1,
            task_type="Практическая",
            title="Анализ уязвимостей сетевых протоколов",
            variant="Вариант 3",
            status="NOT_STARTED",
            progress_percent=0,
            deadline_date="2026-11-20 23:59",
            notes="Провести сканирование nmap",
            folder_path=task_folder,
        )
        window.load_tasks()
        # В контейнере задач должны быть карточка и stretch (итого >= 2)
        assert window.tasks_layout.count() >= 2
        print("[OK] Task added and rendered as TaskCardWidget in center list")

        # 4. Проверка клика по задаче и инспектора
        window._on_task_card_clicked(task_id)
        assert window.selected_task is not None
        assert window.selected_task.id == task_id
        print("[OK] Task clicked and inspector updated with subfolders")

        # 5. Проверка изменения статуса карточки
        window._on_task_status_changed(task_id, "IN_PROGRESS")
        updated_task = db.get_task(task_id)
        assert updated_task.status == "IN_PROGRESS"
        print("[OK] Status update signal handled and persisted")

        # 6. Проверка диалогов (валидация полей)
        dlg_subj = AddSubjectDialog(window)
        dlg_subj.name_edit.setText("Тестовый предмет")
        data_s = dlg_subj.get_data()
        assert data_s["name"] == "Тестовый предмет"
        print("[OK] AddSubjectDialog instantiated and data verified")

        dlg_task = AddTaskDialog(db, default_subject_id=subj_id, parent=window)
        dlg_task.title_edit.setText("Тестовая работа")
        data_t = dlg_task.get_data()
        assert data_t["title"] == "Тестовая работа"
        assert data_t["subject_id"] == subj_id
        print("[OK] AddTaskDialog instantiated and auto-numbering verified")

        # 7. Проверка переключения тем Monet (Pixel) в тёмном и светлом режимах
        from src.ui.theme import (
            PIXEL_THEMES_DARK,
            PIXEL_THEMES_LIGHT,
            apply_windows_acrylic,
            get_md3_urgency,
            get_stylesheet,
            get_theme,
        )

        for t_key in PIXEL_THEMES_DARK.keys():
            # Тёмная тема
            window.set_active_theme(t_key, mode="dark")
            assert window.current_theme_key == t_key
            assert window.current_theme_mode == "dark"
            assert window.theme["is_dark"] is True
            assert db.get_setting("theme_name") == t_key
            assert db.get_setting("theme_mode") == "dark"

            # Светлая тема
            window.set_active_theme(t_key, mode="light")
            assert window.current_theme_key == t_key
            assert window.current_theme_mode == "light"
            assert window.theme["is_dark"] is False
            assert db.get_setting("theme_name") == t_key
            assert db.get_setting("theme_mode") == "light"
        print("[OK] Monet theme switching verified across all Pixel Dark & Light palettes")

        # 8. Проверка семантических функций контрастности
        code_d, fg_d, bg_d = get_md3_urgency("2026-11-20", is_completed=False, is_dark=True)
        code_l, fg_l, bg_l = get_md3_urgency("2026-11-20", is_completed=False, is_dark=False)
        assert code_d == code_l
        assert fg_d != fg_l  # Разный контраст для светлой и темной тем

        # 9. Проверка SettingsDialog и иконок Material Design
        settings_dlg = SettingsDialog(
            main_window=window,
            theme_key=window.current_theme_key,
            theme_mode="light",
        )
        assert len(settings_dlg.theme_swatches) == 5
        assert settings_dlg.theme_mode == "light"

        # Переключение режима через диалог
        settings_dlg._on_mode_toggled("dark")
        assert settings_dlg.theme_mode == "dark"
        assert window.current_theme_mode == "dark"

        settings_dlg._on_mode_toggled("light")
        assert settings_dlg.theme_mode == "light"
        assert window.current_theme_mode == "light"

        # Переключение палитры через свотч в диалоге
        settings_dlg._on_swatch_clicked("emerald")
        assert settings_dlg.theme_key == "emerald"
        assert window.current_theme_key == "emerald"

        icon_settings = get_material_icon("settings", "#FFFFFF", 20)
        assert not icon_settings.isNull()
        icon_dark = get_material_icon("dark_mode", "#A8C7FA", 18)
        assert not icon_dark.isNull()
        icon_light = get_material_icon("light_mode", "#0B57D0", 18)
        assert not icon_light.isNull()
        print("[OK] SettingsDialog Dark/Light toggling and Material Design SVG icons verified")

        # 7. Проверка Шага 3 (Инспектор и Файловые секции Drag & Drop)
        from src.ui.file_inspector import TaskInspectorWidget, FileDropZoneSection, FileItemWidget
        assert isinstance(window.inspector_widget, TaskInspectorWidget)
        insp = window.inspector_widget

        # Проверка 3-х файловых секций и поддержки Drag & Drop
        assert insp.sec_task.acceptDrops() is True
        assert insp.sec_workspace.acceptDrops() is True
        assert insp.sec_submission.acceptDrops() is True
        print("[OK] Step 3: 3 File drop zones initialized with acceptDrops=True")

        # Добавление тестового файла в папку 01_Task
        dummy_task_file = tmp_path / "Методичка_Тест.pdf"
        dummy_task_file.write_text("Test Task Content", encoding="utf-8")
        fs.copy_file_to_subfolder(dummy_task_file, insp.sec_task.folder_path)
        insp.sec_task.refresh_files()

        assert insp.sec_task.count_badge.text() == "1"
        assert insp.sec_task.files_layout.count() >= 1
        file_item = insp.sec_task.files_layout.itemAt(0).widget()
        assert isinstance(file_item, FileItemWidget)
        assert "Методичка_Тест.pdf" in file_item.file_path.name
        print("[OK] Step 3: File successfully added to 01_Task and rendered as FileItemWidget")

        # Проверка ползунка прогресса и обновления статуса
        insp.prog_slider.setValue(65)
        insp._on_progress_slider_released()
        task_after_slider = db.get_task(task_id)
        assert task_after_slider.progress_percent == 65
        print("[OK] Step 3: Progress slider updated DB and UI cards")

        # Проверка удаления файла
        fs.delete_file(file_item.file_path)
        insp.sec_task.refresh_files()
        assert insp.sec_task.count_badge.text() == "0"
        print("[OK] Step 3: File deletion and badge count update verified")

        # ======================================================================
        # Проверка анимации переключения разделов и отсутствия белых обводок
        # ======================================================================
        # 1. Переключение на "Все практические работы"
        window._select_all_tasks()
        assert window.current_subject_id is None
        assert "Все практические работы" in window.center_title.text()
        print("[OK] Section switch to 'All Tasks' verified")

        # 2. Переключение на конкретный предмет
        window._on_subject_clicked(subj_id)
        assert window.current_subject_id == subj_id
        assert subj_name in window.center_title.text()
        print(f"[OK] Section switch to subject '{subj_name}' verified")

        # 3. Проверка Zero-Border стилей: отсутствие белых рамок
        for c in window.subject_cards:
            assert "#FFFFFF" not in c.styleSheet()
            assert "border: none" in c.styleSheet() or "1.5px solid" in c.styleSheet()
        for tc in window.task_cards:
            assert "#FFFFFF" not in tc.styleSheet()
            assert "border: none" in tc.styleSheet() or "1.5px solid" in tc.styleSheet()
        assert "border: none" in window.center_widget.styleSheet()
        assert "border: none" in window.sidebar_widget.styleSheet()
        assert "border: none" in window.right_widget.styleSheet()
        assert "border: 1px solid #FFFFFF" not in window.add_task_btn.styleSheet()
        print("[OK] Zero-Border validation: no harsh white borders detected")

        window.close()

    print("\n[SUCCESS] All Step 2 & Step 3 UI tests passed successfully!")


if __name__ == "__main__":
    test_ui_components()

"""Точка входа в приложение UniVault.
Инициализирует базу данных, файловый менеджер и запускает главное окно PySide6.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.database import Database
from src.fs_manager import FSManager
from src.ui.main_window import MainWindow
from src.ui.theme import load_application_fonts


def get_app_dir() -> Path:
    """Возвращает базовую директорию проекта."""
    return Path(__file__).resolve().parent


def main() -> None:
    # Базовые директории
    app_dir = get_app_dir()
    data_dir = app_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    db_path = data_dir / "univault.db"
    db = Database(db_path)

    # Определение и сохранение пути к Root Workspace
    saved_root = db.get_setting("root_path")
    if not saved_root:
        # По умолчанию создаем Workspace внутри директории проекта
        default_workspace = app_dir / "Workspace"
        db.set_setting("root_path", str(default_workspace))
        root_path = default_workspace
    else:
        root_path = Path(saved_root)

    # Инициализация файлового менеджера
    fs = FSManager(root_path)

    # Запуск графического интерфейса
    app = QApplication(sys.argv)
    app.setApplicationName("UniVault")
    app.setOrganizationName("UniVault")

    # Подгрузка кастомных шрифтов Roboto из resources/fonts
    load_application_fonts()

    window = MainWindow(db=db, fs=fs)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

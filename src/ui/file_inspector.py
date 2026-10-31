"""Компонент детального инспектора практической работы и файловых зон (Шаг 3).
Включает поддержку Drag-and-Drop, открытие файлов по двойному клику,
удаление и добавление файлов, быстрые действия и редактирование метаданных задачи.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QDateTime, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QDragEnterEvent, QDropEvent, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QTextEdit,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ..database import (
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_LABELS,
    Database,
    Subject,
    Task,
)
from ..fs_manager import FSManager
from .icons import get_material_icon
from .theme import get_md3_urgency


class FileItemWidget(QFrame):
    """Строка отдельного файла с иконкой, именем, размером и кнопками действий."""

    file_deleted = Signal(Path)

    def __init__(
        self,
        file_path: Path,
        fs: FSManager,
        theme: dict,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.fs = fs
        self.theme = theme
        self.is_dark = is_dark

        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"{self.file_path.name}\n(Двойной клик — открыть файл)\nПуть: {self.file_path}")

        self._init_ui()

    def _init_ui(self) -> None:
        bg_col = "rgba(255, 255, 255, 0.04)" if self.is_dark else "rgba(0, 0, 0, 0.03)"
        hover_bg = "rgba(255, 255, 255, 0.10)" if self.is_dark else "rgba(0, 0, 0, 0.06)"

        self.setStyleSheet(
            f"""
            QFrame#fileItemFrame {{
                background-color: {bg_col};
                border: none;
                border-radius: 12px;
            }}
            QFrame#fileItemFrame:hover {{
                background-color: {hover_bg};
                border: 1px solid {self.theme.get('primary', '#8AB4F8')};
            }}
            """
        )
        self.setObjectName("fileItemFrame")
        self.setMinimumWidth(0)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 8, 6)
        layout.setSpacing(6)

        # 1. Иконка типа файла
        icon_name = self.fs.get_file_icon_name(self.file_path)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_material_icon(icon_name, color=self.theme.get("primary", "#8AB4F8"), size=18).pixmap(18, 18))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(icon_lbl)

        # 2. Имя файла и размер
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        name_text = self.file_path.name
        if len(name_text) > 24:
            display_name = name_text[:17] + "..." + name_text[-4:]
        else:
            display_name = name_text

        self.name_label = QLabel(display_name)
        self.name_label.setMinimumWidth(0)
        self.name_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {self.theme.get('text_primary', '#FFFFFF')}; background: transparent; border: none;"
        )
        self.name_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text_layout.addWidget(self.name_label)

        try:
            size_bytes = self.file_path.stat().st_size
            size_str = self.fs.format_file_size(size_bytes)
        except Exception:
            size_str = "—"

        self.size_label = QLabel(size_str)
        self.size_label.setStyleSheet(
            f"font-size: 10px; color: {self.theme.get('text_secondary', '#C4C7D0')}; background: transparent; border: none;"
        )
        self.size_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text_layout.addWidget(self.size_label)
        layout.addLayout(text_layout, 1)

        # 3. Кнопка «Открыть»
        open_btn = QPushButton()
        open_btn.setIcon(get_material_icon("open_in_new", color=self.theme.get("text_secondary", "#C4C7D0"), size=14))
        open_btn.setToolTip("Открыть файл в программе по умолчанию")
        open_btn.setFixedSize(24, 24)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            """
        )
        open_btn.clicked.connect(self._open_file)
        layout.addWidget(open_btn)

        # 4. Кнопка «Удалить»
        del_btn = QPushButton()
        del_btn.setIcon(get_material_icon("delete", color="#EF4444", size=14))
        del_btn.setToolTip("Удалить файл")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.18);
            }}
            """
        )
        del_btn.clicked.connect(self._confirm_delete)
        layout.addWidget(del_btn)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Открытие файла в программе по умолчанию по двойному клику."""
        if event.button() == Qt.LeftButton:
            self._open_file()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def _open_file(self) -> None:
        self.fs.open_file_default(self.file_path)

    def _confirm_delete(self) -> None:
        reply = QMessageBox.question(
            self,
            "Удаление файла",
            f"Вы уверены, что хотите удалить файл:\n{self.file_path.name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            success = self.fs.delete_file(self.file_path)
            if success:
                self.file_deleted.emit(self.file_path)


class FileDropZoneSection(QFrame):
    """Файловая секция (01_Task, 02_Workspace, 03_Submission) с поддержкой Drag-and-Drop."""

    files_changed = Signal()
    report_requested = Signal()
    zip_requested = Signal()

    def __init__(
        self,
        section_code: str,
        section_title: str,
        section_desc: str,
        folder_path: Path,
        fs: FSManager,
        theme: dict,
        is_dark: bool = True,
        is_workspace_section: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.section_code = section_code
        self.section_title = section_title
        self.section_desc = section_desc
        self.folder_path = Path(folder_path)
        self.fs = fs
        self.theme = theme
        self.is_dark = is_dark
        self.is_workspace_section = is_workspace_section

        self.is_drag_active = False

        # Включаем прием перетаскиваемых файлов
        self.setAcceptDrops(True)

        self._init_ui()
        self.refresh_files()

    def _init_ui(self) -> None:
        self.setObjectName("dropZoneSection")
        self.setMinimumWidth(0)
        self._apply_frame_style(is_drag=False)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(10)

        # Шапка секции
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Иконка секции
        icon_map = {
            "01_Task": "description",
            "02_Workspace": "code",
            "03_Submission": "send",
        }
        sec_icon = icon_map.get(self.section_code, "folder")
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_material_icon(sec_icon, color=self.theme.get("primary", "#8AB4F8"), size=18).pixmap(18, 18))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        header_layout.addWidget(icon_lbl)

        # Заголовки
        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        self.title_label = QLabel(f"{self.section_code}")
        self.title_label.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {self.theme.get('text_primary', '#FFFFFF')}; background: transparent; border: none;"
        )
        title_box.addWidget(self.title_label)

        self.desc_label = QLabel(self.section_desc)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet(
            f"font-size: 10px; color: {self.theme.get('text_secondary', '#C4C7D0')}; background: transparent; border: none;"
        )
        title_box.addWidget(self.desc_label)
        header_layout.addLayout(title_box, 1)

        # Бейдж количества файлов
        self.count_badge = QLabel("0")
        self.count_badge.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                color: {self.theme.get('primary', '#8AB4F8')};
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 700;
                border: none;
            }}
            """
        )
        header_layout.addWidget(self.count_badge)

        self.main_layout.addLayout(header_layout)

        # Контейнер для списка файлов
        self.files_container = QWidget()
        self.files_container.setStyleSheet("background: transparent; border: none;")
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setContentsMargins(0, 2, 0, 2)
        self.files_layout.setSpacing(6)
        self.main_layout.addWidget(self.files_container)

        # Панель быстрых действий (кнопки)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(5)

        # Кнопка «+ Добавить файл»
        add_btn = QPushButton("Файл")
        add_btn.setIcon(get_material_icon("add", color=self.theme.get("primary", "#8AB4F8"), size=14))
        add_btn.setToolTip("Добавить файлы в эту секцию")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedHeight(28)
        btn_hover_bg = "rgba(255, 255, 255, 0.20)" if self.is_dark else "rgba(0, 0, 0, 0.08)"
        add_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                color: {self.theme.get('primary', '#8AB4F8')};
                font-size: 11px;
                font-weight: 600;
                border-radius: 14px;
                padding: 0 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {btn_hover_bg};
            }}
            """
        )
        add_btn.clicked.connect(self._choose_and_add_files)
        actions_layout.addWidget(add_btn)

        # Кнопка «Папка» (открыть в Проводнике)
        open_folder_btn = QPushButton("Папка")
        open_folder_btn.setIcon(get_material_icon("folder_open", color=self.theme.get("text_secondary", "#C4C7D0"), size=14))
        open_folder_btn.setToolTip("Открыть папку в Проводнике Windows")
        open_folder_btn.setCursor(Qt.PointingHandCursor)
        open_folder_btn.setFixedHeight(28)
        open_folder_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme.get('text_secondary', '#C4C7D0')};
                font-size: 11px;
                font-weight: 600;
                border-radius: 14px;
                padding: 0 6px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {btn_hover_bg};
                color: {self.theme.get('text_primary', '#FFFFFF')};
            }}
            """
        )
        open_folder_btn.clicked.connect(lambda: self.fs.open_path_in_explorer(self.folder_path))
        actions_layout.addWidget(open_folder_btn)

        # Если это секция 02_Workspace — добавляем кнопку «VS Code»
        if self.is_workspace_section:
            vscode_btn = QPushButton("VS Code")
            vscode_btn.setIcon(get_material_icon("code", color=self.theme.get("primary", "#8AB4F8"), size=14))
            vscode_btn.setToolTip("Открыть рабочую папку в редакторе VS Code")
            vscode_btn.setCursor(Qt.PointingHandCursor)
            vscode_btn.setFixedHeight(28)
            vscode_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.theme.get('primary', '#8AB4F8')};
                    font-size: 11px;
                    font-weight: 600;
                    border-radius: 14px;
                    padding: 0 6px;
                    border: 1px solid {self.theme.get('primary', '#8AB4F8')};
                }}
                QPushButton:hover {{
                    background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                }}
                """
            )
            vscode_btn.clicked.connect(lambda: self.fs.open_in_vscode(self.folder_path))
            actions_layout.addWidget(vscode_btn)

        actions_layout.addStretch()
        self.main_layout.addLayout(actions_layout)

        # Если это секция 03_Submission — добавляем второй ряд быстрых действий «Отчет» и «ZIP»
        if self.section_code == "03_Submission":
            sub_actions_layout = QHBoxLayout()
            sub_actions_layout.setSpacing(6)

            report_btn = QPushButton("Отчет .docx")
            report_btn.setIcon(get_material_icon("description", color=self.theme.get("primary", "#8AB4F8"), size=14))
            report_btn.setToolTip("Создать отчет по шаблону .docx с титульным листом")
            report_btn.setCursor(Qt.PointingHandCursor)
            report_btn.setFixedHeight(28)
            report_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.theme.get('primary', '#8AB4F8')};
                    font-size: 11px;
                    font-weight: 600;
                    border-radius: 14px;
                    padding: 0 8px;
                    border: 1px solid {self.theme.get('primary', '#8AB4F8')};
                }}
                QPushButton:hover {{
                    background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                }}
                """
            )
            report_btn.clicked.connect(self.report_requested.emit)
            sub_actions_layout.addWidget(report_btn)

            zip_btn = QPushButton("ZIP архив")
            zip_btn.setIcon(get_material_icon("archive", color=self.theme.get("primary", "#8AB4F8"), size=14))
            zip_btn.setToolTip("Упаковать файлы сдачи в ZIP-архив и скопировать путь в буфер")
            zip_btn.setCursor(Qt.PointingHandCursor)
            zip_btn.setFixedHeight(28)
            zip_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.theme.get('primary', '#8AB4F8')};
                    font-size: 11px;
                    font-weight: 600;
                    border-radius: 14px;
                    padding: 0 8px;
                    border: 1px solid {self.theme.get('primary', '#8AB4F8')};
                }}
                QPushButton:hover {{
                    background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                }}
                """
            )
            zip_btn.clicked.connect(self.zip_requested.emit)
            sub_actions_layout.addWidget(zip_btn)

            sub_actions_layout.addStretch()
            self.main_layout.addLayout(sub_actions_layout)
        self.main_layout.addLayout(actions_layout)

    def _apply_frame_style(self, is_drag: bool = False) -> None:
        card_bg = self.theme.get("card_bg", "rgba(255, 255, 255, 0.05)")
        if is_drag:
            primary = self.theme.get("primary", "#8AB4F8")
            self.setStyleSheet(
                f"""
                QFrame#dropZoneSection {{
                    background-color: {card_bg};
                    border: 2px dashed {primary};
                    border-radius: 18px;
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                QFrame#dropZoneSection {{
                    background-color: {card_bg};
                    border: none;
                    border-radius: 18px;
                }}
                """
            )

    # ==========================================================================
    # Drag-and-Drop события
    # ==========================================================================

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Проверка наличия локальных файлов при перетаскивании в зону."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.is_drag_active = True
            self._apply_frame_style(is_drag=True)
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self.is_drag_active = False
        self._apply_frame_style(is_drag=False)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """Копирование перетащенных файлов в соответствующую подпапку."""
        self.is_drag_active = False
        self._apply_frame_style(is_drag=False)

        urls = event.mimeData().urls()
        copied_any = False
        for url in urls:
            local_path = url.toLocalFile()
            if local_path and os.path.exists(local_path):
                res = self.fs.copy_file_to_subfolder(Path(local_path), self.folder_path)
                if res:
                    copied_any = True

        if copied_any:
            self.refresh_files()
            self.files_changed.emit()

        event.acceptProposedAction()

    # ==========================================================================
    # Обновление списка файлов
    # ==========================================================================

    def refresh_files(self) -> None:
        """Очищает и перерисовывает элементы файлов в секции."""
        while self.files_layout.count() > 0:
            child = self.files_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        files: List[Path] = []
        if self.folder_path.exists() and self.folder_path.is_dir():
            try:
                files = sorted(
                    [p for p in self.folder_path.iterdir() if p.is_file()],
                    key=lambda p: p.name.lower(),
                )
            except Exception:
                files = []

        self.count_badge.setText(str(len(files)))

        if not files:
            empty_hint = QLabel("Перетащите файлы сюда или нажмите «+ Файл»")
            empty_hint.setWordWrap(True)
            empty_hint.setMinimumWidth(0)
            empty_hint.setAlignment(Qt.AlignCenter)
            empty_hint.setStyleSheet(
                f"""
                QLabel {{
                    color: {self.theme.get('text_secondary', '#C4C7D0')};
                    font-size: 11px;
                    font-style: italic;
                    padding: 12px 6px;
                    border: 1px dashed {'rgba(255, 255, 255, 0.12)' if self.is_dark else 'rgba(0, 0, 0, 0.12)'};
                    border-radius: 10px;
                    background: transparent;
                }}
                """
            )
            self.files_layout.addWidget(empty_hint)
        else:
            for f in files:
                item = FileItemWidget(f, self.fs, self.theme, is_dark=self.is_dark)
                item.file_deleted.connect(self._on_file_deleted)
                self.files_layout.addWidget(item)

    def _choose_and_add_files(self) -> None:
        """Диалог выбора файлов для добавления в секцию."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            f"Выберите файлы для добавления в {self.section_code}",
            "",
            "Все файлы (*.*)",
        )
        if files:
            for f in files:
                self.fs.copy_file_to_subfolder(Path(f), self.folder_path)
            self.refresh_files()
            self.files_changed.emit()

    def _on_file_deleted(self, deleted_path: Path) -> None:
        self.refresh_files()
        self.files_changed.emit()


class SubtaskItemWidget(QFrame):
    """Строка отдельной подзадачи чек-листа с чекбоксом и кнопкой удаления."""

    toggled = Signal(int, bool)
    deleted = Signal(int)

    def __init__(
        self,
        subtask_id: int,
        title: str,
        is_done: bool,
        theme: dict,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.subtask_id = subtask_id
        self.subtask_title = title
        self.is_done = is_done
        self.theme = theme
        self.is_dark = is_dark

        self._init_ui()

    def _init_ui(self) -> None:
        self.setMinimumWidth(0)
        self.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        # 1. Чекбокс индикатор (компактный, без встроенного текста)
        self.checkbox = QCheckBox()
        self.checkbox.setFixedWidth(20)
        self.checkbox.setChecked(self.is_done)
        self.checkbox.setCursor(Qt.PointingHandCursor)
        self._update_checkbox_style()
        self.checkbox.toggled.connect(self._on_toggled)
        layout.addWidget(self.checkbox)

        # 2. Метка текста с поддержкой переноса строк (WordWrap)
        self.title_label = QLabel(self.subtask_title)
        self.title_label.setWordWrap(True)
        self.title_label.setCursor(Qt.PointingHandCursor)
        self.title_label.setMinimumWidth(0)
        self._update_title_label_style()
        self.title_label.mousePressEvent = lambda e: self.checkbox.toggle()
        layout.addWidget(self.title_label, 1)

        # 3. Кнопка удаления
        del_btn = QPushButton()
        del_btn.setIcon(get_material_icon("close", color=self.theme.get("text_secondary", "#C4C7D0"), size=13))
        del_btn.setToolTip("Удалить этап")
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.PointingHandCursor)
        hover_bg = "rgba(239, 68, 68, 0.18)"
        del_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            """
        )
        del_btn.clicked.connect(lambda: self.deleted.emit(self.subtask_id))
        layout.addWidget(del_btn)

    def _update_checkbox_style(self) -> None:
        primary = self.theme.get("primary", "#8AB4F8")
        indicator_border = primary if self.checkbox.isChecked() else self.theme.get("text_secondary", "#C4C7D0")
        indicator_bg = primary if self.checkbox.isChecked() else "transparent"

        self.checkbox.setStyleSheet(
            f"""
            QCheckBox {{
                spacing: 0px;
                background: transparent;
                border: none;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1.5px solid {indicator_border};
                background: {indicator_bg};
            }}
            QCheckBox::indicator:hover {{
                border-color: {primary};
            }}
            """
        )

    def _update_title_label_style(self) -> None:
        text_color = self.theme.get("text_muted", "#9DA1AA") if self.is_done else self.theme.get("text_primary", "#FFFFFF")
        font = self.title_label.font()
        font.setPointSize(10)
        font.setStrikeOut(self.is_done)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(
            f"color: {text_color}; font-size: 11px; font-weight: 500; background: transparent; border: none;"
        )

    def _on_toggled(self, checked: bool) -> None:
        self.is_done = checked
        self._update_checkbox_style()
        self._update_title_label_style()
        self.toggled.emit(self.subtask_id, checked)


class TaskInspectorWidget(QWidget):
    """Полный инспектор выбранной работы с метаданными, статусом, файловыми зонами и заметками."""

    task_status_changed = Signal(int, str)
    task_progress_changed = Signal(int, int)
    task_files_changed = Signal(int)

    def __init__(
        self,
        task: Task,
        subject: Optional[Subject],
        db: Database,
        fs: FSManager,
        theme: dict,
        current_theme_mode: str = "dark",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.task = task
        self.subject = subject
        self.db = db
        self.fs = fs
        self.theme = theme
        self.current_theme_mode = current_theme_mode
        self.is_dark = current_theme_mode == "dark"

        self._init_ui()

    def _init_ui(self) -> None:
        self.setMinimumWidth(0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # ======================================================================
        # Карточка 1: Шапка задачи и метаданные
        # ======================================================================
        info_card = QFrame()
        info_card.setMinimumWidth(0)
        info_card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.theme.get('card_bg', '#1E1B2E')};
                border-radius: 20px;
                border: none;
            }}
            """
        )
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(14, 14, 14, 14)
        info_layout.setSpacing(8)

        # Префикс типа и номер
        type_prefix = {
            "Практическая": "ПР",
            "Лабораторная": "ЛР",
            "Курсовая": "КР",
            "Реферат": "РЕФ",
        }.get(self.task.type, self.task.type)

        header_lbl = QLabel(f"{type_prefix} №{self.task.number}")
        header_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {self.theme.get('primary', '#8AB4F8')}; border: none; background: transparent;"
        )
        info_layout.addWidget(header_lbl)

        # Заголовок работы
        title_lbl = QLabel(self.task.title)
        title_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {self.theme.get('text_primary', '#FFFFFF')}; border: none; background: transparent;"
        )
        title_lbl.setWordWrap(True)
        info_layout.addWidget(title_lbl)

        # Предмет и Вариант
        meta_parts = []
        if self.subject:
            meta_parts.append(f"Предмет: {self.subject.short_name or self.subject.name}")
        if self.task.variant:
            meta_parts.append(f"Вариант: {self.task.variant}")
        if meta_parts:
            meta_lbl = QLabel(" • ".join(meta_parts))
            meta_lbl.setWordWrap(True)
            meta_lbl.setStyleSheet(
                f"font-size: 11px; color: {self.theme.get('text_secondary', '#C4C7D0')}; border: none; background: transparent;"
            )
            info_layout.addWidget(meta_lbl)

        # Разделитель
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {'rgba(255, 255, 255, 0.08)' if self.is_dark else 'rgba(0, 0, 0, 0.08)'}; max-height: 1px; border: none;")
        info_layout.addWidget(sep)

        # Выбор статуса через выпадающий список
        status_row = QHBoxLayout()
        status_lbl = QLabel("Статус:")
        status_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {self.theme.get('text_secondary', '#C4C7D0')}; border: none; background: transparent;"
        )
        status_row.addWidget(status_lbl)

        self.status_combo = QComboBox()
        self.status_combo.minimumSizeHint = lambda: QSize(100, 28)
        for code, label in STATUS_LABELS.items():
            self.status_combo.addItem(label, code)

        idx = self.status_combo.findData(self.task.status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)

        combo_bg = "rgba(255, 255, 255, 0.08)" if self.is_dark else "rgba(0, 0, 0, 0.06)"
        combo_popup_bg = self.theme.get("dialog_bg", "#1E2230") if self.is_dark else "#FFFFFF"
        combo_item_color = self.theme.get("text_primary", "#FFFFFF") if self.is_dark else self.theme.get("text_primary", "#1D1B20")
        self.status_combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {combo_bg};
                color: {self.theme.get('text_primary', '#FFFFFF')};
                border-radius: 12px;
                border: 1px solid {'rgba(255, 255, 255, 0.12)' if self.is_dark else 'rgba(0, 0, 0, 0.12)'};
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {combo_popup_bg};
                color: {combo_item_color};
                selection-background-color: {self.theme.get('secondary_container', 'rgba(168, 199, 250, 0.25)')};
                selection-color: {self.theme.get('primary', '#8AB4F8')};
                border-radius: 12px;
                border: 1px solid {'rgba(255, 255, 255, 0.12)' if self.is_dark else 'rgba(0, 0, 0, 0.12)'};
                padding: 4px;
                outline: none;
            }}
            """
        )
        self.status_combo.currentIndexChanged.connect(self._on_status_changed)
        status_row.addWidget(self.status_combo, 1)
        info_layout.addLayout(status_row)

        # Ползунок прогресса (0–100%)
        prog_row = QHBoxLayout()
        prog_row.setSpacing(8)

        self.prog_label = QLabel(f"Прогресс: {self.task.progress_percent}%")
        self.prog_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {self.theme.get('text_secondary', '#C4C7D0')}; border: none; background: transparent;"
        )
        prog_row.addWidget(self.prog_label)

        self.prog_slider = QSlider(Qt.Horizontal)
        self.prog_slider.setRange(0, 100)
        self.prog_slider.setValue(int(self.task.progress_percent or 0))
        self.prog_slider.setFixedHeight(20)
        self.prog_slider.valueChanged.connect(self._on_progress_slider_moved)
        self.prog_slider.sliderReleased.connect(self._on_progress_slider_released)
        prog_row.addWidget(self.prog_slider, 1)
        info_layout.addLayout(prog_row)

        # Дедлайн
        if self.task.deadline_date:
            _, dl_fg, _ = get_md3_urgency(
                self.task.deadline_date,
                self.task.status == STATUS_COMPLETED,
                is_dark=self.is_dark,
            )
            dl_lbl = QLabel(f"Дедлайн: {self.task.deadline_date}")
            dl_lbl.setStyleSheet(
                f"font-size: 11px; font-weight: 600; color: {dl_fg}; border: none; background: transparent;"
            )
            info_layout.addWidget(dl_lbl)

        layout.addWidget(info_card)

        # ======================================================================
        # Карточка 2: 3 файловые секции с Drag-and-Drop (01_Task, 02_Workspace, 03_Submission)
        # ======================================================================
        subj_folder = self.subject.folder_path if self.subject else ""
        subfolders = self.fs.get_task_subfolders(subj_folder, self.task.folder_path)

        # Заголовок секций
        sections_title = QLabel("ФАЙЛОВЫЕ ЗОНЫ")
        sections_title.setWordWrap(True)
        sections_title.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.theme.get('text_secondary', '#C4C7D0')}; letter-spacing: 0.8px; margin-top: 4px; border: none; background: transparent;"
        )
        layout.addWidget(sections_title)

        # 01_Task
        self.sec_task = FileDropZoneSection(
            section_code="01_Task",
            section_title="Условия и методички",
            section_desc="Методические указания и файлы заданий",
            folder_path=subfolders["task"],
            fs=self.fs,
            theme=self.theme,
            is_dark=self.is_dark,
            is_workspace_section=False,
            parent=self,
        )
        self.sec_task.files_changed.connect(self._on_files_changed)
        layout.addWidget(self.sec_task)

        # 02_Workspace
        self.sec_workspace = FileDropZoneSection(
            section_code="02_Workspace",
            section_title="Рабочие файлы и код",
            section_desc="Черновики, скрипты и исходный код",
            folder_path=subfolders["workspace"],
            fs=self.fs,
            theme=self.theme,
            is_dark=self.is_dark,
            is_workspace_section=True,
            parent=self,
        )
        self.sec_workspace.files_changed.connect(self._on_files_changed)
        layout.addWidget(self.sec_workspace)

        # 03_Submission
        self.sec_submission = FileDropZoneSection(
            section_code="03_Submission",
            section_title="Материалы к сдаче",
            section_desc="Готовые отчеты и финальные файлы",
            folder_path=subfolders["submission"],
            fs=self.fs,
            theme=self.theme,
            is_dark=self.is_dark,
            is_workspace_section=False,
            parent=self,
        )
        self.sec_submission.files_changed.connect(self._on_files_changed)
        self.sec_submission.report_requested.connect(self._on_generate_report)
        self.sec_submission.zip_requested.connect(self._on_create_zip)
        layout.addWidget(self.sec_submission)

        # ======================================================================
        # Карточка 3: Чек-лист подзадач и этапов выполнения (Шаг 4)
        # ======================================================================
        checklist_card = QFrame()
        checklist_card.setMinimumWidth(0)
        checklist_card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.theme.get('card_bg', '#1E1B2E')};
                border-radius: 18px;
                border: none;
            }}
            """
        )
        self.checklist_layout = QVBoxLayout(checklist_card)
        self.checklist_layout.setContentsMargins(14, 12, 14, 12)
        self.checklist_layout.setSpacing(8)

        # Шапка чек-листа
        cl_header_row = QHBoxLayout()
        cl_header_row.setSpacing(8)

        cl_icon = QLabel()
        cl_icon.setPixmap(get_material_icon("checklist", color=self.theme.get("primary", "#8AB4F8"), size=18).pixmap(18, 18))
        cl_icon.setStyleSheet("background: transparent; border: none;")
        cl_header_row.addWidget(cl_icon)

        cl_title = QLabel("ЧЕК-ЛИСТ")
        cl_title.setWordWrap(True)
        cl_title.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.theme.get('text_secondary', '#C4C7D0')}; letter-spacing: 0.8px; border: none; background: transparent;"
        )
        cl_header_row.addWidget(cl_title)
        cl_header_row.addStretch()

        self.cl_badge = QLabel("0/0")
        self.cl_badge.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                color: {self.theme.get('primary', '#8AB4F8')};
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 700;
                border: none;
            }}
            """
        )
        cl_header_row.addWidget(self.cl_badge)
        self.checklist_layout.addLayout(cl_header_row)

        # Контейнер для списка подзадач
        self.subtasks_container = QWidget()
        self.subtasks_container.setStyleSheet("background: transparent; border: none;")
        self.subtasks_layout = QVBoxLayout(self.subtasks_container)
        self.subtasks_layout.setContentsMargins(0, 0, 0, 0)
        self.subtasks_layout.setSpacing(4)
        self.checklist_layout.addWidget(self.subtasks_container)

        # Строка добавления новой подзадачи
        add_subtask_row = QHBoxLayout()
        add_subtask_row.setSpacing(6)

        self.new_subtask_input = QLineEdit()
        self.new_subtask_input.setMinimumWidth(50)
        self.new_subtask_input.setPlaceholderText("Новый этап (напр. Написать отчет)...")
        self.new_subtask_input.setFixedHeight(30)
        input_bg = "rgba(255, 255, 255, 0.05)" if self.is_dark else "rgba(0, 0, 0, 0.04)"
        placeholder_color = "rgba(255, 255, 255, 0.45)" if self.is_dark else "rgba(0, 0, 0, 0.40)"
        self.new_subtask_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {self.theme.get('text_primary', '#FFFFFF')};
                placeholder-text-color: {placeholder_color};
                border: none;
                border-radius: 15px;
                padding: 0 12px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.theme.get('primary', '#8AB4F8')};
            }}
            """
        )
        self.new_subtask_input.returnPressed.connect(self._on_add_subtask)
        add_subtask_row.addWidget(self.new_subtask_input, 1)

        add_subtask_btn = QPushButton()
        add_subtask_btn.setIcon(get_material_icon("add", color=self.theme.get("primary", "#8AB4F8"), size=14))
        add_subtask_btn.setToolTip("Добавить этап в чек-лист")
        add_subtask_btn.setFixedSize(30, 30)
        add_subtask_btn.setCursor(Qt.PointingHandCursor)
        add_subtask_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                border: none;
                border-radius: 15px;
            }}
            QPushButton:hover {{
                background-color: {'rgba(255, 255, 255, 0.20)' if self.is_dark else 'rgba(0, 0, 0, 0.08)'};
            }}
            """
        )
        add_subtask_btn.clicked.connect(self._on_add_subtask)
        add_subtask_row.addWidget(add_subtask_btn)

        self.checklist_layout.addLayout(add_subtask_row)
        layout.addWidget(checklist_card)

        # ======================================================================
        # Карточка 4: Заметки и замечания
        # ======================================================================
        notes_card = QFrame()
        notes_card.setMinimumWidth(0)
        notes_card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.theme.get('card_bg', '#1E1B2E')};
                border-radius: 16px;
                border: none;
            }}
            """
        )
        notes_layout = QVBoxLayout(notes_card)
        notes_layout.setContentsMargins(14, 12, 14, 12)
        notes_layout.setSpacing(6)

        notes_header = QLabel("Заметки и замечания:")
        notes_header.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.theme.get('text_secondary', '#C4C7D0')}; border: none; background: transparent;"
        )
        notes_layout.addWidget(notes_header)

        self.notes_editor = QTextEdit()
        self.notes_editor.setPlaceholderText("Введите комментарии преподавателя или заметки...")
        self.notes_editor.setFixedHeight(75)
        self.notes_editor.setText(self.task.notes or "")
        notes_bg = "rgba(255, 255, 255, 0.04)" if self.is_dark else "rgba(0, 0, 0, 0.04)"
        placeholder_color = "rgba(255, 255, 255, 0.45)" if self.is_dark else "rgba(0, 0, 0, 0.40)"
        self.notes_editor.setStyleSheet(
            f"background: {notes_bg}; color: {self.theme.get('text_primary', '#FFFFFF')}; placeholder-text-color: {placeholder_color}; border-radius: 12px; border: none; padding: 8px 10px; font-size: 12px;"
        )
        self.notes_editor.textChanged.connect(self._on_notes_changed)
        notes_layout.addWidget(self.notes_editor)
        layout.addWidget(notes_card)

        # ======================================================================
        # Карточка 4: Кнопка «Открыть всю папку работы»
        # ======================================================================
        full_dir_btn = QPushButton("Открыть всю папку")
        full_dir_btn.setIcon(get_material_icon("folder_open", color=self.theme.get("primary", "#8AB4F8"), size=16))
        full_dir_btn.setCursor(Qt.PointingHandCursor)
        full_dir_btn.setFixedHeight(38)
        full_dir_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                color: {self.theme.get('primary', '#8AB4F8')};
                border-radius: 19px;
                border: none;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {'rgba(255, 255, 255, 0.20)' if self.is_dark else 'rgba(0, 0, 0, 0.08)'};
            }}
            """
        )
        task_dir = self.fs.get_task_dir(subj_folder, self.task.folder_path)
        full_dir_btn.clicked.connect(lambda: self.fs.open_path_in_explorer(task_dir))
        layout.addWidget(full_dir_btn)

        # Загружаем чек-лист подзадач
        self._refresh_subtasks()

    def _on_status_changed(self, index: int) -> None:
        new_status = self.status_combo.currentData()
        if new_status and new_status != self.task.status:
            self.task.status = new_status
            # Если завершено — ставим 100%
            if new_status == STATUS_COMPLETED:
                self.prog_slider.setValue(100)
                self.prog_label.setText("Прогресс: 100%")
                self.db.update_task_status(self.task.id, new_status, progress_percent=100)
            else:
                self.db.update_task_status(self.task.id, new_status)
            self.task_status_changed.emit(self.task.id, new_status)

    def _on_progress_slider_moved(self, value: int) -> None:
        self.prog_label.setText(f"Прогресс: {value}%")

    def _on_progress_slider_released(self) -> None:
        val = self.prog_slider.value()
        self.task.progress_percent = val
        self.db.update_task_progress(self.task.id, val)
        self.task_progress_changed.emit(self.task.id, val)

    def _on_notes_changed(self) -> None:
        text = self.notes_editor.toPlainText()
        self.db.update_task_notes(self.task.id, text)

    def _on_files_changed(self) -> None:
        self.task_files_changed.emit(self.task.id)

    def _on_generate_report(self) -> None:
        """Создает отчет по шаблону docx из _Templates в 03_Submission."""
        student_name = self.db.get_setting("student_name", "") or "Иванов Иван Иванович"
        student_group = self.db.get_setting("student_group", "") or "ИВТ-21"
        subj_name = self.subject.name if self.subject else "Дисциплина"
        subj_folder = self.subject.folder_path if self.subject else ""

        try:
            report_path = self.fs.generate_task_report(
                subject_name=subj_name,
                task_number=self.task.number,
                task_type=self.task.type,
                task_title=self.task.title,
                student_name=student_name,
                student_group=student_group,
                subject_folder=subj_folder,
                task_folder=self.task.folder_path,
                variant=self.task.variant,
            )
            self.sec_submission.refresh_files()
            self.task_files_changed.emit(self.task.id)
            QToolTip.showText(
                QCursor.pos(),
                f"Отчет успешно сформирован:\n{report_path.name}",
                self,
            )
        except Exception as e:
            QToolTip.showText(QCursor.pos(), f"Ошибка генерации отчета: {e}", self)

    def _on_create_zip(self) -> None:
        """Упаковывает файлы сдачи в zip-архив и копирует путь к нему."""
        subj_folder = self.subject.folder_path if self.subject else ""
        subfolders = self.fs.get_task_subfolders(subj_folder, self.task.folder_path)
        sub_dir = subfolders["submission"]
        files = [f for f in sub_dir.iterdir() if f.is_file() and not f.name.endswith(".zip")]
        if not files:
            QToolTip.showText(
                QCursor.pos(),
                "Секция сдачи пуста!\nСначала добавьте файлы или нажмите «Отчет».",
                self,
            )
            return

        try:
            type_pfx = {"Практическая": "ПР", "Лабораторная": "ЛР", "Курсовая": "КР", "Реферат": "РЕФ"}.get(self.task.type, "Работа")
            zip_filename = f"{type_pfx}{self.task.number}_submission.zip"
            zip_path = self.fs.create_submission_zip(
                subject_folder=subj_folder,
                task_folder=self.task.folder_path,
                zip_filename=zip_filename,
            )
            if zip_path and zip_path.exists():
                app = QApplication.instance()
                if app:
                    app.clipboard().setText(str(zip_path.resolve()))
                self.sec_submission.refresh_files()
                self.task_files_changed.emit(self.task.id)
                QToolTip.showText(
                    QCursor.pos(),
                    f"Архив готов, путь скопирован в буфер:\n{zip_path.name}",
                    self,
                )
        except Exception as e:
            QToolTip.showText(QCursor.pos(), f"Ошибка упаковки ZIP: {e}", self)

    def _refresh_subtasks(self) -> None:
        """Загружает список подзадач из БД и отрисовывает их."""
        while self.subtasks_layout.count() > 0:
            child = self.subtasks_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        subtasks = self.db.get_subtasks(self.task.id)
        if not subtasks:
            empty_box = QWidget()
            empty_box.setStyleSheet("background: transparent; border: none;")
            eb_layout = QVBoxLayout(empty_box)
            eb_layout.setContentsMargins(0, 4, 0, 4)
            eb_layout.setSpacing(6)

            hint = QLabel("Этапы работы не добавлены")
            hint.setAlignment(Qt.AlignCenter)
            hint.setStyleSheet(
                f"color: {self.theme.get('text_secondary', '#C4C7D0')}; font-size: 10px; font-style: italic; border: none; background: transparent;"
            )
            eb_layout.addWidget(hint)

            tpl_btn = QPushButton("Заполнить типовой план (4 этапа)")
            tpl_btn.setCursor(Qt.PointingHandCursor)
            tpl_btn.setFixedHeight(26)
            tpl_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.theme.get('primary', '#8AB4F8')};
                    font-size: 10px;
                    font-weight: 600;
                    border: 1px dashed {self.theme.get('primary', '#8AB4F8')};
                    border-radius: 13px;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                }}
                """
            )
            tpl_btn.clicked.connect(self._on_add_default_plan)
            eb_layout.addWidget(tpl_btn)

            self.subtasks_layout.addWidget(empty_box)
            self.cl_badge.setText("0/0")
            return

        done_cnt = 0
        for s in subtasks:
            if s["is_done"]:
                done_cnt += 1
            item = SubtaskItemWidget(
                subtask_id=s["id"],
                title=s["title"],
                is_done=bool(s["is_done"]),
                theme=self.theme,
                is_dark=self.is_dark,
                parent=self,
            )
            item.toggled.connect(self._on_subtask_toggled)
            item.deleted.connect(self._on_subtask_deleted)
            self.subtasks_layout.addWidget(item)

        total = len(subtasks)
        pct = round((done_cnt / total) * 100) if total > 0 else 0
        self.cl_badge.setText(f"{done_cnt}/{total} ({pct}%)")

    def _on_add_default_plan(self) -> None:
        """Добавляет типовые 4 этапа выполнения практической работы."""
        default_steps = [
            "Изучить методические указания и условие",
            "Написать исходный код и скрипты",
            "Оформить отчет по шаблону docx",
            "Защитить работу перед преподавателем",
        ]
        for step in default_steps:
            self.db.add_subtask(self.task.id, step)
        self._refresh_subtasks()
        self._sync_progress_from_subtasks()

    def _on_add_subtask(self) -> None:
        text = self.new_subtask_input.text().strip()
        if not text:
            return
        self.db.add_subtask(self.task.id, text)
        self.new_subtask_input.clear()
        self._refresh_subtasks()
        self._sync_progress_from_subtasks()

    def _on_subtask_toggled(self, subtask_id: int, is_done: bool) -> None:
        self.db.set_subtask_done(subtask_id, is_done)
        self._refresh_subtasks()
        self._sync_progress_from_subtasks()

    def _on_subtask_deleted(self, subtask_id: int) -> None:
        self.db.delete_subtask(subtask_id)
        self._refresh_subtasks()
        self._sync_progress_from_subtasks()

    def _sync_progress_from_subtasks(self) -> None:
        """Синхронизирует процент выполнения работы с чек-листом подзадач."""
        subtasks = self.db.get_subtasks(self.task.id)
        if not subtasks:
            return
        done_cnt = sum(1 for s in subtasks if s["is_done"])
        new_pct = round((done_cnt / len(subtasks)) * 100)
        self.prog_slider.setValue(new_pct)
        self.prog_label.setText(f"Прогресс: {new_pct}%")
        self.task.progress_percent = new_pct
        self.db.update_task_progress(self.task.id, new_pct)

        if new_pct == 100 and self.task.status != STATUS_COMPLETED:
            self.task.status = STATUS_COMPLETED
            idx = self.status_combo.findData(STATUS_COMPLETED)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)
            self.db.update_task_status(self.task.id, STATUS_COMPLETED, progress_percent=100)
            self.task_status_changed.emit(self.task.id, STATUS_COMPLETED)
        elif new_pct > 0 and self.task.status == "NOT_STARTED":
            self.task.status = "IN_PROGRESS"
            idx = self.status_combo.findData("IN_PROGRESS")
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)
            self.db.update_task_status(self.task.id, "IN_PROGRESS")
            self.task_status_changed.emit(self.task.id, "IN_PROGRESS")

        self.task_progress_changed.emit(self.task.id, new_pct)


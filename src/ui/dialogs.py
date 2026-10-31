"""Диалоговые окна в стилистике Google Material Design 3 Expressive.
Zero-Borders, капсульные поля ввода, тональные поверхности, Material Design Icons и окно настроек.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from PySide6.QtCore import QDateTime, QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..database import (
    Database,
    EXAM_TYPES,
    STATUS_LABELS,
    Subject,
    TASK_TYPES,
)
from .cards import ThemeSwatchButton
from .icons import get_material_icon
from .theme import (
    DEFAULT_THEME,
    MD3_TEXT_PRIMARY,
    MD3_TEXT_SECONDARY,
    PIXEL_THEMES,
    SUBJECT_PRESET_COLORS_MD3,
    get_theme,
)


class SettingsDialog(QDialog):
    """
    Диалог настроек приложения в стиле Google Material Design 3 Expressive.
    Содержит переключение светлой/темной темы и палитр Google Pixel Monet,
    управление корневой директорией и статус системных интеграций.
    """

    def __init__(
        self,
        main_window: QWidget,
        theme_key: str = DEFAULT_THEME,
        theme_mode: str = "dark",
    ) -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.theme_key = theme_key
        self.theme_mode = theme_mode if theme_mode in ("dark", "light") else "dark"
        self.theme: Dict[str, Any] = get_theme(theme_key, mode=self.theme_mode)
        self.theme_swatches: Dict[str, ThemeSwatchButton] = {}

        self.setWindowTitle("Настройки — UniVault")
        self.setMinimumWidth(520)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(16)

        # 1. Заголовок диалога
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        self.header_icon = QLabel()
        header_row.addWidget(self.header_icon)

        self.header_title = QLabel("Настройки")
        header_row.addWidget(self.header_title)
        header_row.addStretch()

        layout.addLayout(header_row)

        # 2. Секция: Режим темы (Тёмная / Светлая)
        self.mode_card = QFrame()
        mode_layout = QVBoxLayout(self.mode_card)
        mode_layout.setContentsMargins(18, 14, 18, 14)
        mode_layout.setSpacing(10)

        mode_title_row = QHBoxLayout()
        mode_title_row.setSpacing(8)
        self.mode_icon = QLabel()
        mode_title_row.addWidget(self.mode_icon)

        self.mode_sec_title = QLabel("РЕЖИМ ОФОРМЛЕНИЯ")
        mode_title_row.addWidget(self.mode_sec_title)
        mode_title_row.addStretch()
        mode_layout.addLayout(mode_title_row)

        mode_buttons_row = QHBoxLayout()
        mode_buttons_row.setSpacing(10)

        self.dark_mode_btn = QPushButton("Тёмная")
        self.dark_mode_btn.setCursor(Qt.PointingHandCursor)
        self.dark_mode_btn.setFixedHeight(38)
        self.dark_mode_btn.clicked.connect(lambda: self._on_mode_toggled("dark"))
        mode_buttons_row.addWidget(self.dark_mode_btn, 1)

        self.light_mode_btn = QPushButton("Светлая")
        self.light_mode_btn.setCursor(Qt.PointingHandCursor)
        self.light_mode_btn.setFixedHeight(38)
        self.light_mode_btn.clicked.connect(lambda: self._on_mode_toggled("light"))
        mode_buttons_row.addWidget(self.light_mode_btn, 1)

        mode_layout.addLayout(mode_buttons_row)
        layout.addWidget(self.mode_card)

        # 3. Секция: Темы оформления Google Pixel Monet
        self.theme_card = QFrame()
        theme_layout = QVBoxLayout(self.theme_card)
        theme_layout.setContentsMargins(18, 14, 18, 14)
        theme_layout.setSpacing(10)

        theme_title_row = QHBoxLayout()
        theme_title_row.setSpacing(8)
        self.palette_icon = QLabel()
        theme_title_row.addWidget(self.palette_icon)

        self.theme_sec_title = QLabel("ЦВЕТОВАЯ ПАЛИТРА (MONET ENGINE)")
        theme_title_row.addWidget(self.theme_sec_title)
        theme_title_row.addStretch()
        theme_layout.addLayout(theme_title_row)

        self.theme_desc = QLabel("Выберите акцентную палитру Google Pixel — переход сопровождается матовой волновой рябью:")
        self.theme_desc.setWordWrap(True)
        theme_layout.addWidget(self.theme_desc)

        # Ряд круглых свотчей с субпиксельным сглаживанием
        swatches_row = QHBoxLayout()
        swatches_row.setSpacing(10)

        for key, pdata in PIXEL_THEMES.items():
            palette = get_theme(key, mode=self.theme_mode)
            is_active = (key == self.theme_key)
            swatch_btn = ThemeSwatchButton(
                theme_key=key,
                swatch_color=palette["swatch"],
                is_selected=is_active,
                theme_name=palette["name"],
                is_dark=(self.theme_mode == "dark"),
                parent=self,
            )
            swatch_btn.clicked.connect(self._on_swatch_clicked)
            self.theme_swatches[key] = swatch_btn
            swatches_row.addWidget(swatch_btn)

        swatches_row.addStretch()
        theme_layout.addLayout(swatches_row)

        self.theme_status_label = QLabel()
        theme_layout.addWidget(self.theme_status_label)

        layout.addWidget(self.theme_card)

        # 4. Секция: Рабочая область Workspace
        self.ws_card = QFrame()
        ws_layout = QVBoxLayout(self.ws_card)
        ws_layout.setContentsMargins(18, 14, 18, 14)
        ws_layout.setSpacing(10)

        ws_title_row = QHBoxLayout()
        ws_title_row.setSpacing(8)
        self.folder_icon = QLabel()
        ws_title_row.addWidget(self.folder_icon)

        self.ws_sec_title = QLabel("РАБОЧАЯ ОБЛАСТЬ (WORKSPACE)")
        ws_title_row.addWidget(self.ws_sec_title)
        ws_title_row.addStretch()
        ws_layout.addLayout(ws_title_row)

        current_root = str(self.main_window.fs.root_path) if hasattr(self.main_window, "fs") else ""
        self.ws_path_label = QLabel(current_root)
        self.ws_path_label.setWordWrap(True)
        ws_layout.addWidget(self.ws_path_label)

        ws_buttons_row = QHBoxLayout()
        ws_buttons_row.setSpacing(10)

        self.open_btn = QPushButton("Открыть в проводнике")
        self.open_btn.setFixedHeight(36)
        self.open_btn.setCursor(Qt.PointingHandCursor)
        if hasattr(self.main_window, "fs"):
            self.open_btn.clicked.connect(lambda: self.main_window.fs.open_path_in_explorer(self.main_window.fs.root_path))
        ws_buttons_row.addWidget(self.open_btn)

        ws_buttons_row.addStretch()
        ws_layout.addLayout(ws_buttons_row)

        layout.addWidget(self.ws_card)

        # 5. Секция: Данные студента (для автозаполнения отчетов)
        self.student_card = QFrame()
        st_layout = QVBoxLayout(self.student_card)
        st_layout.setContentsMargins(18, 14, 18, 14)
        st_layout.setSpacing(10)

        st_title_row = QHBoxLayout()
        st_title_row.setSpacing(8)
        self.student_icon = QLabel()
        st_title_row.addWidget(self.student_icon)

        self.student_sec_title = QLabel("ДАННЫЕ СТУДЕНТА (ДЛЯ АВТОЗАПОЛНЕНИЯ ОТЧЕТОВ)")
        st_title_row.addWidget(self.student_sec_title)
        st_title_row.addStretch()
        st_layout.addLayout(st_title_row)

        curr_name = self.main_window.db.get_setting("student_name", "") if hasattr(self.main_window, "db") else ""
        curr_grp = self.main_window.db.get_setting("student_group", "") if hasattr(self.main_window, "db") else ""

        st_form = QFormLayout()
        st_form.setSpacing(8)

        self.student_name_label = QLabel("ФИО:")
        self.student_name_label.setStyleSheet("font-size: 12px; font-weight: 500; border: none; background: transparent;")
        self.student_name_input = QLineEdit(curr_name or "")
        self.student_name_input.setPlaceholderText("Иванов Иван Иванович")
        self.student_name_input.setFixedHeight(34)
        st_form.addRow(self.student_name_label, self.student_name_input)

        self.student_group_label = QLabel("Группа:")
        self.student_group_label.setStyleSheet("font-size: 12px; font-weight: 500; border: none; background: transparent;")
        self.student_group_input = QLineEdit(curr_grp or "")
        self.student_group_input.setPlaceholderText("ИВТ-21")
        self.student_group_input.setFixedHeight(34)
        st_form.addRow(self.student_group_label, self.student_group_input)

        st_layout.addLayout(st_form)
        layout.addWidget(self.student_card)

        # 6. Кнопка «Готово»
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        self.close_btn = QPushButton("Готово")
        self.close_btn.setFixedHeight(44)
        self.close_btn.setMinimumWidth(130)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(self.close_btn)

        layout.addLayout(bottom_row)

        # Применяем все стили диалога
        self._refresh_dialog_theme()

    def accept(self) -> None:
        """Сохраняет настройки студента при закрытии окна."""
        if hasattr(self, "student_name_input") and hasattr(self.main_window, "db"):
            self.main_window.db.set_setting("student_name", self.student_name_input.text().strip())
        if hasattr(self, "student_group_input") and hasattr(self.main_window, "db"):
            self.main_window.db.set_setting("student_group", self.student_group_input.text().strip())
        super().accept()

    def _refresh_dialog_theme(self) -> None:
        """Перекрашивает диалог под текущую палитру и выбранный режим (Dark/Light)."""
        self.theme = get_theme(self.theme_key, mode=self.theme_mode)
        is_dark = (self.theme_mode == "dark")

        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {self.theme.get('dialog_bg', '#1A1D24')};
                border-radius: 28px;
                border: none;
            }}
            QLabel {{
                color: {self.theme['text_primary']};
                font-size: 13px;
                font-weight: 500;
                border: none;
                background: transparent;
            }}
            """
        )

        self.header_icon.setPixmap(get_material_icon("settings", color=self.theme["primary"], size=24).pixmap(24, 24))
        self.header_title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {self.theme['text_primary']}; border: none; background: transparent;"
        )

        card_bg = self.theme.get("dialog_card", "rgba(255, 255, 255, 0.05)")
        card_style = f"QFrame {{ background-color: {card_bg}; border-radius: 20px; border: none; }}"
        self.mode_card.setStyleSheet(card_style)
        self.theme_card.setStyleSheet(card_style)
        self.ws_card.setStyleSheet(card_style)
        if hasattr(self, "student_card"):
            self.student_card.setStyleSheet(card_style)

        if hasattr(self, "student_icon"):
            self.student_icon.setStyleSheet("background: transparent; border: none;")
            self.student_icon.setPixmap(get_material_icon("badge", color=self.theme["primary"], size=18).pixmap(18, 18))
        if hasattr(self, "student_sec_title"):
            self.student_sec_title.setStyleSheet(
                f"font-size: 11px; font-weight: 700; color: {self.theme['text_secondary']}; letter-spacing: 1px; border: none; background: transparent;"
            )
        if hasattr(self, "student_name_input"):
            inp_bg = "rgba(0,0,0,0.30)" if is_dark else "rgba(0,0,0,0.06)"
            st_inp_style = f"""
                QLineEdit {{
                    font-size: 12px;
                    color: {self.theme['text_primary']};
                    background: {inp_bg};
                    padding: 0 12px;
                    border-radius: 12px;
                    border: none;
                }}
                QLineEdit:focus {{
                    border: 1px solid {self.theme['primary']};
                }}
            """
            self.student_name_input.setStyleSheet(st_inp_style)
            self.student_group_input.setStyleSheet(st_inp_style)

        self.mode_icon.setStyleSheet("background: transparent; border: none;")
        self.mode_icon.setPixmap(get_material_icon("tune", color=self.theme["primary"], size=18).pixmap(18, 18))
        self.mode_sec_title.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.theme['text_secondary']}; letter-spacing: 1px; border: none; background: transparent;"
        )

        self.palette_icon.setStyleSheet("background: transparent; border: none;")
        self.palette_icon.setPixmap(get_material_icon("palette", color=self.theme["primary"], size=18).pixmap(18, 18))
        self.theme_sec_title.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.theme['text_secondary']}; letter-spacing: 1px; border: none; background: transparent;"
        )
        self.theme_desc.setStyleSheet(f"font-size: 12px; color: {self.theme['text_secondary']}; border: none; background: transparent;")

        self.folder_icon.setStyleSheet("background: transparent; border: none;")
        self.folder_icon.setPixmap(get_material_icon("folder", color=self.theme["primary"], size=18).pixmap(18, 18))
        self.ws_sec_title.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.theme['text_secondary']}; letter-spacing: 1px; border: none; background: transparent;"
        )

        path_bg = "rgba(0,0,0,0.30)" if is_dark else "rgba(0,0,0,0.06)"
        self.ws_path_label.setStyleSheet(
            f"font-size: 12px; color: {self.theme['text_primary']}; background: {path_bg}; padding: 8px 12px; border-radius: 12px;"
        )

        # Стили кнопок переключения режима
        active_btn_style = f"""
            QPushButton {{
                background-color: {self.theme['primary']};
                color: {self.theme['on_primary']};
                border-radius: 19px;
                border: none;
                font-size: 13px;
                font-weight: 700;
                padding: 0 16px;
            }}
        """
        inactive_btn_hover = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.08)"
        inactive_btn_style = f"""
            QPushButton {{
                background-color: {self.theme['secondary_container']};
                color: {self.theme['text_secondary']};
                border-radius: 19px;
                border: none;
                font-size: 13px;
                font-weight: 500;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {inactive_btn_hover};
                color: {self.theme['text_primary']};
            }}
        """

        if is_dark:
            self.dark_mode_btn.setStyleSheet(active_btn_style)
            self.dark_mode_btn.setIcon(get_material_icon("dark_mode", color=self.theme["on_primary"], size=18))
            self.light_mode_btn.setStyleSheet(inactive_btn_style)
            self.light_mode_btn.setIcon(get_material_icon("light_mode", color=self.theme["text_secondary"], size=18))
        else:
            self.light_mode_btn.setStyleSheet(active_btn_style)
            self.light_mode_btn.setIcon(get_material_icon("light_mode", color=self.theme["on_primary"], size=18))
            self.dark_mode_btn.setStyleSheet(inactive_btn_style)
            self.dark_mode_btn.setIcon(get_material_icon("dark_mode", color=self.theme["text_secondary"], size=18))

        # Обновляем свотчи
        for key, swatch in self.theme_swatches.items():
            palette = get_theme(key, mode=self.theme_mode)
            swatch.set_swatch_color(palette["swatch"])
            swatch.set_is_dark(is_dark)
            swatch.set_selected(key == self.theme_key)

        curr_name = self.theme.get("name", self.theme_key)
        self.theme_status_label.setText(f"Активная тема: {curr_name}")
        self.theme_status_label.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {self.theme['primary']}; border: none; background: transparent;"
        )

        open_hover_bg = "rgba(255, 255, 255, 0.22)" if is_dark else "rgba(0, 0, 0, 0.08)"
        self.open_btn.setIcon(get_material_icon("folder_open", color=self.theme["primary"], size=18))
        self.open_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme['secondary_container']};
                color: {self.theme['primary']};
                border-radius: 18px;
                border: none;
                font-size: 12px;
                font-weight: 600;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {open_hover_bg};
            }}
            """
        )

        self.close_btn.setIcon(get_material_icon("check", color=self.theme["on_primary"], size=18))
        self.close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme['primary']};
                color: {self.theme['on_primary']};
                border-radius: 22px;
                border: none;
                font-size: 14px;
                font-weight: 600;
                padding: 0 24px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get('primary_hover', self.theme['primary'])};
            }}
            """
        )

    def _on_mode_toggled(self, new_mode: str) -> None:
        """Переключает режим между Светлой и Тёмной темой."""
        if self.theme_mode == new_mode:
            return
        self.theme_mode = new_mode
        self._refresh_dialog_theme()

        if hasattr(self.main_window, "trigger_theme_transition"):
            self.main_window.trigger_theme_transition(self.theme_key, mode=self.theme_mode)
        elif hasattr(self.main_window, "set_active_theme"):
            self.main_window.set_active_theme(self.theme_key, mode=self.theme_mode)

    def _on_swatch_clicked(self, theme_key: str) -> None:
        """Обрабатывает выбор темы из настроек и запускает волновой переход в главном окне."""
        self.theme_key = theme_key
        self._refresh_dialog_theme()

        if hasattr(self.main_window, "trigger_theme_transition"):
            self.main_window.trigger_theme_transition(theme_key, mode=self.theme_mode)
        elif hasattr(self.main_window, "set_active_theme"):
            self.main_window.set_active_theme(theme_key, mode=self.theme_mode)


class AddSubjectDialog(QDialog):
    """Диалог добавления предмета в стиле MD3 Expressive (Zero Borders)."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        theme_key: str = DEFAULT_THEME,
        mode: str = "dark",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Добавить предмет")
        self.setMinimumWidth(480)
        self.theme_mode = mode if mode in ("dark", "light") else "dark"
        self.theme: Dict[str, str] = get_theme(theme_key, mode=self.theme_mode)
        self.selected_color = SUBJECT_PRESET_COLORS_MD3[0]
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {self.theme['dialog_bg']};
                border-radius: 28px;
                border: none;
            }}
            QLabel {{
                color: {self.theme['text_primary']};
                font-size: 13px;
                font-weight: 600;
                border: none;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(20)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        h_icon = QLabel()
        h_icon.setPixmap(get_material_icon("school", color=self.theme["primary"], size=22).pixmap(22, 22))
        header_row.addWidget(h_icon)

        header = QLabel("Новый учебный предмет")
        header.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {self.theme['text_primary']}; border: none; background: transparent;")
        header_row.addWidget(header)
        header_row.addStretch()
        layout.addLayout(header_row)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)

        self.name_edit = QLineEdit()
        self.name_edit.setFixedHeight(44)
        self.name_edit.setPlaceholderText("Например: Структуры и алгоритмы")
        form.addRow("Название *:", self.name_edit)

        self.short_name_edit = QLineEdit()
        self.short_name_edit.setFixedHeight(44)
        self.short_name_edit.setPlaceholderText("Например: СИАОД")
        form.addRow("Краткий тег:", self.short_name_edit)

        self.teacher_edit = QLineEdit()
        self.teacher_edit.setFixedHeight(44)
        self.teacher_edit.setPlaceholderText("Например: Иванов И.И.")
        form.addRow("Преподаватель:", self.teacher_edit)

        self.exam_combo = QComboBox()
        self.exam_combo.setFixedHeight(44)
        self.exam_combo.addItems(EXAM_TYPES)
        form.addRow("Аттестация:", self.exam_combo)

        # Выбор цвета маркера через круглые свотчи
        color_container = QWidget()
        color_layout = QHBoxLayout(color_container)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(10)

        self.color_group = QButtonGroup(self)
        self.color_buttons: List[QPushButton] = []

        for idx, color in enumerate(SUBJECT_PRESET_COLORS_MD3):
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color};
                    border-radius: 14px;
                    border: none;
                    padding: 0;
                }}
                QPushButton:checked {{
                    border: 3px solid #FFFFFF;
                }}
                """
            )
            if idx == 0:
                btn.setChecked(True)
            self.color_group.addButton(btn, idx)
            btn.clicked.connect(lambda _, c=color: self._set_color(c))
            color_layout.addWidget(btn)
            self.color_buttons.append(btn)

        color_layout.addStretch()
        form.addRow("Цвет маркера:", color_container)

        layout.addLayout(form)

        # Кнопки действий
        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        ok_btn = btn_box.button(QDialogButtonBox.Ok)
        ok_btn.setText("Создать")
        ok_btn.setIcon(get_material_icon("add", color=self.theme["on_primary"], size=18))
        ok_btn.setProperty("primary", "true")
        ok_btn.setFixedHeight(44)
        ok_btn.setCursor(Qt.PointingHandCursor)

        cancel_btn = btn_box.button(QDialogButtonBox.Cancel)
        cancel_btn.setText("Отмена")
        cancel_btn.setIcon(get_material_icon("close", color=self.theme["on_secondary"], size=18))
        cancel_btn.setFixedHeight(44)
        cancel_btn.setCursor(Qt.PointingHandCursor)

        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _set_color(self, color: str) -> None:
        self.selected_color = color

    def _validate_and_accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название учебного предмета!")
            self.name_edit.setFocus()
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "short_name": self.short_name_edit.text().strip() or None,
            "teacher_name": self.teacher_edit.text().strip() or None,
            "exam_type": self.exam_combo.currentText(),
            "color_hex": self.selected_color,
        }


class AddTaskDialog(QDialog):
    """Диалог добавления работы в стиле MD3 Expressive (Zero Borders)."""

    def __init__(
        self,
        db: Database,
        default_subject_id: Optional[int] = None,
        parent: Optional[QWidget] = None,
        theme_key: str = DEFAULT_THEME,
        mode: str = "dark",
    ) -> None:
        super().__init__(parent)
        self.db = db
        self.default_subject_id = default_subject_id
        self.theme_mode = mode if mode in ("dark", "light") else "dark"
        self.theme: Dict[str, str] = get_theme(theme_key, mode=self.theme_mode)
        self.setWindowTitle("Добавить работу")
        self.setMinimumWidth(540)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {self.theme['dialog_bg']};
                border-radius: 28px;
                border: none;
            }}
            QLabel {{
                color: {self.theme['text_primary']};
                font-size: 13px;
                font-weight: 600;
                border: none;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(20)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        t_icon = QLabel()
        t_icon.setPixmap(get_material_icon("assignment", color=self.theme["primary"], size=22).pixmap(22, 22))
        header_row.addWidget(t_icon)

        header = QLabel("Новая практическая работа")
        header.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {self.theme['text_primary']}; border: none; background: transparent;")
        header_row.addWidget(header)
        header_row.addStretch()
        layout.addLayout(header_row)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)

        # Выбор предмета
        self.subject_combo = QComboBox()
        self.subject_combo.setFixedHeight(44)
        self.subjects: List[Subject] = self.db.get_subjects()
        selected_index = 0
        for idx, subj in enumerate(self.subjects):
            tag = f" ({subj.short_name})" if subj.short_name else ""
            self.subject_combo.addItem(f"{subj.name}{tag}", userData=subj.id)
            if self.default_subject_id and subj.id == self.default_subject_id:
                selected_index = idx
        if self.subjects:
            self.subject_combo.setCurrentIndex(selected_index)
        self.subject_combo.currentIndexChanged.connect(self._update_next_number)
        form.addRow("Предмет *:", self.subject_combo)

        # Тип работы и Номер
        type_num_widget = QWidget()
        type_num_layout = QHBoxLayout(type_num_widget)
        type_num_layout.setContentsMargins(0, 0, 0, 0)
        type_num_layout.setSpacing(10)

        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(44)
        self.type_combo.addItems(TASK_TYPES)
        self.type_combo.currentIndexChanged.connect(self._update_next_number)
        type_num_layout.addWidget(self.type_combo, 2)

        self.number_spin = QSpinBox()
        self.number_spin.setFixedHeight(44)
        self.number_spin.setRange(1, 999)
        self.number_spin.setValue(1)
        type_num_layout.addWidget(QLabel("№"), 0)
        type_num_layout.addWidget(self.number_spin, 1)

        form.addRow("Тип и номер:", type_num_widget)

        # Тема работы
        self.title_edit = QLineEdit()
        self.title_edit.setFixedHeight(44)
        self.title_edit.setPlaceholderText("Например: Двоичные деревья поиска")
        form.addRow("Тема работы *:", self.title_edit)

        # Вариант
        self.variant_edit = QLineEdit()
        self.variant_edit.setFixedHeight(44)
        self.variant_edit.setPlaceholderText("Например: Вариант 12")
        form.addRow("Вариант:", self.variant_edit)

        # Дата дедлайна
        self.deadline_edit = QDateTimeEdit()
        self.deadline_edit.setFixedHeight(44)
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        default_dl = datetime.now() + timedelta(days=7)
        default_dl = default_dl.replace(hour=23, minute=59, second=0)
        self.deadline_edit.setDateTime(QDateTime(default_dl.date(), default_dl.time()))
        form.addRow("Дедлайн:", self.deadline_edit)

        # Начальный статус
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(44)
        for key, label in STATUS_LABELS.items():
            self.status_combo.addItem(label, userData=key)
        self.status_combo.setCurrentIndex(0)
        form.addRow("Статус:", self.status_combo)

        # Заметки
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Требования преподавателя, критерии сдачи...")
        self.notes_edit.setFixedHeight(90)
        self.notes_edit.setStyleSheet(
            f"background-color: {self.theme['card_bg']}; border-radius: 18px; border: none; padding: 12px 16px;"
        )
        form.addRow("Заметки:", self.notes_edit)

        layout.addLayout(form)

        # Кнопки
        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        ok_btn = btn_box.button(QDialogButtonBox.Ok)
        ok_btn.setText("Создать")
        ok_btn.setIcon(get_material_icon("add", color=self.theme["on_primary"], size=18))
        ok_btn.setProperty("primary", "true")
        ok_btn.setFixedHeight(44)
        ok_btn.setCursor(Qt.PointingHandCursor)

        cancel_btn = btn_box.button(QDialogButtonBox.Cancel)
        cancel_btn.setText("Отмена")
        cancel_btn.setIcon(get_material_icon("close", color=self.theme["on_secondary"], size=18))
        cancel_btn.setFixedHeight(44)
        cancel_btn.setCursor(Qt.PointingHandCursor)

        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._update_next_number()

    def _update_next_number(self) -> None:
        subject_id = self.subject_combo.currentData()
        task_type = self.type_combo.currentText()
        if subject_id is not None:
            next_num = self.db.get_next_task_number(subject_id, task_type)
            self.number_spin.setValue(next_num)

    def _validate_and_accept(self) -> None:
        if self.subject_combo.count() == 0:
            QMessageBox.warning(self, "Ошибка", "Сначала создайте хотя бы один предмет!")
            return
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите тему работы!")
            self.title_edit.setFocus()
            return
        self.accept()

    def get_data(self) -> dict:
        dt: datetime = self.deadline_edit.dateTime().toPython()
        deadline_str = dt.strftime("%Y-%m-%d %H:%M")
        return {
            "subject_id": self.subject_combo.currentData(),
            "number": self.number_spin.value(),
            "type": self.type_combo.currentText(),
            "title": self.title_edit.text().strip(),
            "variant": self.variant_edit.text().strip() or None,
            "status": self.status_combo.currentData(),
            "deadline_date": deadline_str,
            "notes": self.notes_edit.toPlainText().strip() or None,
        }

"""Виджет карточки практической работы в стилистике Google Material Design 3 Expressive.
Zero-Border, тональная иерархия, скрытый текст в прогресс-баре, фиксированный капсульный комбобокс.
"""

from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..database import (
    STATUS_COMPLETED,
    STATUS_DEFAULT_PROGRESS,
    STATUS_LABELS,
    Task,
)
from .icons import get_material_icon
from .theme import (
    DEFAULT_THEME,
    STATUS_COLORS_MD3,
    get_md3_urgency,
    get_theme,
)


class TaskCardWidget(QFrame):
    """
    Интерактивная карточка работы Material 3 Expressive.
    Zero-Border: разделение исключительно за счет тона фона и воздушных отступов.
    """

    clicked = Signal(int)  # task_id
    status_changed = Signal(int, str)  # task_id, new_status
    open_folder_requested = Signal(int)  # task_id

    def __init__(
        self,
        task: Task,
        is_selected: bool = False,
        theme_key: str = DEFAULT_THEME,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.task = task
        self.is_selected = is_selected
        self.theme: Dict[str, str] = get_theme(theme_key)

        self.setFrameShape(QFrame.NoFrame)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("TaskCard")

        self._init_ui()
        self._update_container_style()

    def set_selected(self, selected: bool) -> None:
        """Переключает состояние выбора без добавления рамки — только сменой тона."""
        self.is_selected = selected
        self._update_container_style()

    def apply_theme(self, theme_key: str) -> None:
        """Реактивное обновление цветовой палитры Monet."""
        self.theme = get_theme(theme_key)
        self._update_container_style()
        self._update_badges()
        self._update_deadline_badge()
        self._style_status_combo(self.task.status)
        self._style_open_button()
        self.title_label.setStyleSheet(
            f"font-size: 17px; font-weight: 600; color: {self.theme['text_primary']}; border: none; background: transparent;"
        )
        self.prog_pct_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {self.theme['text_secondary']}; border: none; background: transparent;"
        )

    def refresh_theme(self, palette: Dict[str, str]) -> None:
        self.theme = palette
        self._update_container_style()
        self._update_badges()
        self._update_deadline_badge()
        self._style_status_combo(self.task.status)
        self._style_open_button()
        self.title_label.setStyleSheet(
            f"font-size: 17px; font-weight: 600; color: {self.theme['text_primary']}; border: none; background: transparent;"
        )
        self.prog_pct_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {self.theme['text_secondary']}; border: none; background: transparent;"
        )

    def _update_container_style(self) -> None:
        card_bg = self.theme.get("card_bg", "rgba(32, 38, 52, 185)")
        card_hover = self.theme.get("card_hover", "rgba(42, 50, 68, 210)")
        card_selected = self.theme.get("card_selected", "rgba(52, 64, 88, 225)")

        active_bg = card_selected if self.is_selected else card_bg

        # ВАЖНО: Никаких borders! Только чистый тон поверхности и скругление 20px
        self.setStyleSheet(
            f"""
            QFrame#TaskCard {{
                background-color: {active_bg};
                border-radius: 20px;
                border: none;
            }}
            QFrame#TaskCard:hover {{
                background-color: {card_hover};
            }}
            """
        )

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(12)

        # ----------------------------------------------------------------------
        # 1. Верхний ряд: Чип предмета, Чип типа и номера, Чип варианта, Дедлайн
        # ----------------------------------------------------------------------
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Цветной кружок-индикатор предмета
        self.color_dot = QLabel()
        self.color_dot.setFixedSize(10, 10)
        top_row.addWidget(self.color_dot)

        # Чип названия предмета
        self.subject_chip = None
        if self.task.subject_name:
            self.subject_chip = QLabel(self.task.subject_name)
            top_row.addWidget(self.subject_chip)

        # Чип типа и номера работы (ПР, ЛР, КР)
        type_prefix = {
            "Практическая": "ПР",
            "Лабораторная": "ЛР",
            "Курсовая": "КР",
            "Реферат": "РЕФ",
        }.get(self.task.type, self.task.type)

        self.type_chip = QLabel(f"{type_prefix} №{self.task.number}")
        top_row.addWidget(self.type_chip)

        # Чип варианта
        self.variant_chip = None
        if self.task.variant:
            self.variant_chip = QLabel(self.task.variant)
            self.variant_chip.setStyleSheet(
                """
                QLabel {
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #C6C6CD;
                    border-radius: 8px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    border: none;
                }
                """
            )
            top_row.addWidget(self.variant_chip)

        top_row.addStretch()

        # Семантический чип дедлайна
        deadline_text = self._format_deadline_display(self.task.deadline_date)
        self.deadline_chip = QLabel(deadline_text)
        top_row.addWidget(self.deadline_chip)

        self._update_badges()
        self._update_deadline_badge()
        main_layout.addLayout(top_row)

        # ----------------------------------------------------------------------
        # 2. Центральный ряд: Крупная тема работы
        # ----------------------------------------------------------------------
        self.title_label = QLabel(self.task.title)
        self.title_label.setStyleSheet(
            f"font-size: 17px; font-weight: 600; color: {self.theme['text_primary']}; border: none; background: transparent;"
        )
        self.title_label.setWordWrap(True)
        main_layout.addWidget(self.title_label)

        # ----------------------------------------------------------------------
        # 3. Нижний ряд: Компактный статус (32px), прогресс-бар и Tonal кнопка
        # ----------------------------------------------------------------------
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        # Компактный селектор статуса (фиксированная высота 32px, скругление 16px)
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(32)
        self.status_combo.setMinimumWidth(148)
        self.status_combo.setCursor(Qt.PointingHandCursor)

        for key, label in STATUS_LABELS.items():
            self.status_combo.addItem(label, userData=key)

        current_idx = self.status_combo.findData(self.task.status)
        if current_idx >= 0:
            self.status_combo.setCurrentIndex(current_idx)

        self._style_status_combo(self.task.status)
        self.status_combo.currentIndexChanged.connect(self._on_status_changed)
        bottom_row.addWidget(self.status_combo)

        # Прогресс-бар M3 Expressive (высота 6px, скругление 3px, скрытый встроенный текст)
        progress_container = QWidget()
        progress_container.setStyleSheet("background: transparent; border: none;")
        prog_layout = QVBoxLayout(progress_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(2)

        prog_label_row = QHBoxLayout()
        prog_label_row.setContentsMargins(0, 0, 0, 0)
        prog_label_row.addStretch()

        self.prog_pct_lbl = QLabel(f"{self.task.progress_percent}%")
        self.prog_pct_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {self.theme['text_secondary']}; border: none; background: transparent;"
        )
        prog_label_row.addWidget(self.prog_pct_lbl)
        prog_layout.addLayout(prog_label_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(self.task.progress_percent)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        prog_layout.addWidget(self.progress_bar)

        bottom_row.addWidget(progress_container, 1)

        # Компактная Tonal кнопка «Открыть папку» (высота 32px, скругление 16px)
        self.open_folder_btn = QPushButton("Открыть папку")
        self.open_folder_btn.setToolTip("Открыть папку работы на диске")
        self.open_folder_btn.setFixedHeight(32)
        self.open_folder_btn.setCursor(Qt.PointingHandCursor)
        self._style_open_button()
        self.open_folder_btn.clicked.connect(lambda: self.open_folder_requested.emit(self.task.id))
        bottom_row.addWidget(self.open_folder_btn)

        main_layout.addLayout(bottom_row)

    def _update_badges(self) -> None:
        dot_color = self.task.subject_color or self.theme["primary"]
        self.color_dot.setStyleSheet(
            f"background-color: {dot_color}; border-radius: 5px; border: none;"
        )

        if self.subject_chip:
            self.subject_chip.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {self.theme['secondary_container']};
                    color: {self.theme['primary']};
                    border-radius: 8px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    border: none;
                }}
                """
            )

        self.type_chip.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.theme['secondary_container']};
                color: {self.theme['on_secondary']};
                border-radius: 8px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }}
            """
        )

    def _update_deadline_badge(self) -> None:
        urgency, urg_text_color, urg_bg_color = get_md3_urgency(
            self.task.deadline_date,
            self.task.status == STATUS_COMPLETED,
        )
        self.deadline_chip.setStyleSheet(
            f"""
            QLabel {{
                background-color: {urg_bg_color};
                color: {urg_text_color};
                border-radius: 8px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }}
            """
        )

    def _style_open_button(self) -> None:
        self.open_folder_btn.setFixedHeight(32)
        self.open_folder_btn.setIcon(get_material_icon("folder_open", color=self.theme["primary"], size=16))
        self.open_folder_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme['secondary_container']};
                color: {self.theme['primary']};
                border: none;
                border-radius: 16px;
                min-height: 32px;
                max-height: 32px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.22);
                color: #FFFFFF;
                border: none;
                border-radius: 16px;
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.12);
                color: #FFFFFF;
                border: none;
                border-radius: 16px;
            }}
            """
        )

    def _style_status_combo(self, status: str) -> None:
        st_info = STATUS_COLORS_MD3.get(status, {})
        bg_col = st_info.get("bg", "rgba(142, 144, 153, 30)")
        fg_col = st_info.get("fg", "#C6C6CD")

        self.status_combo.setFixedHeight(32)
        self.status_combo.setMinimumWidth(148)
        self.status_combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {bg_col};
                border: none;
                color: {fg_col};
                font-weight: 600;
                font-size: 12px;
                padding: 0 14px;
                border-radius: 16px;
                min-height: 32px;
                max-height: 32px;
            }}
            QComboBox:hover {{
                background-color: {bg_col};
                border: none;
                border-radius: 16px;
            }}
            QComboBox:focus {{
                border: none;
                border-radius: 16px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }}
            QComboBox QAbstractItemView {{
                background-color: #1A1D24;
                border: none;
                border-radius: 14px;
                padding: 6px;
                selection-background-color: {self.theme['secondary_container']};
                selection-color: {self.theme['on_secondary']};
                color: {self.theme['text_primary']};
            }}
            """
        )

    def _format_deadline_display(self, deadline_str: Optional[str]) -> str:
        if not deadline_str:
            return "Без дедлайна"
        if self.task.status == STATUS_COMPLETED:
            return "Сдано"
        try:
            if len(deadline_str) == 10:
                dt = deadline_str
            else:
                parts = deadline_str.split(" ")
                date_parts = parts[0].split("-")
                time_part = parts[1] if len(parts) > 1 else ""
                dt = f"{date_parts[2]}.{date_parts[1]} {time_part}".strip()
            return f"До {dt}"
        except Exception:
            return deadline_str

    def _on_status_changed(self, index: int) -> None:
        new_status = self.status_combo.itemData(index)
        if new_status and new_status != self.task.status:
            self.task.status = new_status
            default_prog = STATUS_DEFAULT_PROGRESS.get(new_status, self.task.progress_percent)
            self.task.progress_percent = default_prog
            self.progress_bar.setValue(default_prog)
            self.prog_pct_lbl.setText(f"{default_prog}%")
            self._style_status_combo(new_status)
            self._update_deadline_badge()
            self.status_changed.emit(self.task.id, new_status)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.clicked.emit(self.task.id)

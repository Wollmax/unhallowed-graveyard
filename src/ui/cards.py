"""Google Material Design 3 Expressive (Pixel Monet Engine) Card Widgets.
Кастомные компоненты интерфейса: ThemeSwatchButton, SubjectCard и TaskCard.
Zero-Borders, аппаратный антиалиасинг QPainter, семантические чипы и надежная геометрия.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
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
    Subject,
    Task,
)
from .icons import get_material_icon
from .theme import (
    DEFAULT_THEME,
    PIXEL_THEMES,
    STATUS_COLORS_MD3,
    get_md3_urgency,
    get_theme,
)


# ==============================================================================
# 1. Круглая кнопка выбора темы Pixel Monet (QPainter Antialiasing)
# ==============================================================================

class ThemeSwatchButton(QWidget):
    """
    Круглая кнопка выбора темы Google Pixel Monet.
    Отрисовывается через QPainter с субпиксельным сглаживанием без пиксельных лесенок CSS.
    При активности отображает четкое внешнее белое кольцо толщиной 2px.
    """

    clicked = Signal(str)  # theme_key

    def __init__(
        self,
        theme_key: str,
        swatch_color: str,
        is_selected: bool = False,
        theme_name: str = "",
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.theme_key = theme_key
        self.swatch_color = swatch_color
        self.is_selected = is_selected
        self.theme_name = theme_name
        self.is_dark = is_dark
        self.is_hovered = False

        self.setFixedSize(26, 26)
        self.setCursor(Qt.PointingHandCursor)
        if theme_name:
            self.setToolTip(theme_name)

    def set_selected(self, selected: bool) -> None:
        """Переключает активное состояние кнопки и перерисовывает кольцо."""
        if self.is_selected != selected:
            self.is_selected = selected
            self.update()

    def set_is_dark(self, is_dark: bool) -> None:
        """Обновляет режим отображения контрастного кольца (темная/светлая тема)."""
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self.update()

    def set_swatch_color(self, color: str) -> None:
        """Обновляет цвет свотча при смене светлой/темной темы."""
        if self.swatch_color != color:
            self.swatch_color = color
            self.update()

    def isChecked(self) -> bool:
        """Совместимость с интерфейсом переключателей."""
        return self.is_selected

    def setChecked(self, checked: bool) -> None:
        """Совместимость с интерфейсом переключателей."""
        self.set_selected(checked)

    def enterEvent(self, event) -> None:
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.theme_key)
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Отрисовывает идеально сглаженный кругляшок с кольцом активности."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        color = QColor(self.swatch_color)

        ring_color = QColor("#FFFFFF") if self.is_dark else QColor("#1A1C1E")
        hover_ring = QColor(255, 255, 255, 120) if self.is_dark else QColor(0, 0, 0, 90)

        if self.is_selected:
            # 1. Внешнее четкое кольцо толщиной 2px
            ring_pen = QPen(ring_color, 2.0)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(1.0, 1.0, w - 2.0, h - 2.0))

            # 2. Внутренний круг фирменного оттенка палитры
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QRectF(4.0, 4.0, w - 8.0, h - 8.0))
        else:
            if self.is_hovered:
                # Мягкое полупрозрачное кольцо при наведении
                hover_pen = QPen(hover_ring, 1.5)
                painter.setPen(hover_pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QRectF(1.5, 1.5, w - 3.0, h - 3.0))

                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(QRectF(3.5, 3.5, w - 7.0, h - 7.0))
            else:
                # Стандартный ровный круг
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(QRectF(2.0, 2.0, w - 4.0, h - 4.0))


# ==============================================================================
# 2. Карточка учебного предмета (Левая панель)
# ==============================================================================

class SubjectCard(QFrame):
    """
    Карточка предмета в стиле Google Material 3 Expressive.
    Скругление 18px, Zero Borders, индикатор прогресса со сбалансированной типографикой.
    """

    clicked = Signal(int)  # subject_id

    def __init__(
        self,
        subject: Subject,
        is_selected: bool = False,
        theme_key: str = DEFAULT_THEME,
        mode: str = "dark",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.subject = subject
        self.is_selected = is_selected
        self.is_hovered = False
        self.theme_mode = mode if mode in ("dark", "light") else "dark"
        self.theme: Dict[str, str] = get_theme(theme_key, mode=self.theme_mode)

        self.setObjectName("SubjectCard")
        self.setFrameShape(QFrame.NoFrame)
        self.setCursor(Qt.PointingHandCursor)

        # Мягкая рассеянная тень матового стекла с поддержкой прыгучей анимации (Spring Overshoot)
        is_dark = self.theme.get("is_dark", True)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(10.0)
        self._shadow.setYOffset(2.0)
        self._shadow.setXOffset(0.0)
        self._shadow.setColor(QColor(0, 0, 0, 50 if is_dark else 20))
        self.setGraphicsEffect(self._shadow)

        self._anim_group: Optional[QParallelAnimationGroup] = None

        self._init_ui()

    def set_selected(self, selected: bool) -> None:
        """Обновляет состояние выбора карточки и применяет фоновые стили."""
        prev = self.is_selected
        self.is_selected = selected
        self._update_card_style()
        if selected and not prev:
            self._animate_bounce(is_hover=True)
        elif not selected and prev:
            self._animate_bounce(is_hover=False)

    def apply_theme(self, palette: Union[Dict[str, Any], str], mode: str = "dark") -> None:
        """
        Динамически обновляет палитру карточки, сохраняя все скругления и размеры.
        Принимает словарь палитры или строковый ключ темы.
        """
        if isinstance(palette, str):
            self.theme = get_theme(palette, mode=mode)
        else:
            self.theme = palette

        self._update_card_style()
        self._update_badges()
        self._update_progress_style()
        self._update_labels_style()

    def update_progress(self, completed: int, total: int) -> None:
        """Обновляет данные прогресс-бара и статистической строки."""
        self.subject.completed_tasks = completed
        self.subject.total_tasks = total
        pct = int((completed / total * 100)) if total > 0 else 0
        self.progress_bar.setValue(pct)

        stat_text = f"{completed}/{total} • {pct}%" if total > 0 else "0/0 • 0%"
        self.stat_label.setText(stat_text)

    def _update_card_style(self) -> None:
        """Формирует стили контейнера карточки в чистом стиле Zero-Border."""
        if self.is_selected:
            bg_color = self.theme["secondary_container"]
            border = f"1.5px solid {self.theme.get('primary', '#8AB4F8')}"
        elif self.is_hovered:
            bg_color = self.theme["card_hover"]
            border = "none"
        else:
            bg_color = self.theme["card_bg"]
            border = "none"

        self.setStyleSheet(
            f"""
            QFrame#SubjectCard {{
                background-color: {bg_color};
                border-radius: 18px;
                border: {border};
            }}
            """
        )

    def enterEvent(self, event) -> None:
        """Наведение курсора: подсветка грани и прыгучий подъем тени (Spring Overshoot)."""
        self.is_hovered = True
        self._update_card_style()
        self._animate_bounce(is_hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Увод курсора: плавный возврат в исходное состояние."""
        self.is_hovered = False
        self._update_card_style()
        self._animate_bounce(is_hover=False)
        super().leaveEvent(event)

    def _animate_bounce(self, is_hover: bool) -> None:
        """Прыгучая физика (Spring Bounce) через QEasingCurve.OutBack."""
        if self._anim_group and self._anim_group.state() == QParallelAnimationGroup.Running:
            self._anim_group.stop()

        self._anim_group = QParallelAnimationGroup(self)
        is_dark = self.theme.get("is_dark", True)

        target_blur = 24.0 if is_hover else 10.0
        target_y = 6.0 if is_hover else 2.0
        target_alpha = (75 if is_hover else 50) if is_dark else (40 if is_hover else 20)

        anim_b = QPropertyAnimation(self._shadow, b"blurRadius")
        anim_b.setDuration(240)
        anim_b.setStartValue(self._shadow.blurRadius())
        anim_b.setEndValue(target_blur)
        anim_b.setEasingCurve(QEasingCurve.OutBack if is_hover else QEasingCurve.OutQuad)

        anim_y = QPropertyAnimation(self._shadow, b"yOffset")
        anim_y.setDuration(240)
        anim_y.setStartValue(self._shadow.yOffset())
        anim_y.setEndValue(target_y)
        anim_y.setEasingCurve(QEasingCurve.OutBack if is_hover else QEasingCurve.OutQuad)

        self._shadow.setColor(QColor(0, 0, 0, target_alpha))

        self._anim_group.addAnimation(anim_b)
        self._anim_group.addAnimation(anim_y)
        self._anim_group.start()

    def _init_ui(self) -> None:
        self._update_card_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # ----------------------------------------------------------------------
        # Верхний ряд: Цветная точка, краткий тег и капсульный тип сдачи
        # ----------------------------------------------------------------------
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setContentsMargins(0, 0, 0, 0)

        # 1. Цветная точка предмета (10x10 px, border-radius: 5px)
        self.color_dot = QLabel()
        self.color_dot.setFixedSize(10, 10)
        self.color_dot.setStyleSheet(
            f"background-color: {self.subject.color_hex}; border-radius: 5px; border: none; background-clip: padding;"
        )
        self.color_dot.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top_row.addWidget(self.color_dot)

        # 2. Краткий тег предмета (жирный 12px)
        tag_text = self.subject.short_name or "КУРС"
        self.tag_label = QLabel(tag_text)
        self.tag_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top_row.addWidget(self.tag_label)

        top_row.addStretch()

        # 3. Капсульный чип типа сдачи (Экзамен / Зачет)
        self.exam_chip: Optional[QLabel] = None
        if self.subject.exam_type:
            self.exam_chip = QLabel(self.subject.exam_type)
            self.exam_chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            top_row.addWidget(self.exam_chip)

        self._update_badges()
        layout.addLayout(top_row)

        # ----------------------------------------------------------------------
        # Средний ряд: Название предмета и преподаватель
        # ----------------------------------------------------------------------
        self.name_label = QLabel(self.subject.name)
        self.name_label.setWordWrap(True)
        self.name_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.name_label)

        self.teacher_label: Optional[QLabel] = None
        if self.subject.teacher_name:
            self.teacher_label = QLabel(f"Преподаватель: {self.subject.teacher_name}")
            self.teacher_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            layout.addWidget(self.teacher_label)

        self._update_labels_style()

        # ----------------------------------------------------------------------
        # Нижний ряд: Гладкий прогресс-бар и ОДИН аккуратный лейбл статистики
        # ----------------------------------------------------------------------
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        bottom_row.setContentsMargins(0, 2, 0, 0)

        total = self.subject.total_tasks
        done = self.subject.completed_tasks
        pct = int((done / total * 100)) if total > 0 else 0

        # Предотвращаем баг №1: setTextVisible(False) для исключения встроенного текста 0%
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(pct)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        bottom_row.addWidget(self.progress_bar, 1)

        # Единственный отдельный QLabel для вывода статистики без обрезки по вертикали
        stat_text = f"{done}/{total} • {pct}%" if total > 0 else "0/0 • 0%"
        self.stat_label = QLabel(stat_text)
        self.stat_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.stat_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        bottom_row.addWidget(self.stat_label)

        self._update_progress_style()
        layout.addLayout(bottom_row)

    def _update_badges(self) -> None:
        """Обновляет стили чипов верхнего ряда."""
        self.tag_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.theme['secondary_container']};
                color: {self.theme['primary']};
                border-radius: 8px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }}
            """
        )

        if self.exam_chip:
            is_dark = self.theme.get("is_dark", True)
            exam_bg = "rgba(255, 255, 255, 18)" if is_dark else "rgba(0, 0, 0, 16)"
            self.exam_chip.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {exam_bg};
                    color: {self.theme['text_secondary']};
                    border-radius: 8px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 600;
                    border: none;
                }}
                """
            )

    def _update_labels_style(self) -> None:
        """Стилизует текстовые метки названия и преподавателя."""
        self.name_label.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {self.theme['text_primary']}; border: none; background: transparent;"
        )
        if self.teacher_label:
            self.teacher_label.setStyleSheet(
                f"font-size: 12px; color: {self.theme['text_secondary']}; border: none; background: transparent;"
            )

    def _update_progress_style(self) -> None:
        """Стилизует прогресс-бар и текстовую статистику."""
        is_dark = self.theme.get("is_dark", True)
        pb_bg = "rgba(255, 255, 255, 25)" if is_dark else "rgba(0, 0, 0, 20)"
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {pb_bg};
                border: none;
                border-radius: 3px;
                height: 6px;
                max-height: 6px;
                min-height: 6px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {self.theme['primary']};
                border-radius: 3px;
                border: none;
            }}
            """
        )
        self.stat_label.setStyleSheet(
            f"font-size: 12px; font-weight: 600; min-height: 18px; color: {self.theme['text_secondary']}; border: none; background: transparent;"
        )

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.subject.id)


# ==============================================================================
# 3. Карточка практической работы (Центральная панель)
# ==============================================================================

class TaskCard(QFrame):
    """
    Карточка работы в стиле Google Material 3 Expressive.
    Скругление 20px, семантические чипы дедлайна, компактный капсульный QComboBox (32px),
    гладкий прогресс-бар и Tonal-кнопка открытия папки.
    """

    clicked = Signal(int)  # task_id
    status_changed = Signal(int, str)  # task_id, new_status
    open_folder_requested = Signal(int)  # task_id

    def __init__(
        self,
        task: Task,
        is_selected: bool = False,
        theme_key: str = DEFAULT_THEME,
        mode: str = "dark",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.task = task
        self.is_selected = is_selected
        self.is_hovered = False
        self.theme_mode = mode if mode in ("dark", "light") else "dark"
        self.theme: Dict[str, str] = get_theme(theme_key, mode=self.theme_mode)

        self.setObjectName("TaskCard")
        self.setFrameShape(QFrame.NoFrame)
        self.setCursor(Qt.PointingHandCursor)

        # Мягкая рассеянная тень матового стекла с поддержкой прыгучей анимации (Spring Overshoot)
        is_dark = self.theme.get("is_dark", True)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(12.0)
        self._shadow.setYOffset(3.0)
        self._shadow.setXOffset(0.0)
        self._shadow.setColor(QColor(0, 0, 0, 55 if is_dark else 22))
        self.setGraphicsEffect(self._shadow)

        self._anim_group: Optional[QParallelAnimationGroup] = None

        self._init_ui()

    def set_selected(self, selected: bool) -> None:
        """Устанавливает выбор карточки и переключает фоновые цвета."""
        prev = self.is_selected
        self.is_selected = selected
        self._update_card_style()
        if selected and not prev:
            self._animate_bounce(is_hover=True)
        elif not selected and prev:
            self._animate_bounce(is_hover=False)

    def apply_theme(self, palette: Union[Dict[str, Any], str], mode: str = "dark") -> None:
        """
        Динамически обновляет тему карточки работы, полностью сохраняя геометрию и радиусы.
        Предотвращает баг №3 при смене темы оформления.
        """
        if isinstance(palette, str):
            self.theme = get_theme(palette, mode=mode)
        else:
            self.theme = palette

        self._update_card_style()
        self._update_badges()
        self._update_deadline_badge()
        self._update_title_style()
        self._update_combo_style()
        self._update_progress_style()
        self._update_folder_button_style()

    def update_status(self, new_status: str, progress_percent: Optional[int] = None) -> None:
        """Внешнее обновление статуса и прогресса карточки."""
        self.task.status = new_status
        if progress_percent is not None:
            self.task.progress_percent = progress_percent
        else:
            self.task.progress_percent = STATUS_DEFAULT_PROGRESS.get(new_status, self.task.progress_percent)

        idx = self.status_combo.findData(new_status)
        if idx >= 0 and self.status_combo.currentIndex() != idx:
            self.status_combo.blockSignals(True)
            self.status_combo.setCurrentIndex(idx)
            self.status_combo.blockSignals(False)

        self.progress_bar.setValue(self.task.progress_percent)
        self.pct_label.setText(f"{self.task.progress_percent}%")
        self._update_deadline_badge()
        self._update_combo_style()

    def update_progress(self, progress_percent: int) -> None:
        """Внешнее обновление процента выполнения работы."""
        self.task.progress_percent = max(0, min(100, progress_percent))
        self.progress_bar.setValue(self.task.progress_percent)
        self.pct_label.setText(f"{self.task.progress_percent}%")

    def update_deadline(self, deadline_date: Optional[str]) -> None:
        """Внешнее обновление дедлайна работы."""
        self.task.deadline_date = deadline_date
        self._update_deadline_badge()

    def _update_card_style(self) -> None:
        """Стилизует подложку карточки работы в чистом стиле Zero-Border."""
        if self.is_selected:
            bg_color = self.theme.get("card_selected", self.theme["card_bg"])
            border = f"1.5px solid {self.theme.get('primary', '#8AB4F8')}"
        elif self.is_hovered:
            bg_color = self.theme["card_hover"]
            border = "none"
        else:
            bg_color = self.theme["card_bg"]
            border = "none"

        self.setStyleSheet(
            f"""
            QFrame#TaskCard {{
                background-color: {bg_color};
                border-radius: 20px;
                border: {border};
            }}
            """
        )

    def enterEvent(self, event) -> None:
        """Наведение курсора: подсветка грани и прыгучий подъем тени (Spring Overshoot)."""
        self.is_hovered = True
        self._update_card_style()
        self._animate_bounce(is_hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Увод курсора: плавный возврат в исходное состояние."""
        self.is_hovered = False
        self._update_card_style()
        self._animate_bounce(is_hover=False)
        super().leaveEvent(event)

    def _animate_bounce(self, is_hover: bool) -> None:
        """Прыгучая физика (Spring Bounce) через QEasingCurve.OutBack."""
        if self._anim_group and self._anim_group.state() == QParallelAnimationGroup.Running:
            self._anim_group.stop()

        self._anim_group = QParallelAnimationGroup(self)
        is_dark = self.theme.get("is_dark", True)

        target_blur = 28.0 if is_hover else 12.0
        target_y = 8.0 if is_hover else 3.0
        target_alpha = (85 if is_hover else 55) if is_dark else (48 if is_hover else 22)

        anim_b = QPropertyAnimation(self._shadow, b"blurRadius")
        anim_b.setDuration(240)
        anim_b.setStartValue(self._shadow.blurRadius())
        anim_b.setEndValue(target_blur)
        anim_b.setEasingCurve(QEasingCurve.OutBack if is_hover else QEasingCurve.OutQuad)

        anim_y = QPropertyAnimation(self._shadow, b"yOffset")
        anim_y.setDuration(240)
        anim_y.setStartValue(self._shadow.yOffset())
        anim_y.setEndValue(target_y)
        anim_y.setEasingCurve(QEasingCurve.OutBack if is_hover else QEasingCurve.OutQuad)

        self._shadow.setColor(QColor(0, 0, 0, target_alpha))

        self._anim_group.addAnimation(anim_b)
        self._anim_group.addAnimation(anim_y)
        self._anim_group.start()

    def _init_ui(self) -> None:
        self._update_card_style()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        # ----------------------------------------------------------------------
        # Верхний ряд: Чипы предмета, типа/номера, варианта и дедлайна
        # ----------------------------------------------------------------------
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setContentsMargins(0, 0, 0, 0)

        # 1. Капсульный чип предмета
        subj_name = self.task.subject_name or "КУРС"
        self.subject_chip = QLabel(subj_name)
        self.subject_chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top_row.addWidget(self.subject_chip)

        # 2. Чип типа и номера (ЛР №1, ПР №2)
        type_prefix = {
            "Практическая": "ПР",
            "Лабораторная": "ЛР",
            "Курсовая": "КР",
            "Реферат": "РЕФ",
        }.get(self.task.type, self.task.type)
        self.type_chip = QLabel(f"{type_prefix} №{self.task.number}")
        self.type_chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top_row.addWidget(self.type_chip)

        # 3. Чип варианта (Вар. 11, если указан)
        self.variant_chip: Optional[QLabel] = None
        if self.task.variant:
            var_raw = str(self.task.variant).strip()
            var_text = var_raw if var_raw.lower().startswith("вар") else f"Вар. {var_raw}"
            self.variant_chip = QLabel(var_text)
            self.variant_chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            top_row.addWidget(self.variant_chip)

        top_row.addStretch()

        # 4. Семантический чип дедлайна
        self.deadline_badge = QLabel()
        self.deadline_badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top_row.addWidget(self.deadline_badge)

        self._update_badges()
        self._update_deadline_badge()
        main_layout.addLayout(top_row)

        # ----------------------------------------------------------------------
        # Средний ряд: Тема работы (крупный выразительный заголовок 17px DemiBold)
        # ----------------------------------------------------------------------
        self.title_label = QLabel(self.task.title)
        self.title_label.setWordWrap(True)
        self.title_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._update_title_style()
        main_layout.addWidget(self.title_label)

        # ----------------------------------------------------------------------
        # Нижний ряд: QComboBox статуса (32px), Прогресс-бар и кнопка Папка
        # ----------------------------------------------------------------------
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        bottom_row.setContentsMargins(0, 2, 0, 0)
        bottom_row.setAlignment(Qt.AlignVCenter)

        # 1. Компактный QComboBox статуса (Предотвращаем баг №2: 32px высота, >= 145px ширина)
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(32)
        self.status_combo.setMinimumWidth(150)
        for key, label in STATUS_LABELS.items():
            self.status_combo.addItem(label, userData=key)

        curr_idx = self.status_combo.findData(self.task.status)
        if curr_idx >= 0:
            self.status_combo.setCurrentIndex(curr_idx)

        self.status_combo.currentIndexChanged.connect(self._on_combo_status_changed)
        bottom_row.addWidget(self.status_combo)

        # 2. Центральная зона прогресса (растягивается, stretch=1)
        bottom_row.addSpacing(16)

        # Предотвращаем баг №1: setTextVisible(False) для исключения внутреннего текста 0%
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(self.task.progress_percent)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        bottom_row.addWidget(self.progress_bar, 1)

        # Единственный отдельный QLabel для точного отображения процентов без сжатия
        self.pct_label = QLabel(f"{self.task.progress_percent}%")
        self.pct_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        bottom_row.addWidget(self.pct_label)

        # 3. Капсульная кнопка Папка (Tonal Button, 32px)
        self.folder_button = QPushButton("Папка")
        self.folder_button.setFixedHeight(32)
        self.folder_button.setCursor(Qt.PointingHandCursor)
        self.folder_button.setToolTip("Открыть папку работы в проводнике")
        self.folder_button.clicked.connect(lambda: self.open_folder_requested.emit(self.task.id))
        bottom_row.addWidget(self.folder_button)

        self._update_combo_style()
        self._update_progress_style()
        self._update_folder_button_style()

        main_layout.addLayout(bottom_row)

    def _update_badges(self) -> None:
        """Обновляет стили верхних информационных чипов."""
        is_dark = self.theme.get("is_dark", True)
        neutral_chip_bg = "rgba(255, 255, 255, 20)" if is_dark else "rgba(0, 0, 0, 16)"

        # Чип предмета
        self.subject_chip.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.theme['secondary_container']};
                color: {self.theme['primary']};
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }}
            """
        )

        # Чип типа и номера
        self.type_chip.setStyleSheet(
            f"""
            QLabel {{
                background-color: {neutral_chip_bg};
                color: {self.theme['text_primary']};
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }}
            """
        )

        # Чип варианта
        if self.variant_chip:
            self.variant_chip.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {neutral_chip_bg};
                    color: {self.theme['text_secondary']};
                    border-radius: 8px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    border: none;
                }}
                """
            )

    def _update_title_style(self) -> None:
        """Стилизует заголовок работы."""
        self.title_label.setStyleSheet(
            f"font-size: 17px; font-weight: 600; color: {self.theme['text_primary']}; border: none; background: transparent;"
        )

    def _update_deadline_badge(self) -> None:
        """Форматирует дату дедлайна и окрашивает чип по семантическим правилам."""
        deadline_text = self._format_deadline_display(self.task.deadline_date)
        self.deadline_badge.setText(deadline_text)

        bg_col, text_col = self._get_deadline_style()
        self.deadline_badge.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg_col};
                color: {text_col};
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }}
            """
        )

    def _get_deadline_style(self) -> Tuple[str, str]:
        """Определяет цвета фона и текста чипа дедлайна в зависимости от оставшегося времени."""
        is_dark = self.theme.get("is_dark", True)
        neutral_bg = "rgba(255, 255, 255, 18)" if is_dark else "rgba(0, 0, 0, 16)"
        if self.task.status == STATUS_COMPLETED or not self.task.deadline_date:
            return neutral_bg, self.theme.get("text_secondary", "#8E9099")

        try:
            dl_str = self.task.deadline_date
            if len(dl_str) == 10:
                dl = datetime.strptime(dl_str, "%Y-%m-%d")
            elif "T" in dl_str:
                dl = datetime.strptime(dl_str[:16], "%Y-%m-%dT%H:%M")
            else:
                dl = datetime.strptime(dl_str[:16], "%Y-%m-%d %H:%M")

            seconds = (dl - datetime.now()).total_seconds()

            if seconds <= 24 * 3600:
                # Просрочено (<0) или осталось менее 24 часов
                bg = "rgba(255, 180, 171, 40)" if is_dark else "rgba(186, 26, 26, 28)"
                fg = "#FFB4AB" if is_dark else "#BA1A1A"
                return bg, fg
            elif seconds <= 3 * 24 * 3600:
                # Осталось менее 3 дней
                bg = "rgba(245, 191, 66, 40)" if is_dark else "rgba(178, 108, 0, 28)"
                fg = "#FFDF9E" if is_dark else "#8C5800"
                return bg, fg
            else:
                # Более 3 дней
                return neutral_bg, self.theme.get("text_secondary", "#8E9099")
        except Exception:
            return neutral_bg, self.theme.get("text_secondary", "#8E9099")

    def _format_deadline_display(self, deadline_str: Optional[str]) -> str:
        """Преобразует дату дедлайна в компактный пользовательский вид."""
        if not deadline_str:
            return "Без дедлайна"
        if self.task.status == STATUS_COMPLETED:
            return "Сдано"

        try:
            if len(deadline_str) == 10:
                dt_obj = datetime.strptime(deadline_str, "%Y-%m-%d")
                return f"До {dt_obj.strftime('%d.%m')}"
            elif "T" in deadline_str:
                dt_obj = datetime.strptime(deadline_str[:16], "%Y-%m-%dT%H:%M")
                return f"До {dt_obj.strftime('%d.%m %H:%M')}"
            else:
                dt_obj = datetime.strptime(deadline_str[:16], "%Y-%m-%d %H:%M")
                return f"До {dt_obj.strftime('%d.%m %H:%M')}"
        except Exception:
            return f"До {deadline_str}"

    def _update_combo_style(self) -> None:
        """Стилизует выпадающий список статуса (фиксированная капсула 32px, min-width 150px) из матового стекла."""
        is_dark = self.theme.get("is_dark", True)
        combo_bg = "rgba(255, 255, 255, 18)" if is_dark else "rgba(0, 0, 0, 14)"
        combo_hover = "rgba(255, 255, 255, 30)" if is_dark else "rgba(0, 0, 0, 22)"
        itemview_bg = "#1A1D24" if is_dark else "#FFFFFF"

        self.status_combo.setFixedHeight(32)
        self.status_combo.setMinimumWidth(150)
        self.status_combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {combo_bg};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 16px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 500;
                min-height: 32px;
                max-height: 32px;
                height: 32px;
            }}
            QComboBox:hover {{
                background-color: {combo_hover};
                border: 1px solid {self.theme['primary']};
                border-radius: 16px;
            }}
            QComboBox:focus {{
                border: 1.5px solid {self.theme['primary']};
                border-radius: 16px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }}
            QComboBox QAbstractItemView {{
                background-color: {itemview_bg};
                border: none;
                border-radius: 14px;
                padding: 6px;
                selection-background-color: {self.theme['secondary_container']};
                selection-color: {self.theme['on_secondary']};
                color: {self.theme['text_primary']};
            }}
            """
        )

    def _update_progress_style(self) -> None:
        """Стилизует прогресс-бар и процентную метку."""
        is_dark = self.theme.get("is_dark", True)
        pb_bg = "rgba(255, 255, 255, 25)" if is_dark else "rgba(0, 0, 0, 20)"
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {pb_bg};
                border: none;
                border-radius: 3px;
                height: 6px;
                max-height: 6px;
                min-height: 6px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {self.theme['primary']};
                border-radius: 3px;
                border: none;
            }}
            """
        )
        self.pct_label.setStyleSheet(
            f"font-size: 12px; font-weight: 600; min-height: 18px; color: {self.theme['primary']}; border: none; background: transparent;"
        )

    def _update_folder_button_style(self) -> None:
        """Стилизует кнопку открытия папки как Material 3 Tonal Button из матового стекла."""
        self.folder_button.setFixedHeight(32)
        self.folder_button.setIcon(get_material_icon("folder_open", color=self.theme["on_secondary"], size=16))
        is_dark = self.theme.get("is_dark", True)
        btn_border = "rgba(208, 188, 255, 0.25)" if is_dark else "rgba(103, 80, 164, 0.20)"
        hover_bg = "rgba(255, 255, 255, 0.22)" if is_dark else "rgba(0, 0, 0, 0.08)"

        self.folder_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme['secondary_container']};
                color: {self.theme['on_secondary']};
                border: 1px solid {btn_border};
                border-radius: 16px;
                min-height: 32px;
                max-height: 32px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border: 1px solid {self.theme['primary']};
                color: {'#FFFFFF' if is_dark else self.theme['primary']};
                border-radius: 16px;
            }}
            QPushButton:pressed {{
                background-color: {'rgba(255, 255, 255, 0.12)' if is_dark else 'rgba(0, 0, 0, 0.12)'};
                border: 1px solid {btn_border};
                border-radius: 16px;
            }}
            """
        )

    def _on_combo_status_changed(self, index: int) -> None:
        """Обработчик интерактивной смены статуса работы пользователем."""
        new_status = self.status_combo.itemData(index)
        if new_status and new_status != self.task.status:
            self.task.status = new_status
            default_prog = STATUS_DEFAULT_PROGRESS.get(new_status, self.task.progress_percent)
            self.task.progress_percent = default_prog
            self.progress_bar.setValue(default_prog)
            self.pct_label.setText(f"{default_prog}%")
            self._update_deadline_badge()
            self.status_changed.emit(self.task.id, new_status)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.task.id)


# ==============================================================================
# Алиасы для обратной совместимости с существующим кодом
# ==============================================================================

SubjectCardWidget = SubjectCard
TaskCardWidget = TaskCard

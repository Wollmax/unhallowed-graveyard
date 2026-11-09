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
    QVariantAnimation,
)
from PySide6.QtGui import QColor, QMouseEvent, QPaintEvent, QPainter, QPen
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
    STATUS_WAIT_DEFENSE,
    Subject,
    Task,
    parse_deadline_datetime,
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
        self._color = QColor(self.swatch_color)

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
            self._color = QColor(color)
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


class CustomThemeSwatchButton(ThemeSwatchButton):
    """
    Круглая кнопка пользовательского цвета Monet с возможностью удаления.
    При наведении отображает мини-иконку «✕» в верхнем углу для удаления из сохранённых.
    """

    delete_requested = Signal(str)  # hex_color

    def __init__(
        self,
        hex_color: str,
        is_selected: bool = False,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(
            theme_key=f"custom:{hex_color}",
            swatch_color=hex_color,
            is_selected=is_selected,
            theme_name=f"Свой цвет ({hex_color})",
            is_dark=is_dark,
            parent=parent,
        )
        self.hex_color = hex_color
        self.setFixedSize(28, 28)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            # Клик по иконке удаления в правом верхнем углу
            if self.is_hovered and event.pos().x() >= 16 and event.pos().y() <= 12:
                self.delete_requested.emit(self.hex_color)
                event.accept()
                return
            self.clicked.emit(self.theme_key)
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        # Если курсор над свотчем — рисуем аккуратный значок «✕» для удаления
        if self.is_hovered:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            # Круг подложки крестика
            del_rect = QRectF(16.0, 1.0, 11.0, 11.0)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(220, 54, 46))
            painter.drawEllipse(del_rect)

            # Крестик
            painter.setPen(QPen(QColor(255, 255, 255), 1.6, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(18.5, 3.5, 24.5, 9.5)
            painter.drawLine(24.5, 3.5, 18.5, 9.5)



# ==============================================================================
# Кэш стилей для подвиджетов карточек (предотвращает повторный парсинг QSS)
# ==============================================================================

_CARD_SUBWIDGET_STYLE_CACHE: Dict[Tuple[str, str, str, str, str, str, str], Dict[str, str]] = {}


def _get_card_subwidget_styles(theme: Dict[str, Any]) -> Dict[str, str]:
    """Возвращает кэшированные таблицы стилей для дочерних элементов карточек."""
    is_dark = theme.get("is_dark", True)
    key = (
        str(theme.get("primary", "")),
        "dark" if is_dark else "light",
        str(theme.get("secondary_container", "")),
        str(theme.get("on_secondary", "")),
        str(theme.get("text_primary", "")),
        str(theme.get("text_secondary", "")),
        str(theme.get("card_bg", "")),
    )
    cached = _CARD_SUBWIDGET_STYLE_CACHE.get(key)
    if cached is not None:
        return cached

    neutral_chip_bg = "rgba(255, 255, 255, 20)" if is_dark else "rgba(0, 0, 0, 16)"
    combo_bg = "rgba(255, 255, 255, 18)" if is_dark else "rgba(0, 0, 0, 14)"
    combo_hover = "rgba(255, 255, 255, 30)" if is_dark else "rgba(0, 0, 0, 22)"
    itemview_bg = "#1A1D24" if is_dark else "#FFFFFF"
    pb_bg = "rgba(255, 255, 255, 25)" if is_dark else "rgba(0, 0, 0, 20)"
    btn_border = "rgba(208, 188, 255, 0.25)" if is_dark else "rgba(103, 80, 164, 0.20)"
    hover_bg = "rgba(255, 255, 255, 0.22)" if is_dark else "rgba(0, 0, 0, 0.08)"
    pressed_bg = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.14)"

    styles = {
        "subj_card_badge": f"QLabel {{ background-color: {theme['secondary_container']}; color: {theme['primary']}; border-radius: 8px; padding: 3px 8px; font-size: 11px; font-weight: 600; border: none; }}",
        "exam_badge": f"QLabel {{ background-color: {'rgba(255, 255, 255, 18)' if is_dark else 'rgba(0, 0, 0, 16)'}; color: {theme['text_secondary']}; border-radius: 8px; padding: 3px 8px; font-size: 11px; font-weight: 600; border: none; }}",
        "subj_name": f"font-size: 15px; font-weight: 600; color: {theme['text_primary']}; border: none; background: transparent;",
        "subj_teacher": f"font-size: 12px; color: {theme['text_secondary']}; border: none; background: transparent;",
        "subj_pb": f"QProgressBar {{ background-color: {pb_bg}; border: none; border-radius: 3px; height: 6px; max-height: 6px; min-height: 6px; text-align: center; color: transparent; }} QProgressBar::chunk {{ background-color: {theme['primary']}; border-radius: 3px; border: none; }}",
        "subj_stat": f"font-size: 12px; font-weight: 600; min-height: 18px; color: {theme['text_secondary']}; border: none; background: transparent;",
        "task_subj_chip": f"QLabel {{ background-color: {theme['secondary_container']}; color: {theme['primary']}; border-radius: 8px; padding: 4px 10px; font-size: 11px; font-weight: 600; border: none; }}",
        "task_type_chip": f"QLabel {{ background-color: {neutral_chip_bg}; color: {theme['text_primary']}; border-radius: 8px; padding: 4px 10px; font-size: 11px; font-weight: 600; border: none; }}",
        "task_variant_chip": f"QLabel {{ background-color: {neutral_chip_bg}; color: {theme['text_secondary']}; border-radius: 8px; padding: 4px 10px; font-size: 11px; font-weight: 600; border: none; }}",
        "task_title": f"font-size: 17px; font-weight: 600; color: {theme['text_primary']}; border: none; background: transparent;",
        "task_combo": f"""
            QComboBox {{
                background-color: {combo_bg};
                color: {theme['text_primary']};
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
                border: 1px solid {theme['primary']};
                border-radius: 16px;
            }}
            QComboBox:focus {{
                border: 1.5px solid {theme['primary']};
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
                selection-background-color: {theme['secondary_container']};
                selection-color: {theme['on_secondary']};
                color: {theme['text_primary']};
            }}
        """,
        "task_pb": f"""
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
                background-color: {theme['primary']};
                border-radius: 3px;
                border: none;
            }}
        """,
        "task_pct": f"font-size: 12px; font-weight: 600; min-height: 18px; color: {theme['primary']}; border: none; background: transparent;",
        "task_folder_btn": f"""
            QPushButton {{
                background-color: {theme['secondary_container']};
                color: {theme['on_secondary']};
                border-radius: 16px;
                border: 1px solid {btn_border};
                min-height: 32px;
                max-height: 32px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border: 1px solid {theme['primary']};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
            }}
        """,
    }
    _CARD_SUBWIDGET_STYLE_CACHE[key] = styles
    return styles


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

        # Мягкая рассеянная тень: отключена по умолчанию для 6000 FPS скролла, включается при hover/selection
        is_dark = self.theme.get("is_dark", True)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(10.0)
        self._shadow.setYOffset(2.0)
        self._shadow.setXOffset(0.0)
        self._shadow.setColor(QColor(0, 0, 0, 50 if is_dark else 20))
        self._shadow.setEnabled(is_selected)
        self.setGraphicsEffect(self._shadow)

        self._base_y: Optional[int] = None
        self._current_lift: float = 0.0
        self._target_is_hover: bool = False

        self._anim_blur = QPropertyAnimation(self._shadow, b"blurRadius", self)
        self._anim_blur.setDuration(240)
        self._anim_y_offset = QPropertyAnimation(self._shadow, b"yOffset", self)
        self._anim_y_offset.setDuration(240)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(self._anim_blur)
        self._anim_group.addAnimation(self._anim_y_offset)
        self._anim_group.finished.connect(self._on_anim_group_done)

        self._lift_anim = QVariantAnimation(self)
        self._lift_anim.valueChanged.connect(self._on_lift_step)
        self._lift_anim.finished.connect(self._on_lift_done)

        self._init_styles()
        self._init_ui()

    def _on_anim_group_done(self) -> None:
        if not self._target_is_hover and not self.is_selected:
            self._shadow.setEnabled(False)

    def _init_styles(self) -> None:
        p = self.theme.get("primary", "#8AB4F8")
        sc = self.theme.get("secondary_container", "#2B2930")
        ch = self.theme.get("card_hover", "#262338")
        cb = self.theme.get("card_bg", "#1E1B2E")
        self._style_selected = f"QFrame#SubjectCard {{ background-color: {sc}; border-radius: 18px; border: 1.5px solid {p}; }}"
        self._style_hover = f"QFrame#SubjectCard {{ background-color: {ch}; border-radius: 18px; border: none; }}"
        self._style_normal = f"QFrame#SubjectCard {{ background-color: {cb}; border-radius: 18px; border: none; }}"

    def set_selected(self, selected: bool) -> None:
        """Обновляет состояние выбора карточки и применяет фоновые стили."""
        if self.is_selected == selected:
            return
        prev = self.is_selected
        self.is_selected = selected
        self._update_card_style()
        if selected:
            self._shadow.setEnabled(True)
            self._animate_bounce(is_hover=True)
        elif prev:
            self._animate_bounce(is_hover=False)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        if getattr(self, "_is_internal_lift_move", False):
            return
        self._base_y = self.y() - int(self._current_lift)

    def apply_theme(self, palette: Union[Dict[str, Any], str], mode: str = "dark") -> None:
        """
        Динамически обновляет палитру карточки, сохраняя все скругления и размеры.
        Принимает словарь палитры или строковый ключ темы.
        """
        if isinstance(palette, str):
            palette = get_theme(palette, mode=mode)

        cache_key = (
            str(palette.get("primary", "")),
            str(palette.get("card_bg", "")),
            mode,
        )
        if getattr(self, "_applied_theme_key", None) == cache_key:
            return
        self._applied_theme_key = cache_key
        self.theme = palette

        self._init_styles()
        self._current_card_style = None
        self._update_card_style()
        self._update_badges()
        self._update_progress_style()
        self._update_labels_style()

    def update_subject_data(self, subject: Subject, is_selected: bool = False) -> None:
        """Обновляет все данные карточки предмета in-place без пересоздания виджета."""
        if self._lift_anim.state() == QVariantAnimation.Running:
            self._lift_anim.stop()
        if self._anim_group.state() == QParallelAnimationGroup.Running:
            self._anim_group.stop()
        self._base_y = None
        self._current_lift = 0.0
        self.is_hovered = False

        self.subject = subject
        self.set_selected(is_selected)

        # 1. Цветная точка
        dot_style = f"background-color: {self.subject.color_hex}; border-radius: 5px; border: none; background-clip: padding;"
        if getattr(self.color_dot, "_cached_dot_style", None) != dot_style:
            self.color_dot.setStyleSheet(dot_style)
            self.color_dot._cached_dot_style = dot_style

        # 2. Краткий тег
        tag_text = self.subject.short_name or "КУРС"
        if self.tag_label.text() != tag_text:
            self.tag_label.setText(tag_text)

        # 3. Капсульный чип типа сдачи
        if self.subject.exam_type:
            if self.exam_chip is None:
                self.exam_chip = QLabel(self.subject.exam_type)
                self.exam_chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                styles = _get_card_subwidget_styles(self.theme)
                self.exam_chip.setStyleSheet(styles["exam_badge"])
                if hasattr(self, "top_row"):
                    self.top_row.addWidget(self.exam_chip)
            else:
                if self.exam_chip.text() != self.subject.exam_type:
                    self.exam_chip.setText(self.subject.exam_type)
                self.exam_chip.show()
        elif self.exam_chip is not None:
            self.exam_chip.hide()

        # 4. Название
        if self.name_label.text() != self.subject.name:
            self.name_label.setText(self.subject.name)

        # 5. Преподаватель
        if self.subject.teacher_name:
            teacher_text = f"Преподаватель: {self.subject.teacher_name}"
            if self.teacher_label is None:
                self.teacher_label = QLabel(teacher_text)
                self.teacher_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                styles = _get_card_subwidget_styles(self.theme)
                self.teacher_label.setStyleSheet(styles["subj_teacher"])
                self.layout().insertWidget(2, self.teacher_label)
            else:
                if self.teacher_label.text() != teacher_text:
                    self.teacher_label.setText(teacher_text)
                self.teacher_label.show()
        elif self.teacher_label is not None:
            self.teacher_label.hide()

        # 6. Прогресс
        self.update_progress(self.subject.completed_tasks, self.subject.total_tasks)

    def update_progress(self, completed: int, total: int) -> None:
        """Обновляет прогресс-бар и текстовую статистику предмета in-place."""
        self.subject.completed_tasks = completed
        self.subject.total_tasks = total
        pct = int((completed / total * 100)) if total > 0 else 0
        if self.progress_bar.value() != pct:
            self.progress_bar.setValue(pct)
        stat_text = f"{completed}/{total} • {pct}%" if total > 0 else "0/0 • 0%"
        if self.stat_label.text() != stat_text:
            self.stat_label.setText(stat_text)

    def _update_card_style(self) -> None:
        """Формирует стили контейнера карточки в чистом стиле Zero-Border."""
        if not hasattr(self, "_style_normal"):
            self._init_styles()
        target = self._style_selected if self.is_selected else (self._style_hover if self.is_hovered else self._style_normal)
        if getattr(self, "_current_card_style", None) != target:
            self._current_card_style = target
            self.setStyleSheet(target)

    def enterEvent(self, event) -> None:
        """Наведение курсора: подсветка грани и прыгучий подъем тени (Spring Overshoot)."""
        self.is_hovered = True
        self._shadow.setEnabled(True)
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
        """Прыгучая физика (Spring Bounce) через QEasingCurve.OutBack с нулевыми аллокациями."""
        self._target_is_hover = is_hover
        if is_hover or self.is_selected:
            self._shadow.setEnabled(True)
        if self._anim_group.state() == QParallelAnimationGroup.Running:
            self._anim_group.stop()

        is_dark = self.theme.get("is_dark", True)
        target_blur = 24.0 if is_hover else 10.0
        target_y = 6.0 if is_hover else 2.0
        target_alpha = (75 if is_hover else 50) if is_dark else (40 if is_hover else 20)
        easing = QEasingCurve.OutBack if is_hover else QEasingCurve.OutQuad

        self._anim_blur.setStartValue(self._shadow.blurRadius())
        self._anim_blur.setEndValue(target_blur)
        self._anim_blur.setEasingCurve(easing)

        self._anim_y_offset.setStartValue(self._shadow.yOffset())
        self._anim_y_offset.setEndValue(target_y)
        self._anim_y_offset.setEasingCurve(easing)

        self._shadow.setColor(QColor(0, 0, 0, target_alpha))
        self._anim_group.start()

        # Физический вертикальный подъём (Spring Lift -4px OutBack)
        if self._lift_anim.state() == QVariantAnimation.Running:
            self._lift_anim.stop()

        if self._base_y is None:
            self._base_y = self.y() - int(self._current_lift)

        target_lift = -4.0 if is_hover else 0.0
        self._lift_anim.setDuration(220 if is_hover else 180)
        self._lift_anim.setStartValue(self._current_lift)
        self._lift_anim.setEndValue(target_lift)
        self._lift_anim.setEasingCurve(QEasingCurve.OutBack if is_hover else QEasingCurve.OutCubic)
        self._lift_anim.start()

    def _on_lift_step(self, val: float) -> None:
        self._current_lift = val
        if self._base_y is not None:
            new_y = self._base_y + int(val)
            if self.y() != new_y:
                self._is_internal_lift_move = True
                try:
                    self.move(self.x(), new_y)
                finally:
                    self._is_internal_lift_move = False

    def _on_lift_done(self) -> None:
        if not self._target_is_hover:
            if self._base_y is not None and self.y() != self._base_y:
                self._is_internal_lift_move = True
                try:
                    self.move(self.x(), self._base_y)
                finally:
                    self._is_internal_lift_move = False
            self._base_y = None
            self._current_lift = 0.0

    def _init_ui(self) -> None:
        self._update_card_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # ----------------------------------------------------------------------
        # Верхний ряд: Цветная точка, краткий тег и капсульный тип сдачи
        # ----------------------------------------------------------------------
        self.top_row = QHBoxLayout()
        self.top_row.setSpacing(8)
        self.top_row.setContentsMargins(0, 0, 0, 0)

        # 1. Цветная точка предмета (10x10 px, border-radius: 5px)
        self.color_dot = QLabel()
        self.color_dot.setFixedSize(10, 10)
        self.color_dot.setStyleSheet(
            f"background-color: {self.subject.color_hex}; border-radius: 5px; border: none; background-clip: padding;"
        )
        self.color_dot.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.top_row.addWidget(self.color_dot)

        # 2. Краткий тег предмета (жирный 12px)
        tag_text = self.subject.short_name or "КУРС"
        self.tag_label = QLabel(tag_text)
        self.tag_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.top_row.addWidget(self.tag_label)

        self.top_row.addStretch()

        # 3. Капсульный чип типа сдачи (Экзамен / Зачет)
        self.exam_chip: Optional[QLabel] = None
        if self.subject.exam_type:
            self.exam_chip = QLabel(self.subject.exam_type)
            self.exam_chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.top_row.addWidget(self.exam_chip)

        self._update_badges()
        layout.addLayout(self.top_row)

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

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(pct)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        bottom_row.addWidget(self.progress_bar, 1)

        stat_text = f"{done}/{total} • {pct}%" if total > 0 else "0/0 • 0%"
        self.stat_label = QLabel(stat_text)
        self.stat_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.stat_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        bottom_row.addWidget(self.stat_label)

        self._update_progress_style()
        layout.addLayout(bottom_row)

    def _update_badges(self) -> None:
        """Обновляет стили чипов верхнего ряда."""
        styles = _get_card_subwidget_styles(self.theme)
        st = styles["subj_card_badge"]
        if getattr(self.tag_label, "_cached_qss", None) != st:
            self.tag_label.setStyleSheet(st)
            self.tag_label._cached_qss = st

        if self.exam_chip:
            eb = styles["exam_badge"]
            if getattr(self.exam_chip, "_cached_qss", None) != eb:
                self.exam_chip.setStyleSheet(eb)
                self.exam_chip._cached_qss = eb

    def _update_labels_style(self) -> None:
        """Стилизует текстовые метки названия и преподавателя."""
        styles = _get_card_subwidget_styles(self.theme)
        sn = styles["subj_name"]
        if getattr(self.name_label, "_cached_qss", None) != sn:
            self.name_label.setStyleSheet(sn)
            self.name_label._cached_qss = sn
        if self.teacher_label:
            st = styles["subj_teacher"]
            if getattr(self.teacher_label, "_cached_qss", None) != st:
                self.teacher_label.setStyleSheet(st)
                self.teacher_label._cached_qss = st

    def _update_progress_style(self) -> None:
        """Стилизует прогресс-бар и текстовую статистику."""
        styles = _get_card_subwidget_styles(self.theme)
        pb = styles["subj_pb"]
        if getattr(self.progress_bar, "_cached_qss", None) != pb:
            self.progress_bar.setStyleSheet(pb)
            self.progress_bar._cached_qss = pb
        sl = styles["subj_stat"]
        if getattr(self.stat_label, "_cached_qss", None) != sl:
            self.stat_label.setStyleSheet(sl)
            self.stat_label._cached_qss = sl

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

        # Мягкая рассеянная тень: отключена по умолчанию для высокого FPS скролла, включается при hover/selection
        is_dark = self.theme.get("is_dark", True)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(12.0)
        self._shadow.setYOffset(3.0)
        self._shadow.setXOffset(0.0)
        self._shadow.setColor(QColor(0, 0, 0, 55 if is_dark else 22))
        self._shadow.setEnabled(is_selected)
        self.setGraphicsEffect(self._shadow)

        # Однократная инициализация переиспользуемых анимаций (предотвращает утечки памяти и аллокации на hover)
        self._base_y: Optional[int] = None
        self._current_lift: float = 0.0
        self._target_is_hover: bool = False

        self._anim_blur = QPropertyAnimation(self._shadow, b"blurRadius", self)
        self._anim_blur.setDuration(240)
        self._anim_y_offset = QPropertyAnimation(self._shadow, b"yOffset", self)
        self._anim_y_offset.setDuration(240)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(self._anim_blur)
        self._anim_group.addAnimation(self._anim_y_offset)
        self._anim_group.finished.connect(self._on_anim_group_done)

        self._lift_anim = QVariantAnimation(self)
        self._lift_anim.valueChanged.connect(self._on_lift_step)
        self._lift_anim.finished.connect(self._on_lift_done)

        self._current_card_style: Optional[str] = None
        self._init_styles()
        self._init_ui()

    def _on_anim_group_done(self) -> None:
        if not self._target_is_hover and not self.is_selected:
            self._shadow.setEnabled(False)

    def _init_styles(self) -> None:
        p = self.theme.get("primary", "#8AB4F8")
        cs = self.theme.get("card_selected", self.theme.get("card_bg", "#1E1B2E"))
        ch = self.theme.get("card_hover", "#262338")
        cb = self.theme.get("card_bg", "#1E1B2E")
        self._style_selected = f"QFrame#TaskCard {{ background-color: {cs}; border-radius: 20px; border: 1.5px solid {p}; }}"
        self._style_hover = f"QFrame#TaskCard {{ background-color: {ch}; border-radius: 20px; border: none; }}"
        self._style_normal = f"QFrame#TaskCard {{ background-color: {cb}; border-radius: 20px; border: none; }}"

    def set_selected(self, selected: bool) -> None:
        """Устанавливает выбор карточки и переключает фоновые цвета."""
        if self.is_selected == selected:
            return
        prev = self.is_selected
        self.is_selected = selected
        self._update_card_style()
        if selected:
            self._shadow.setEnabled(True)
            self._animate_bounce(is_hover=True)
        elif prev:
            self._animate_bounce(is_hover=False)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        if getattr(self, "_is_internal_lift_move", False):
            return
        self._base_y = self.y() - int(self._current_lift)

    def apply_theme(self, palette: Union[Dict[str, Any], str], mode: str = "dark") -> None:
        """
        Динамически обновляет тему карточки работы, полностью сохраняя геометрию и радиусы.
        Предотвращает баг №3 при смене темы оформления.
        """
        if isinstance(palette, str):
            palette = get_theme(palette, mode=mode)

        cache_key = (
            str(palette.get("primary", "")),
            str(palette.get("card_bg", "")),
            mode,
        )
        if getattr(self, "_applied_theme_key", None) == cache_key:
            return
        self._applied_theme_key = cache_key
        self.theme = palette

        self._init_styles()
        self._current_card_style = None
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

    def update_task_data(self, task: Task, is_selected: bool = False) -> None:
        """Обновляет все данные карточки in-place без пересоздания виджета."""
        if self._lift_anim.state() == QVariantAnimation.Running:
            self._lift_anim.stop()
        if self._anim_group.state() == QParallelAnimationGroup.Running:
            self._anim_group.stop()
        self._base_y = None
        self._current_lift = 0.0
        self.is_hovered = False

        self.task = task
        self.set_selected(is_selected)

        # 1. Предмет
        subj_name = self.task.subject_name or "КУРС"
        if self.subject_chip.text() != subj_name:
            self.subject_chip.setText(subj_name)

        # 2. Тип и номер
        type_prefix = {
            "Практическая": "ПР",
            "Лабораторная": "ЛР",
            "Курсовая": "КР",
            "Реферат": "РЕФ",
        }.get(self.task.type, self.task.type)
        type_text = f"{type_prefix} №{self.task.number}"
        if self.type_chip.text() != type_text:
            self.type_chip.setText(type_text)

        # 3. Вариант
        if self.task.variant:
            var_raw = str(self.task.variant).strip()
            var_text = var_raw if var_raw.lower().startswith("вар") else f"Вар. {var_raw}"
            if self.variant_chip is None:
                self.variant_chip = QLabel(var_text)
                self.variant_chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                styles = _get_card_subwidget_styles(self.theme)
                self.variant_chip.setStyleSheet(styles["task_variant_chip"])
                if hasattr(self, "top_row"):
                    self.top_row.insertWidget(2, self.variant_chip)
            else:
                if self.variant_chip.text() != var_text:
                    self.variant_chip.setText(var_text)
                self.variant_chip.show()
        elif self.variant_chip is not None:
            self.variant_chip.hide()

        # 4. Дедлайн
        self._update_deadline_badge()

        # 5. Заголовок
        if self.title_label.text() != self.task.title:
            self.title_label.setText(self.task.title)

        # 6. Статус комбо
        self.status_combo.blockSignals(True)
        idx = self.status_combo.findData(self.task.status)
        if idx >= 0 and self.status_combo.currentIndex() != idx:
            self.status_combo.setCurrentIndex(idx)
        self.status_combo.blockSignals(False)

        # 7. Прогресс
        if self.progress_bar.value() != self.task.progress_percent:
            self.progress_bar.setValue(self.task.progress_percent)
        pct_text = f"{self.task.progress_percent}%"
        if self.pct_label.text() != pct_text:
            self.pct_label.setText(pct_text)

    def _update_card_style(self) -> None:
        """Стилизует подложку карточки работы в чистом стиле Zero-Border."""
        if not hasattr(self, "_style_normal"):
            self._init_styles()
        target = self._style_selected if self.is_selected else (self._style_hover if self.is_hovered else self._style_normal)
        if getattr(self, "_current_card_style", None) != target:
            self._current_card_style = target
            self.setStyleSheet(target)

    def enterEvent(self, event) -> None:
        """Наведение курсора: подсветка грани и прыгучий подъем тени (Spring Overshoot)."""
        self.is_hovered = True
        self._shadow.setEnabled(True)
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
        """Прыгучая физика (Spring Bounce) через QEasingCurve.OutBack с нулевыми аллокациями."""
        self._target_is_hover = is_hover
        if is_hover or self.is_selected:
            self._shadow.setEnabled(True)
        if self._anim_group.state() == QParallelAnimationGroup.Running:
            self._anim_group.stop()

        is_dark = self.theme.get("is_dark", True)
        target_blur = 28.0 if is_hover else 12.0
        target_y = 8.0 if is_hover else 3.0
        target_alpha = (85 if is_hover else 55) if is_dark else (48 if is_hover else 22)
        easing = QEasingCurve.OutBack if is_hover else QEasingCurve.OutQuad

        self._anim_blur.setStartValue(self._shadow.blurRadius())
        self._anim_blur.setEndValue(target_blur)
        self._anim_blur.setEasingCurve(easing)

        self._anim_y_offset.setStartValue(self._shadow.yOffset())
        self._anim_y_offset.setEndValue(target_y)
        self._anim_y_offset.setEasingCurve(easing)

        self._shadow.setColor(QColor(0, 0, 0, target_alpha))
        self._anim_group.start()

        # Физический вертикальный подъём (Spring Lift -4px OutBack)
        if self._lift_anim.state() == QVariantAnimation.Running:
            self._lift_anim.stop()

        if self._base_y is None:
            self._base_y = self.y() - int(self._current_lift)

        target_lift = -4.0 if is_hover else 0.0
        self._lift_anim.setDuration(220 if is_hover else 180)
        self._lift_anim.setStartValue(self._current_lift)
        self._lift_anim.setEndValue(target_lift)
        self._lift_anim.setEasingCurve(QEasingCurve.OutBack if is_hover else QEasingCurve.OutCubic)
        self._lift_anim.start()

    def _on_lift_step(self, val: float) -> None:
        self._current_lift = val
        if self._base_y is not None:
            new_y = self._base_y + int(val)
            if self.y() != new_y:
                self._is_internal_lift_move = True
                try:
                    self.move(self.x(), new_y)
                finally:
                    self._is_internal_lift_move = False

    def _on_lift_done(self) -> None:
        if not self._target_is_hover:
            if self._base_y is not None and self.y() != self._base_y:
                self._is_internal_lift_move = True
                try:
                    self.move(self.x(), self._base_y)
                finally:
                    self._is_internal_lift_move = False
            self._base_y = None
            self._current_lift = 0.0

    def _init_ui(self) -> None:
        self._update_card_style()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        # ----------------------------------------------------------------------
        # Верхний ряд: Чипы предмета, типа/номера, варианта и дедлайна
        # ----------------------------------------------------------------------
        self.top_row = QHBoxLayout()
        self.top_row.setSpacing(8)
        self.top_row.setContentsMargins(0, 0, 0, 0)

        # 1. Капсульный чип предмета
        subj_name = self.task.subject_name or "КУРС"
        self.subject_chip = QLabel(subj_name)
        self.subject_chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.top_row.addWidget(self.subject_chip)

        # 2. Чип типа и номера (ЛР №1, ПР №2)
        type_prefix = {
            "Практическая": "ПР",
            "Лабораторная": "ЛР",
            "Курсовая": "КР",
            "Реферат": "РЕФ",
        }.get(self.task.type, self.task.type)
        self.type_chip = QLabel(f"{type_prefix} №{self.task.number}")
        self.type_chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.top_row.addWidget(self.type_chip)

        # 3. Чип варианта (Вар. 11, если указан)
        self.variant_chip: Optional[QLabel] = None
        if self.task.variant:
            var_raw = str(self.task.variant).strip()
            var_text = var_raw if var_raw.lower().startswith("вар") else f"Вар. {var_raw}"
            self.variant_chip = QLabel(var_text)
            self.variant_chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.top_row.addWidget(self.variant_chip)

        self.top_row.addStretch()

        # 4. Семантический чип дедлайна
        self.deadline_badge = QLabel()
        self.deadline_badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.top_row.addWidget(self.deadline_badge)

        self._update_badges()
        self._update_deadline_badge()
        main_layout.addLayout(self.top_row)

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
        styles = _get_card_subwidget_styles(self.theme)

        # Чип предмета
        sc = styles["task_subj_chip"]
        if getattr(self.subject_chip, "_cached_qss", None) != sc:
            self.subject_chip.setStyleSheet(sc)
            self.subject_chip._cached_qss = sc

        # Чип типа и номера
        tc = styles["task_type_chip"]
        if getattr(self.type_chip, "_cached_qss", None) != tc:
            self.type_chip.setStyleSheet(tc)
            self.type_chip._cached_qss = tc

        # Чип варианта
        if self.variant_chip:
            vc = styles["task_variant_chip"]
            if getattr(self.variant_chip, "_cached_qss", None) != vc:
                self.variant_chip.setStyleSheet(vc)
                self.variant_chip._cached_qss = vc

    def _update_title_style(self) -> None:
        """Стилизует заголовок работы."""
        styles = _get_card_subwidget_styles(self.theme)
        tt = styles["task_title"]
        if getattr(self.title_label, "_cached_qss", None) != tt:
            self.title_label.setStyleSheet(tt)
            self.title_label._cached_qss = tt

    def _update_deadline_badge(self) -> None:
        """Форматирует дату дедлайна и окрашивает чип по семантическим правилам."""
        deadline_text = self._format_deadline_display(self.task.deadline_date)
        if self.deadline_badge.text() != deadline_text:
            self.deadline_badge.setText(deadline_text)

        bg_col, text_col = self._get_deadline_style()
        style_key = (bg_col, text_col)
        if getattr(self.deadline_badge, "_cached_style_key", None) != style_key:
            self.deadline_badge._cached_style_key = style_key
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
        _, fg, bg = get_md3_urgency(
            self.task.deadline_date,
            is_completed=(self.task.status == STATUS_COMPLETED),
            is_dark=is_dark,
            status=self.task.status,
        )
        return bg, fg

    def _format_deadline_display(self, deadline_str: Optional[str]) -> str:
        """Преобразует дату дедлайна в компактный пользовательский вид."""
        if self.task.status == STATUS_COMPLETED:
            return "Сдано"
        if self.task.status == STATUS_WAIT_DEFENSE:
            return "На проверке"
        if not deadline_str:
            return "Без дедлайна"

        try:
            dt_obj = parse_deadline_datetime(deadline_str)
            if dt_obj is None:
                return f"До {deadline_str}"

            delta = dt_obj - datetime.now()
            secs = delta.total_seconds()
            has_time = ":" in str(deadline_str)
            date_str = dt_obj.strftime("%d.%m %H:%M") if has_time else dt_obj.strftime("%d.%m")

            if secs < 0:
                return f"Просрочено ({date_str})"
            elif secs <= 24 * 3600:
                return f"🔥 До {date_str}"
            elif secs <= 3 * 24 * 3600:
                return f"⚠️ До {date_str}"
            else:
                return f"До {date_str}"
        except Exception:
            return f"До {deadline_str}"

    def _update_combo_style(self) -> None:
        """Стилизует выпадающий список статуса (фиксированная капсула 32px, min-width 150px) из матового стекла."""
        styles = _get_card_subwidget_styles(self.theme)
        cm = styles["task_combo"]
        if getattr(self.status_combo, "_cached_qss", None) != cm:
            self.status_combo.setFixedHeight(32)
            self.status_combo.setMinimumWidth(150)
            self.status_combo.setStyleSheet(cm)
            self.status_combo._cached_qss = cm

    def _update_progress_style(self) -> None:
        """Стилизует прогресс-бар и процентную метку."""
        styles = _get_card_subwidget_styles(self.theme)
        pb = styles["task_pb"]
        if getattr(self.progress_bar, "_cached_qss", None) != pb:
            self.progress_bar.setStyleSheet(pb)
            self.progress_bar._cached_qss = pb
        pct = styles["task_pct"]
        if getattr(self.pct_label, "_cached_qss", None) != pct:
            self.pct_label.setStyleSheet(pct)
            self.pct_label._cached_qss = pct

    def _update_folder_button_style(self) -> None:
        """Стилизует кнопку открытия папки как Material 3 Tonal Button из матового стекла."""
        styles = _get_card_subwidget_styles(self.theme)
        fb = styles["task_folder_btn"]
        if getattr(self.folder_button, "_cached_qss", None) != fb:
            self.folder_button.setFixedHeight(32)
            self.folder_button.setStyleSheet(fb)
            self.folder_button._cached_qss = fb
        self.folder_button.setIcon(get_material_icon("folder_open", color=self.theme["on_secondary"], size=16))

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

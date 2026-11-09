"""Внутриоконный модальный оверлей в стилистике Google Material Design 3 Expressive.
Отображает диалоговые окна (добавление предмета, добавление работы) внутри одного
окна Windows с полупрозрачным затемнением и плавной анимацией появления (Fade + Slide).
"""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Property, QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QApplication, QFrame, QGraphicsDropShadowEffect, QVBoxLayout, QWidget


class InWindowModalOverlay(QWidget):
    """
    Модальный оверлей, перекрывающий родительское окно без создания отдельного окна OS.
    Обеспечивает плавное появление карточки диалога по центру с эффектом Fade + Slide.
    """

    closed = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("inWindowModalOverlay")
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setGeometry(parent.rect())

        self._parent_widget = parent
        self._parent_widget.installEventFilter(self)

        # Плавная анимация прозрачности фона через paintEvent (без конфликтов вложенных QGraphicsEffect)
        self._backdrop_opacity: float = 0.0
        self._opacity_anim = QPropertyAnimation(self, b"backdrop_opacity", self)
        self._opacity_anim.finished.connect(self._on_opacity_anim_finished)
        self._is_closing = False

        # Карточка диалога
        self._current_dialog: Optional[QWidget] = None
        self._card_anim: Optional[QPropertyAnimation] = None

        self.hide()

    def get_backdrop_opacity(self) -> float:
        return self._backdrop_opacity

    def set_backdrop_opacity(self, val: float) -> None:
        self._backdrop_opacity = val
        self.update()

    backdrop_opacity = Property(float, get_backdrop_opacity, set_backdrop_opacity)

    def _on_opacity_anim_finished(self) -> None:
        if self._is_closing:
            self._is_closing = False
            self.hide()
            if self._current_dialog:
                self._current_dialog.setParent(None)
                self._current_dialog.deleteLater()
                self._current_dialog = None
            self.closed.emit()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Следит за изменением размера родительского окна и пересчитывает геометрию оверлея."""
        if watched == self._parent_widget and event.type() == QEvent.Resize:
            self.setGeometry(self._parent_widget.rect())
            if self._current_dialog and self.isVisible() and not self._is_closing:
                self._center_dialog(self._current_dialog)
        return super().eventFilter(watched, event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Отрисовывает гладкое полупрозрачное затемнение подложки окна."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        alpha = int(145 * self._backdrop_opacity)
        if alpha > 0:
            painter.fillRect(self.rect(), QColor(0, 0, 0, alpha))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Блокирует клики сквозь полупрозрачный фон в нижележащие элементы интерфейса.
        В отличие от временных меню, диалог формы ввода НЕ закрывается случайным кликом по фону.
        """
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def keyPressEvent(self, event) -> None:
        """Нажатие Escape закрывает модальное окно."""
        if event.key() == Qt.Key_Escape:
            self.close_animated()
            event.accept()
        else:
            super().keyPressEvent(event)

    def show_dialog(self, dialog: QWidget) -> None:
        """Помещает диалог в центр оверлея и запускает красивую анимацию появления."""
        self._is_closing = False
        self._current_dialog = dialog
        dialog.setParent(self)
        dialog.setWindowFlags(Qt.Widget)

        # Применяем мягкую тень карточке (работает стабильно без конфликта с родительским эффектом)
        shadow = QGraphicsDropShadowEffect(dialog)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 80))
        dialog.setGraphicsEffect(shadow)

        self.setGeometry(self._parent_widget.rect())
        self.raise_()
        self.show()

        # Центрируем карточку
        target_rect = self._calc_centered_rect(dialog)
        start_rect = QRect(target_rect.x(), target_rect.y() + 20, target_rect.width(), target_rect.height())
        dialog.setGeometry(start_rect)
        dialog.show()

        # Анимация затемнения подложки (Fade In)
        self._opacity_anim.stop()
        self._opacity_anim.setDuration(220)
        self._opacity_anim.setStartValue(self._backdrop_opacity)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._opacity_anim.start()

        # Анимация всплытия карточки (Slide Up)
        if self._card_anim is not None:
            self._card_anim.stop()
            self._card_anim.deleteLater()
        self._card_anim = QPropertyAnimation(dialog, b"geometry", self)
        self._card_anim.setDuration(240)
        self._card_anim.setStartValue(start_rect)
        self._card_anim.setEndValue(target_rect)
        self._card_anim.setEasingCurve(QEasingCurve.OutBack)
        self._card_anim.start()

        # Передаем фокус первому полю ввода
        dialog.setFocus()

    def close_animated(self) -> None:
        """Плавно скрывает оверлей и карточку."""
        if not self.isVisible() or self._is_closing:
            return

        self._is_closing = True
        self._opacity_anim.stop()
        self._opacity_anim.setDuration(160)
        self._opacity_anim.setStartValue(self._backdrop_opacity)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.InQuad)
        self._opacity_anim.start()

        if self._current_dialog is not None:
            if self._card_anim is not None:
                self._card_anim.stop()
                self._card_anim.deleteLater()
            cur_rect = self._current_dialog.geometry()
            down_rect = QRect(cur_rect.x(), cur_rect.y() + 16, cur_rect.width(), cur_rect.height())
            self._card_anim = QPropertyAnimation(self._current_dialog, b"geometry", self)
            self._card_anim.setDuration(160)
            self._card_anim.setStartValue(cur_rect)
            self._card_anim.setEndValue(down_rect)
            self._card_anim.setEasingCurve(QEasingCurve.InQuad)
            self._card_anim.start()

    def _calc_centered_rect(self, widget: QWidget) -> QRect:
        """Вычисляет центрированный прямоугольник с учетом минимальных и рекомендуемых размеров."""
        parent_size = self.size()
        pref_size = widget.sizeHint()

        min_w = max(420, widget.minimumWidth())
        min_h = max(340, widget.minimumHeight())

        w = min(parent_size.width() - 40, max(min_w, pref_size.width()))
        h = min(parent_size.height() - 40, max(min_h, pref_size.height()))

        x = (parent_size.width() - w) // 2
        y = (parent_size.height() - h) // 2
        return QRect(x, y, w, h)

    def _center_dialog(self, widget: QWidget) -> None:
        widget.setGeometry(self._calc_centered_rect(widget))

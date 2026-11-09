"""Главное окно приложения UniVault в стилистике Google Material Design 3 Expressive & Pixel Monet.
Zero-Border архитектура, аппаратное матовое стекло Windows 11 DWM Acrylic, реактивный движок тем.
"""

from __future__ import annotations

import math
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    Signal,
    QTimer,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..database import (
    Database,
    STATUS_COMPLETED,
    STATUS_LABELS,
    STATUS_WAIT_DEFENSE,
    Subject,
    Task,
    is_deadline_hot,
    parse_deadline_datetime,
)
from ..fs_manager import FSManager
from .cards import SubjectCard, SubjectCardWidget, TaskCard, TaskCardWidget, ThemeSwatchButton
from .dialogs import AddSubjectDialog, AddTaskDialog, SettingsDialog
from .file_inspector import TaskInspectorWidget
from .icons import get_material_icon, get_material_pixmap
from .modal_overlay import InWindowModalOverlay
from .settings_page import SettingsPageWidget
from .theme import (
    DEFAULT_MODE,
    DEFAULT_THEME,
    PIXEL_THEMES,
    PIXEL_THEMES_DARK,
    PIXEL_THEMES_LIGHT,
    apply_windows_acrylic,
    get_md3_urgency,
    get_stylesheet,
    get_theme,
    load_application_fonts,
)


# Предварительно сгенерированная таблица псевдослучайного шума (зернистости)
import random as _random
_rng = _random.Random(1337)
_ORGANIC_NOISE_SAMPLES: List[Tuple[float, float, float, float]] = []
for _i in range(160):
    _angle = (_i / 160.0) * (2.0 * math.pi) + (_rng.random() - 0.5) * 0.08
    _radial_offset = (_rng.random() - 0.5) * 26.0
    _dot_size = _rng.uniform(1.2, 2.6)
    _alpha_factor = _rng.uniform(0.35, 0.85)
    _ORGANIC_NOISE_SAMPLES.append((_angle, _radial_offset, _dot_size, _alpha_factor))


class ThemeRippleOverlay(QWidget):
    """
    Матовый волнообразный оверлей кругового раскрытия темы (Frosted Organic Wave).
    Отображает снимок предыдущей темы с живым органическим волновым контуром,
    многослойным матовым рассеиванием и текстурным шумом (матовой зернистостью).
    """

    def __init__(
        self,
        parent: QWidget,
        old_pixmap: QPixmap,
        origin: QPoint,
        accent_color: QColor,
        duration_ms: int = 540,
        on_finished: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.old_pixmap = old_pixmap
        self.origin = origin
        self.accent_color = accent_color
        self.on_finished = on_finished
        self._progress = 0.0

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setGeometry(parent.rect())

        w = float(parent.width())
        h = float(parent.height())
        corners = [
            (0.0, 0.0),
            (w, 0.0),
            (0.0, h),
            (w, h),
        ]
        self.max_radius = max(
            math.hypot(cx - float(origin.x()), cy - float(origin.y()))
            for cx, cy in corners
        ) + 35.0

        # Используем предрассчитанную константную таблицу органического шума без накладных расходов
        self._noise_samples = _ORGANIC_NOISE_SAMPLES

        self.anim = QPropertyAnimation(self, b"progress", self)
        self.anim.setDuration(duration_ms)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self._cleanup)

        self.show()
        self.raise_()
        self.anim.start()

    @Property(float)
    def progress(self) -> float:
        return self._progress

    @progress.setter
    def progress(self, val: float) -> None:
        self._progress = val
        self.update()

    def stop(self) -> None:
        if hasattr(self, "anim") and self.anim:
            self.anim.stop()

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._progress >= 1.0 or self.old_pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        current_radius = self._progress * self.max_radius

        # 1. Формируем контур подложки со скруглением 28px
        full_path = QPainterPath()
        full_path.addRoundedRect(QRectF(self.rect()), 28.0, 28.0)

        # 2. Формируем живой органический волновой контур раскрытия новой темы
        wave_path = QPainterPath()
        num_points = 96
        first = True
        ox = float(self.origin.x())
        oy = float(self.origin.y())

        for i in range(num_points + 1):
            theta = (i % num_points) * (2.0 * math.pi / num_points)
            # Органические гармоники создают живую форму волны вместо резкого круга
            ripple = (
                4.8 * math.sin(6.0 * theta + self._progress * 7.0)
                + 2.8 * math.cos(11.0 * theta - self._progress * 5.0)
                + 1.5 * math.sin(19.0 * theta + 1.2)
            )
            r = max(0.0, current_radius + ripple)
            px = ox + r * math.cos(theta)
            py = oy + r * math.sin(theta)
            if first:
                wave_path.moveTo(px, py)
                first = False
            else:
                wave_path.lineTo(px, py)
        wave_path.closeSubpath()

        # Зона отображения старой темы (все кроме раскрывшейся волны)
        old_theme_path = QPainterPath()
        old_theme_path.setFillRule(Qt.FillRule.OddEvenFill)
        old_theme_path.addPath(full_path)
        old_theme_path.addPath(wave_path)

        painter.save()
        painter.setClipPath(old_theme_path)
        painter.drawPixmap(0, 0, self.old_pixmap)
        painter.restore()

        # 3. Отрисовка матовой, рассеянной и шумной линии волны
        if current_radius > 2.0:
            painter.save()
            painter.setClipPath(full_path)

            fade_alpha = int(220 * (1.0 - (self._progress ** 1.35)))
            if fade_alpha > 0:
                # --- А. Матовые диффузные полосы (мягкое рассеивание без резкой лески) ---
                # Широкий внешний матовый ореол (глубокая полутень)
                halo1_color = QColor(self.accent_color)
                halo1_color.setAlpha(int(fade_alpha * 0.18))
                painter.setPen(QPen(halo1_color, 26.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(wave_path)

                # Средняя матовая полоса свечения
                halo2_color = QColor(self.accent_color)
                halo2_color.setAlpha(int(fade_alpha * 0.35))
                painter.setPen(QPen(halo2_color, 12.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.drawPath(wave_path)

                # Основной мягкий матовый валик волны
                crest_color = QColor(self.accent_color)
                crest_color.setAlpha(int(fade_alpha * 0.70))
                painter.setPen(QPen(crest_color, 4.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.drawPath(wave_path)

                # Вторичная мягкая волновая рябь (эхо) позади фронта
                if current_radius > 28.0:
                    echo_color = QColor(self.accent_color)
                    echo_color.setAlpha(int(fade_alpha * 0.28))
                    painter.setPen(QPen(echo_color, 3.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    painter.drawEllipse(QPointF(self.origin), current_radius - 22.0, current_radius - 22.0)

                # --- Б. Текстурный шум (матовая зернистость на гребне волны) ---
                painter.setPen(Qt.NoPen)
                for angle, rad_off, dot_sz, a_factor in self._noise_samples:
                    local_ripple = (
                        4.8 * math.sin(6.0 * angle + self._progress * 7.0)
                        + 2.8 * math.cos(11.0 * angle - self._progress * 5.0)
                    )
                    r_noise = max(0.0, current_radius + local_ripple + rad_off)
                    nx = ox + r_noise * math.cos(angle)
                    ny = oy + r_noise * math.sin(angle)

                    grain_alpha = max(0, min(255, int(fade_alpha * a_factor)))
                    grain_color = QColor(255, 255, 255) if rad_off > 0 else QColor(self.accent_color)
                    grain_color.setAlpha(grain_alpha)

                    painter.setBrush(grain_color)
                    painter.drawEllipse(QPointF(nx, ny), dot_sz, dot_sz)

            painter.restore()

    def _cleanup(self) -> None:
        if self.on_finished:
            self.on_finished()
        self.deleteLater()


class MainWindow(QMainWindow):
    """
    Главное окно приложения UniVault.
    Трехколоночная плавающая композиция Material 3 Expressive поверх Windows 11 Acrylic.
    """

    def __init__(self, db: Database, fs: FSManager) -> None:
        super().__init__()
        self.db = db
        self.fs = fs

        # 1. Загрузка сохраненной темы Monet и режима оформления (Dark/Light) из SQLite
        saved_theme = self.db.get_setting("theme_name", DEFAULT_THEME)
        self.current_theme_key: str = (
            saved_theme if (saved_theme in PIXEL_THEMES_DARK or saved_theme in PIXEL_THEMES_LIGHT or saved_theme.startswith("custom")) else DEFAULT_THEME
        )
        saved_mode = self.db.get_setting("theme_mode", DEFAULT_MODE)
        self.current_theme_mode: str = saved_mode if saved_mode in ("dark", "light") else DEFAULT_MODE
        saved_opacity = float(self.db.get_setting("panel_opacity", "1.0") or 1.0)
        self.current_opacity: float = max(0.35, min(1.0, saved_opacity))
        self.current_custom_color: str = self.db.get_setting("custom_theme_color", "#8AB4F8")
        self.theme: Dict[str, Any] = get_theme(
            self.current_theme_key,
            mode=self.current_theme_mode,
            custom_color=self.current_custom_color,
            opacity=self.current_opacity,
        )

        # 2. Состояние приложения
        self.current_subject_id: Optional[int] = None
        self.is_dashboard_mode: bool = False
        self.selected_task: Optional[Task] = None
        self.subject_cards: List[SubjectCard] = []
        self.task_cards: List[TaskCard] = []
        self.theme_swatches: Dict[str, ThemeSwatchButton] = {}
        self._active_ripple: Optional[ThemeRippleOverlay] = None
        self._section_anim: Optional[QVariantAnimation] = None
        self._inspector_anim: Optional[QPropertyAnimation] = None
        self._inspector_slide_anim: Optional[QVariantAnimation] = None
        self._tasks_opacity_effect: Optional[QGraphicsOpacityEffect] = None
        self._hero_opacity_effect: Optional[QGraphicsOpacityEffect] = None
        self._is_quitting: bool = False
        self._last_notified_tiers: Dict[int, str] = {}
        self._last_notified_timestamps: Dict[int, datetime] = {}
        self._last_notified_task_id: Optional[int] = None
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.notification_timer: Optional[QTimer] = None

        # 3. Базовая конфигурация окна
        self.setWindowTitle("UniVault — Academic Workspace")
        self.resize(1320, 860)
        self.setMinimumSize(1040, 680)

        # 4. Применяем глобальную Zero-Border QSS таблицу стилей
        app = QApplication.instance()
        stylesheet = get_stylesheet(
            self.current_theme_key,
            mode=self.current_theme_mode,
            custom_color=self.current_custom_color,
            opacity=self.current_opacity,
        )
        if app:
            app.setStyleSheet(stylesheet)
        else:
            self.setStyleSheet(stylesheet)

        # 5. Инициализация интерфейса и загрузка данных
        self._init_ui()
        self.load_subjects()
        self.load_tasks()

        # 6. Включение аппаратного матового стекла Windows 11 DWM Acrylic
        apply_windows_acrylic(self, is_dark=(self.current_theme_mode == "dark"))

        # 7. Системный трей Windows и фоновый таймер проверки дедлайнов (Шаг 5)
        self._init_tray_icon()
        self._init_notification_timer()

    def showEvent(self, event) -> None:
        """Повторный вызов Acrylic при показе окна для гарантированного эффекта DWM."""
        super().showEvent(event)
        apply_windows_acrylic(self, is_dark=(self.current_theme_mode == "dark"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._active_ripple is not None:
            self._active_ripple.setGeometry(self.center_widget.rect())
        if hasattr(self, "modal_overlay") and self.modal_overlay is not None:
            self.modal_overlay.setGeometry(self.rect())

    def paintEvent(self, event: QPaintEvent) -> None:
        """Отрисовывает атмосферный матовый рассеянный фон (Frosted Glass Ambient Mesh).
        Кэширует объект линейного градиента для исключения аллокаций при частых перерисовках.
        """
        super().paintEvent(event)
        painter = QPainter(self)

        w = float(self.width())
        h = float(self.height())
        is_dark = (self.current_theme_mode == "dark")
        op = getattr(self, "current_opacity", 1.0)
        top_str = self.theme.get("ambient_top", "#251E34" if is_dark else "#F4EBFC")
        bot_str = self.theme.get("ambient_bottom", "#14101E" if is_dark else "#ECE0F8")

        cache_key = (w, h, is_dark, op, top_str, bot_str)
        if getattr(self, "_cached_grad_key", None) != cache_key:
            from PySide6.QtGui import QLinearGradient
            grad = QLinearGradient(0.0, 0.0, w, h)
            top_col = QColor(top_str)
            bot_col = QColor(bot_str)
            top_col.setAlpha(int(150 * op) if is_dark else int(50 + 50 * op))
            bot_col.setAlpha(int(130 * op) if is_dark else int(40 + 45 * op))
            grad.setColorAt(0.0, top_col)
            grad.setColorAt(0.50, bot_col)
            grad.setColorAt(1.0, top_col)
            self._cached_grad = grad
            self._cached_grad_key = cache_key

        painter.fillRect(event.rect(), self._cached_grad)

    # ==========================================================================
    # Инициализация компоновки (Центральная подложка для всего окна)
    # ==========================================================================

    def _init_ui(self) -> None:
        # Корневой контейнер с прозрачным фоном для эффекта Acrylic
        self.root_container = QWidget()
        self.root_container.setObjectName("rootContainer")
        self.root_container.setStyleSheet("QWidget#rootContainer { background: transparent; border: none; }")
        self.setCentralWidget(self.root_container)

        root_layout = QHBoxLayout(self.root_container)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(0)

        # Главная центральная подложка (Center Canvas Backdrop) с матовым стеклом
        self.center_widget = QFrame()
        self.center_widget.setObjectName("centerCard")
        self.center_widget.setStyleSheet(
            f"""
            QFrame#centerCard {{
                background-color: {self.theme['center_bg']};
                border-radius: 28px;
                border: none;
            }}
            """
        )
        root_layout.addWidget(self.center_widget)

        # Контейнер внутри подложки с воздушными отступами
        backdrop_layout = QHBoxLayout(self.center_widget)
        backdrop_layout.setContentsMargins(10, 10, 10, 10)
        backdrop_layout.setSpacing(10)

        self.main_splitter = QSplitter(Qt.Horizontal, self.center_widget)
        self.main_splitter.setHandleWidth(0)
        self.main_splitter.setStyleSheet("QSplitter::handle { background: transparent; width: 0px; height: 0px; border: none; }")
        backdrop_layout.addWidget(self.main_splitter)

        # 1. Левая колонка (Navigation Drawer — 290px), расположенная поверх подложки
        self.sidebar_widget = self._create_sidebar()
        self.main_splitter.addWidget(self.sidebar_widget)

        # 2. Центральный стек страниц (Workspace + Вкладка Настроек)
        self.center_stack = QStackedWidget(self.center_widget)
        self.center_stack.setObjectName("centerStack")
        self.center_stack.setStyleSheet("QStackedWidget#centerStack { background: transparent; border: none; }")

        self.workspace_content = self._create_center_panel()
        self.center_stack.addWidget(self.workspace_content)

        self.settings_page = SettingsPageWidget(
            db=self.db,
            fs=self.fs,
            theme=self.theme,
            theme_key=self.current_theme_key,
            mode=self.current_theme_mode,
            custom_color=self.current_custom_color,
            opacity=self.current_opacity,
            parent=self.center_stack,
        )
        self.settings_page.back_clicked.connect(self._close_settings_page)
        self.settings_page.theme_updated.connect(self._on_settings_theme_updated)
        self.center_stack.addWidget(self.settings_page)

        self.main_splitter.addWidget(self.center_stack)

        # 3. Правая колонка (Inspector Sheet — 415px), расположенная поверх подложки
        self.right_widget = self._create_right_panel()
        self.main_splitter.addWidget(self.right_widget)

        # Начальные пропорции сплиттера: инспектор скрыт, пока не выбрана практическая работа
        self.right_widget.hide()
        self.right_widget.setFixedWidth(0)
        self.main_splitter.setSizes([290, 1030, 0])
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)
        self.main_splitter.setCollapsible(2, True)

        # 4. Внутриоконный модальный оверлей для диалогов (без отдельных окон OS)
        self.modal_overlay = InWindowModalOverlay(self)

    # ==========================================================================
    # 1. Левая колонка: Navigation Drawer (290px)
    # ==========================================================================

    def _create_sidebar(self) -> QWidget:
        widget = QFrame()
        widget.setObjectName("sidebarCard")
        widget.setFixedWidth(290)
        is_dark = self.current_theme_mode == "dark"
        widget.setStyleSheet(
            f"""
            QFrame#sidebarCard {{
                background-color: {self.theme['panel_bg']};
                border-radius: 24px;
                border: none;
            }}
            """
        )
        self._sidebar_shadow = QGraphicsDropShadowEffect(widget)
        self._sidebar_shadow.setBlurRadius(22)
        self._sidebar_shadow.setOffset(0, 4)
        self._sidebar_shadow.setColor(QColor(0, 0, 0, 45) if is_dark else QColor(20, 10, 40, 10))
        widget.setGraphicsEffect(self._sidebar_shadow)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # 1.1 Сводный дашборд «Горящие дедлайны» (Шаг 5)
        self.dashboard_btn = QPushButton("Горящие дедлайны")
        self.dashboard_btn.setCursor(Qt.PointingHandCursor)
        self.dashboard_btn.setFixedHeight(48)
        self._style_dashboard_btn()
        self.dashboard_btn.clicked.connect(self._select_dashboard)
        layout.addWidget(self.dashboard_btn)

        # 1.2 Навигационная таблетка «Все практические работы»
        self.all_tasks_btn = QPushButton("Все практические работы")
        self.all_tasks_btn.setCursor(Qt.PointingHandCursor)
        self.all_tasks_btn.setFixedHeight(48)
        self._style_all_tasks_btn()
        self.all_tasks_btn.clicked.connect(self._select_all_tasks)
        layout.addWidget(self.all_tasks_btn)

        # 1.3 Кнопка Настроек (включая настройку тем Google Pixel Monet и шаблонов)
        self.settings_btn = QPushButton("Настройки и шаблоны")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setFixedHeight(42)
        self._style_settings_btn()
        self.settings_btn.clicked.connect(self._open_settings_dialog)
        layout.addWidget(self.settings_btn)

        # 1.3 Заголовок секции предметов + Tonal кнопка «Добавить»
        subj_header = QHBoxLayout()
        self.subj_title = QLabel("ПРЕДМЕТЫ")
        self.subj_title.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.theme['text_secondary']}; letter-spacing: 1px; border: none; background: transparent;"
        )
        subj_header.addWidget(self.subj_title)
        subj_header.addStretch()

        self.add_subj_btn = QPushButton("Добавить")
        self.add_subj_btn.setCursor(Qt.PointingHandCursor)
        self.add_subj_btn.setFixedHeight(28)
        self._style_add_subj_btn()
        self.add_subj_btn.clicked.connect(self._open_add_subject_dialog)
        subj_header.addWidget(self.add_subj_btn)
        layout.addLayout(subj_header)

        # 1.4 Скролл-список карточек предметов
        self.subjects_scroll = QScrollArea()
        self.subjects_scroll.setWidgetResizable(True)
        self.subjects_scroll.setStyleSheet("background: transparent; border: none;")

        self.subjects_container = QWidget()
        self.subjects_container.setStyleSheet("background: transparent; border: none;")
        self.subjects_layout = QVBoxLayout(self.subjects_container)
        self.subjects_layout.setContentsMargins(0, 8, 0, 4)
        self.subjects_layout.setSpacing(10)
        self.subjects_layout.addStretch()

        self.subjects_scroll.setWidget(self.subjects_container)
        layout.addWidget(self.subjects_scroll, 1)

        # 1.5 Низ панели: Тональная капсульная кнопка корневой директории
        self.ws_info_btn = QPushButton("Корневая папка")
        self.ws_info_btn.setToolTip(str(self.fs.root_path))
        self.ws_info_btn.setCursor(Qt.PointingHandCursor)
        self.ws_info_btn.setFixedHeight(36)
        self._style_ws_info_btn()
        self.ws_info_btn.clicked.connect(lambda: self.fs.open_path_in_explorer(self.fs.root_path))
        layout.addWidget(self.ws_info_btn)

        return widget

    # ==========================================================================
    # 2. Центральная рабочая область (на центральной подложке)
    # ==========================================================================

    def _create_center_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("workspaceContent")
        widget.setStyleSheet("QWidget#workspaceContent { background: transparent; border: none; }")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        # 2.1 Hero Header: Заголовок, Статистика и Extended FAB
        hero_row = QHBoxLayout()
        hero_row.setSpacing(12)

        self.hero_text_container = QWidget()
        self.hero_text_container.setStyleSheet("background: transparent; border: none;")
        self.hero_text_layout = QVBoxLayout(self.hero_text_container)
        self.hero_text_layout.setContentsMargins(0, 0, 0, 0)
        self.hero_text_layout.setSpacing(4)

        self.center_title = QLabel("Все практические работы")
        self.center_title.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {self.theme['text_primary']}; letter-spacing: -0.5px; border: none; background: transparent;"
        )
        self.center_stats = QLabel("Загрузка...")
        self.center_stats.setStyleSheet(
            f"font-size: 13px; color: {self.theme['text_secondary']}; border: none; background: transparent;"
        )

        self.hero_text_layout.addWidget(self.center_title)
        self.hero_text_layout.addWidget(self.center_stats)
        hero_row.addWidget(self.hero_text_container)
        hero_row.addStretch()

        # M3 Extended FAB (+ Новая работа)
        self.add_task_btn = QPushButton("+ Новая работа")
        self.add_task_btn.setProperty("primary", "true")
        self.add_task_btn.setCursor(Qt.PointingHandCursor)
        self.add_task_btn.setFixedHeight(44)
        self._style_add_task_btn()
        self.add_task_btn.clicked.connect(self._open_add_task_dialog)
        hero_row.addWidget(self.add_task_btn)

        layout.addLayout(hero_row)

        # 2.2 Панель фильтрации (Поисковая капсула + Селектор статусов)
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("SearchBar")
        self.search_edit.setFixedHeight(44)
        self.search_edit.setPlaceholderText("Поиск по названию или теме...")
        self._search_action = self.search_edit.addAction(
            get_material_icon("search", color=self.theme["text_secondary"], size=18),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)
        self._search_timer.timeout.connect(self.load_tasks)
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        filter_row.addWidget(self.search_edit, 2)

        self.status_filter_combo = QComboBox()
        self.status_filter_combo.setFixedHeight(44)
        self.status_filter_combo.addItem("Все статусы", userData=None)
        self.status_filter_combo.addItem("Все активные", userData="ACTIVE")
        self.status_filter_combo.addItem("🔥 Только горящие", userData="HOT")
        for key, label in STATUS_LABELS.items():
            self.status_filter_combo.addItem(label, userData=key)
        self.status_filter_combo.currentIndexChanged.connect(self.load_tasks)
        filter_row.addWidget(self.status_filter_combo, 1)

        layout.addLayout(filter_row)

        # 2.3 Скролл-список карточек задач
        self.tasks_scroll = QScrollArea()
        self.tasks_scroll.setWidgetResizable(True)
        self.tasks_scroll.setStyleSheet("background: transparent; border: none;")

        self.tasks_container = QWidget()
        self.tasks_container.setStyleSheet("background: transparent; border: none;")
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(0, 8, 0, 6)
        self.tasks_layout.setSpacing(12)
        self.tasks_layout.addStretch()

        self._tasks_opacity_effect = None
        self._hero_opacity_effect = None

        self.tasks_scroll.setWidget(self.tasks_container)
        layout.addWidget(self.tasks_scroll, 1)

        return widget

    # ==========================================================================
    # 3. Правая колонка: Inspector Sheet (480px)
    # ==========================================================================

    TARGET_INSPECTOR_WIDTH = 480

    def _create_right_panel(self) -> QWidget:
        widget = QFrame()
        widget.setObjectName("rightInspector")
        widget.setFixedWidth(self.TARGET_INSPECTOR_WIDTH)
        is_dark = self.current_theme_mode == "dark"
        widget.setStyleSheet(
            f"""
            QFrame#rightInspector {{
                background-color: {self.theme['panel_bg']};
                border-radius: 24px;
                border: none;
            }}
            """
        )
        self._inspector_shadow = QGraphicsDropShadowEffect(widget)
        self._inspector_shadow.setBlurRadius(22)
        self._inspector_shadow.setOffset(0, 4)
        self._inspector_shadow.setColor(QColor(0, 0, 0, 45) if is_dark else QColor(20, 10, 40, 10))
        widget.setGraphicsEffect(self._inspector_shadow)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(18, 20, 16, 18)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.inspector_header = QLabel("Инспектор")
        self.inspector_header.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {self.theme['text_primary']}; border: none; background: transparent;"
        )
        header_row.addWidget(self.inspector_header)
        header_row.addStretch()

        self.inspector_close_btn = QPushButton("✕")
        self.inspector_close_btn.setToolTip("Закрыть панель инспектора")
        self.inspector_close_btn.setFixedSize(28, 28)
        self.inspector_close_btn.setCursor(Qt.PointingHandCursor)
        self._style_inspector_close_btn()
        self.inspector_close_btn.clicked.connect(self._on_close_inspector_btn_clicked)
        header_row.addWidget(self.inspector_close_btn)

        layout.addLayout(header_row)

        # Скролл-область содержимого инспектора
        self.inspector_scroll = QScrollArea()
        self.inspector_scroll.setWidgetResizable(True)
        self.inspector_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.inspector_scroll.setStyleSheet(
            f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.2)')};
                min-height: 24px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            """
        )

        self.inspector_content = QWidget()
        self.inspector_content.setMinimumWidth(0)
        self.inspector_content.setStyleSheet("background: transparent; border: none;")
        self.inspector_layout = QVBoxLayout(self.inspector_content)
        self.inspector_layout.setContentsMargins(0, 0, 4, 0)
        self.inspector_layout.setSpacing(14)

        self._show_inspector_empty_state()

        self._style_inspector_scroll()
        self.inspector_scroll.setWidget(self.inspector_content)
        layout.addWidget(self.inspector_scroll, 1)

        return widget

    def _style_inspector_scroll(self) -> None:
        if not hasattr(self, "inspector_scroll"):
            return
        handle_bg = self.theme.get("primary", "#8AB4F8")
        is_dark = (self.current_theme_mode == "dark")
        handle_color = QColor(handle_bg)
        handle_rgba = f"rgba({handle_color.red()}, {handle_color.green()}, {handle_color.blue()}, 110)" if is_dark else f"rgba({handle_color.red()}, {handle_color.green()}, {handle_color.blue()}, 140)"
        handle_hover_rgba = f"rgba({handle_color.red()}, {handle_color.green()}, {handle_color.blue()}, 180)"
        self.inspector_scroll.setStyleSheet(
            f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {handle_rgba};
                min-height: 28px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {handle_hover_rgba};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            """
        )

    def _style_inspector_close_btn(self) -> None:
        if not hasattr(self, "inspector_close_btn"):
            return
        self.inspector_close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme['text_secondary']};
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.1)')};
                color: {self.theme['text_primary']};
            }}
            """
        )

    def _show_inspector_empty_state(self) -> None:
        """Отображает минималистичное состояние, когда ни одна задача не выбрана."""
        if hasattr(self, "inspector_widget") and self.inspector_widget is not None:
            self.inspector_widget.hide()

        if not hasattr(self, "_inspector_empty_box") or self._inspector_empty_box is None:
            empty_box = QWidget()
            empty_box.setStyleSheet("background: transparent; border: none;")
            empty_layout = QVBoxLayout(empty_box)
            empty_layout.setContentsMargins(10, 80, 10, 40)
            empty_layout.setSpacing(10)
            empty_layout.setAlignment(Qt.AlignCenter)

            self._inspector_empty_title = QLabel("Работа не выбрана")
            self._inspector_empty_title.setAlignment(Qt.AlignCenter)
            self._inspector_empty_title.setStyleSheet(
                f"font-size: 16px; font-weight: 600; color: {self.theme['text_primary']}; border: none; background: transparent;"
            )

            self._inspector_empty_desc = QLabel("Выберите практическую работу из центрального списка для доступа к файлам и заметкам")
            self._inspector_empty_desc.setWordWrap(True)
            self._inspector_empty_desc.setAlignment(Qt.AlignCenter)
            self._inspector_empty_desc.setStyleSheet(
                f"font-size: 12px; color: {self.theme['text_secondary']}; line-height: 1.5; border: none; background: transparent;"
            )

            empty_layout.addWidget(self._inspector_empty_title)
            empty_layout.addWidget(self._inspector_empty_desc)
            self.inspector_layout.insertWidget(0, empty_box)
            self._inspector_empty_box = empty_box
        else:
            self._inspector_empty_box.show()

    # ==========================================================================
    # Стилизация кнопок под активную палитру Monet
    # ==========================================================================

    def _style_settings_btn(self, is_active: Optional[bool] = None) -> None:
        if is_active is None:
            is_active = (hasattr(self, "center_stack") and self.center_stack.currentIndex() == 1)
        is_dark = self.current_theme_mode == "dark"

        bg = self.theme["secondary_container"] if is_active else "transparent"
        fg = self.theme["primary"] if is_active else self.theme["text_primary"]
        border_col = self.theme["primary"] if is_active else "transparent"
        border_rule = f"1.5px solid {border_col}" if is_active else "none"
        weight = "700" if is_active else "500"

        icon = get_material_icon("settings", color=fg, size=20)
        self.settings_btn.setIcon(icon)
        hover_bg = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.06)"
        pressed_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.10)"
        self.settings_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: {border_rule};
                border-radius: 24px;
                min-height: 48px;
                max-height: 48px;
                padding: 0 18px;
                font-weight: {weight};
                font-size: 14px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: {self.theme['primary']};
                border: 1px solid {self.theme['primary']};
                border-radius: 24px;
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
                border: {border_rule};
                border-radius: 24px;
            }}
            """
        )

    def _style_dashboard_btn(self, is_active: Optional[bool] = None) -> None:
        """Стилизует кнопку дашборда горящих дедлайнов с динамическим бейджем количества."""
        if is_active is None:
            is_active = (
                getattr(self, "is_dashboard_mode", False)
                and (not hasattr(self, "center_stack") or self.center_stack.currentIndex() == 0)
            )
        is_dark = (self.current_theme_mode == "dark")

        try:
            hot_count = self.db.get_deadline_stats()["hot_count"]
        except Exception:
            hot_count = 0

        btn_text = f"Горящие дедлайны ({hot_count})" if hot_count > 0 else "Горящие дедлайны"
        self.dashboard_btn.setText(btn_text)

        bg = self.theme["secondary_container"] if is_active else "transparent"
        fg = self.theme["primary"] if is_active else self.theme["text_primary"]
        border_col = self.theme["primary"] if is_active else "transparent"
        border_rule = f"1.5px solid {border_col}" if is_active else "none"
        weight = "700" if is_active else "500"

        icon_col = self.theme["primary"] if is_active else ("#FFB4AB" if is_dark else "#BA1A1A")
        icon = get_material_icon("whatshot", color=icon_col, size=20)
        self.dashboard_btn.setIcon(icon)
        hover_bg = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.06)"
        pressed_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.10)"
        self.dashboard_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: {border_rule};
                border-radius: 24px;
                min-height: 48px;
                max-height: 48px;
                padding: 0 18px;
                font-weight: {weight};
                font-size: 14px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border: 1px solid {self.theme['primary']};
                border-radius: 24px;
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
                border: {border_rule};
                border-radius: 24px;
            }}
            """
        )

    def _style_all_tasks_btn(self) -> None:
        is_dark = self.current_theme_mode == "dark"
        is_selected = (
            self.current_subject_id is None
            and not getattr(self, "is_dashboard_mode", False)
            and (not hasattr(self, "center_stack") or self.center_stack.currentIndex() == 0)
        )
        bg = self.theme["secondary_container"] if is_selected else "transparent"
        fg = self.theme["primary"] if is_selected else self.theme["text_primary"]
        border_col = self.theme["primary"] if is_selected else "transparent"
        border_rule = f"1.5px solid {border_col}" if is_selected else "none"
        weight = "700" if is_selected else "500"

        icon = get_material_icon("assignment", color=fg, size=20)
        self.all_tasks_btn.setIcon(icon)
        hover_bg = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.06)"
        pressed_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.10)"
        self.all_tasks_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: {border_rule};
                border-radius: 24px;
                min-height: 48px;
                max-height: 48px;
                padding: 0 18px;
                font-weight: {weight};
                font-size: 14px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border: 1px solid {self.theme['primary']};
                border-radius: 24px;
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
                border: {border_rule};
                border-radius: 24px;
            }}
            """
        )

    def _style_add_task_btn(self) -> None:
        icon = get_material_icon("add", color=self.theme["on_primary"], size=18)
        self.add_task_btn.setIcon(icon)
        self.add_task_btn.setText("Новая работа")
        is_dark = self.current_theme_mode == "dark"
        hover_bg = self.theme.get("primary_hover", self.theme["primary"])
        pressed_bg = "rgba(255, 255, 255, 0.70)" if is_dark else "rgba(0, 0, 0, 0.15)"
        self.add_task_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme['primary']};
                color: {self.theme['on_primary']};
                border: none;
                border-radius: 22px;
                min-height: 44px;
                max-height: 44px;
                padding: 0 20px;
                font-weight: 700;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border: none;
                border-radius: 22px;
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
                border: none;
                border-radius: 22px;
            }}
            """
        )

    def _style_add_subj_btn(self) -> None:
        icon = get_material_icon("add", color=self.theme["primary"], size=14)
        self.add_subj_btn.setIcon(icon)
        self.add_subj_btn.setText("Добавить")
        is_dark = self.current_theme_mode == "dark"
        hover_bg = "rgba(255, 255, 255, 0.22)" if is_dark else "rgba(0, 0, 0, 0.08)"
        hover_color = "#FFFFFF" if is_dark else self.theme["primary"]
        pressed_bg = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
        self.add_subj_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme['secondary_container']};
                color: {self.theme['primary']};
                border: none;
                border-radius: 14px;
                min-height: 28px;
                max-height: 28px;
                padding: 0 12px;
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: {hover_color};
                border: 1px solid {self.theme['primary']};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
                border: none;
            }}
            """
        )

    def _style_ws_info_btn(self) -> None:
        icon = get_material_icon("folder_open", color=self.theme["primary"], size=16)
        self.ws_info_btn.setIcon(icon)
        is_dark = self.current_theme_mode == "dark"
        hover_bg = "rgba(255, 255, 255, 0.22)" if is_dark else "rgba(0, 0, 0, 0.08)"
        hover_color = "#FFFFFF" if is_dark else self.theme["primary"]
        pressed_bg = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
        self.ws_info_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme['secondary_container']};
                color: {self.theme['primary']};
                border: none;
                border-radius: 18px;
                min-height: 36px;
                max-height: 36px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: {hover_color};
                border: 1px solid {self.theme['primary']};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
                border: none;
            }}
            """
        )

    def _open_settings_dialog(self) -> None:
        """Открывает настройки как внутреннюю вкладку в центральной области и скрывает инспектор."""
        if hasattr(self, "center_stack"):
            self.selected_task = None
            for card in self.task_cards:
                card.set_selected(False)
            self._close_inspector_animated()
            self.right_widget.setFixedWidth(0)
            self.right_widget.hide()
            if hasattr(self, "main_splitter"):
                sidebar_w = self.sidebar_widget.width() if hasattr(self, "sidebar_widget") else 290
                total_w = self.main_splitter.width()
                if total_w > 0:
                    self.main_splitter.setSizes([sidebar_w, max(100, total_w - sidebar_w), 0])
            self.center_stack.setCurrentIndex(1)
            self._style_settings_btn(is_active=True)
            self._style_all_tasks_btn()
            self._style_dashboard_btn(is_active=False)
            for card in self.subject_cards:
                card.set_selected(False)

    def _close_settings_page(self) -> None:
        """Возвращает к рабочей области с практическими работами."""
        if hasattr(self, "center_stack"):
            self.center_stack.setCurrentIndex(0)
            self._style_settings_btn(is_active=False)
            self._style_all_tasks_btn()
            self._style_dashboard_btn()
            if self.current_subject_id is not None:
                for card in self.subject_cards:
                    card.set_selected(card.subject.id == self.current_subject_id)

    def _on_settings_theme_updated(
        self,
        theme_key: str,
        mode: str,
        custom_color: str,
        opacity: float,
    ) -> None:
        self.set_active_theme(
            theme_key=theme_key,
            mode=mode,
            custom_color=custom_color,
            opacity=opacity,
        )

    # ==========================================================================
    # Переключение тем Google Pixel Monet
    # ==========================================================================

    def set_active_theme(
        self,
        theme_key: str,
        mode: Optional[str] = None,
        custom_color: Optional[str] = None,
        opacity: Optional[float] = None,
    ) -> None:
        """Реактивно переключает тему оформления без перезапуска программы."""
        if mode in ("dark", "light"):
            self.current_theme_mode = mode
        if custom_color:
            self.current_custom_color = custom_color
            self.db.set_setting("custom_theme_color", self.current_custom_color)
        if opacity is not None:
            self.current_opacity = max(0.35, min(1.0, float(opacity)))
            self.db.set_setting("panel_opacity", str(self.current_opacity))

        if theme_key in PIXEL_THEMES_DARK or theme_key in PIXEL_THEMES_LIGHT or theme_key.startswith("custom"):
            self.current_theme_key = theme_key

        self.theme = get_theme(
            self.current_theme_key,
            mode=self.current_theme_mode,
            custom_color=self.current_custom_color,
            opacity=self.current_opacity,
        )
        self.db.set_setting("theme_name", self.current_theme_key)
        self.db.set_setting("theme_mode", self.current_theme_mode)

        self.setUpdatesEnabled(False)
        try:
            # 1. Обновляем глобальный QSS
            app = QApplication.instance()
            stylesheet = get_stylesheet(
                self.current_theme_key,
                mode=self.current_theme_mode,
                custom_color=self.current_custom_color,
                opacity=self.current_opacity,
            )
            if app:
                if app.styleSheet() != stylesheet:
                    app.setStyleSheet(stylesheet)
            else:
                if self.styleSheet() != stylesheet:
                    self.setStyleSheet(stylesheet)

            # Обновляем нативное матовое стекло DWM Acrylic для окна
            apply_windows_acrylic(self, is_dark=(self.current_theme_mode == "dark"))

            # 2. Обновляем фоны подложки и боковых панелей в чистом стиле Zero-Border
            is_dark = (self.current_theme_mode == "dark")
            self.center_widget.setStyleSheet(
                f"QFrame#centerCard {{ background-color: {self.theme['center_bg']}; border-radius: 28px; border: none; }}"
            )
            self.sidebar_widget.setStyleSheet(
                f"QFrame#sidebarCard {{ background-color: {self.theme['panel_bg']}; border-radius: 24px; border: none; }}"
            )
            self.right_widget.setStyleSheet(
                f"QFrame#rightInspector {{ background-color: {self.theme['panel_bg']}; border-radius: 24px; border: none; }}"
            )

            if hasattr(self, "settings_page"):
                self.settings_page.apply_theme(self.theme, mode=self.current_theme_mode)

            if hasattr(self, "_sidebar_shadow"):
                self._sidebar_shadow.setColor(QColor(0, 0, 0, 45) if is_dark else QColor(20, 10, 40, 10))
            if hasattr(self, "_inspector_shadow"):
                self._inspector_shadow.setColor(QColor(0, 0, 0, 45) if is_dark else QColor(20, 10, 40, 10))

            # 3. Обновляем заголовки и стилизованные кнопки
            self.center_title.setStyleSheet(
                f"font-size: 28px; font-weight: 700; color: {self.theme['text_primary']}; letter-spacing: -0.5px; border: none; background: transparent;"
            )
            self.center_stats.setStyleSheet(
                f"font-size: 13px; color: {self.theme['text_secondary']}; border: none; background: transparent;"
            )
            self.inspector_header.setStyleSheet(
                f"font-size: 18px; font-weight: 700; color: {self.theme['text_primary']}; border: none; background: transparent;"
            )
            if hasattr(self, "subj_title"):
                self.subj_title.setStyleSheet(
                    f"font-size: 11px; font-weight: 700; color: {self.theme['text_secondary']}; letter-spacing: 1px; border: none; background: transparent;"
                )

            if hasattr(self, "settings_btn"):
                self._style_settings_btn()
            if hasattr(self, "dashboard_btn"):
                self._style_dashboard_btn()
            self._style_all_tasks_btn()
            self._style_add_task_btn()
            self._style_add_subj_btn()
            self._style_ws_info_btn()
            self._style_inspector_close_btn()
            self._style_inspector_scroll()
            if hasattr(self, "tray_icon") and self.tray_icon:
                tray_pix = get_material_pixmap("school", color=self.theme.get("primary", "#8AB4F8"), size=32)
                self.tray_icon.setIcon(QIcon(tray_pix))
            if hasattr(self, "_search_action") and self._search_action:
                self._search_action.setIcon(
                    get_material_icon("search", color=self.theme["text_secondary"], size=18)
                )

            # 4. Обновляем кольца активности и цвета на свотчах Monet
            for key, swatch in self.theme_swatches.items():
                palette = get_theme(key, mode=self.current_theme_mode)
                swatch.set_swatch_color(palette["swatch"])
                swatch.set_is_dark(self.current_theme_mode == "dark")
                swatch.set_selected(key == self.current_theme_key)

            # 5. Реактивно перекрашиваем все карточки в списках
            for scard in self.subject_cards:
                scard.apply_theme(self.theme, mode=self.current_theme_mode)

            for tcard in self.task_cards:
                tcard.apply_theme(self.theme, mode=self.current_theme_mode)

            # 6. Обновляем инспектор
            if hasattr(self, "inspector_widget") and self.inspector_widget is not None:
                self.inspector_widget.apply_theme(self.theme, self.current_theme_mode)

            if self.selected_task:
                self._update_inspector(self.selected_task)
            else:
                self._show_inspector_empty_state()
                if hasattr(self, "_inspector_empty_title") and self._inspector_empty_title is not None:
                    self._inspector_empty_title.setStyleSheet(
                        f"font-size: 16px; font-weight: 600; color: {self.theme['text_primary']}; border: none; background: transparent;"
                    )
                    self._inspector_empty_desc.setStyleSheet(
                        f"font-size: 12px; color: {self.theme['text_secondary']}; line-height: 1.5; border: none; background: transparent;"
                    )

            self.update()
        finally:
            self.setUpdatesEnabled(True)

    def trigger_theme_transition(self, theme_key: str, mode: Optional[str] = None) -> None:
        """
        Запускает плавный волнообразный Circular Reveal переход на новую тему Monet.
        Волна акцентного света и новая палитра исходят радиально из кликнутого свотча или кнопки режима.
        """
        target_mode = mode if mode in ("dark", "light") else self.current_theme_mode
        if theme_key == self.current_theme_key and target_mode == self.current_theme_mode:
            return
        if theme_key not in PIXEL_THEMES_DARK and theme_key not in PIXEL_THEMES_LIGHT:
            return

        # Если окно скрыто или в offscreen/headless окружении — мгновенное переключение
        if (
            not self.isVisible()
            or self.width() <= 10
            or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
        ):
            self.set_active_theme(theme_key, mode=target_mode)
            return

        # Точные координаты центра кликнутого свотча относительно центральной подложки
        swatch_btn = self.theme_swatches.get(theme_key)
        if swatch_btn and swatch_btn.isVisible():
            origin = swatch_btn.mapTo(
                self.center_widget,
                QPoint(swatch_btn.width() // 2, swatch_btn.height() // 2),
            )
        elif hasattr(self, "settings_btn") and self.settings_btn.isVisible():
            origin = self.settings_btn.mapTo(
                self.center_widget,
                QPoint(self.settings_btn.width() // 2, self.settings_btn.height() // 2),
            )
        else:
            origin = QPoint(self.center_widget.width() // 2, self.center_widget.height() // 2)

        # 1. Захватываем пиксельный снимок текущей темы перед переключением
        old_pixmap = self.center_widget.grab()

        # 2. Мгновенно применяем новую тему к стилям всех дочерних виджетов
        self.set_active_theme(theme_key, mode=target_mode)

        # 3. Завершаем предыдущую анимацию, если она была активна
        if self._active_ripple is not None:
            try:
                self._active_ripple.stop()
                self._active_ripple.deleteLater()
            except Exception:
                pass
            self._active_ripple = None

        # 4. Создаем волнообразный оверлей кругового раскрытия
        new_palette = get_theme(theme_key, mode=target_mode)
        accent_color = QColor(new_palette["primary"])

        self._active_ripple = ThemeRippleOverlay(
            parent=self.center_widget,
            old_pixmap=old_pixmap,
            origin=origin,
            accent_color=accent_color,
            duration_ms=500,
            on_finished=self._on_ripple_finished,
        )

    def _on_ripple_finished(self) -> None:
        """Callback завершения анимации волнового оверлея."""
        self._active_ripple = None

    def _on_search_text_changed(self, text: str) -> None:
        """Дебаунсинг текстового поиска (150 мс) для исключения перестроения дерева виджетов на каждый символ."""
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            self.load_tasks()
        else:
            self._search_timer.start()

    # ==========================================================================
    # Загрузка данных (Предметы и Задачи)
    # ==========================================================================

    def load_subjects(self) -> None:
        """Перезагружает или обновляет кастомные карточки предметов в левой панели с in-place переиспользованием."""
        subjects = self.db.get_subjects()

        self.subjects_container.setUpdatesEnabled(False)
        try:
            if not subjects:
                while self.subjects_layout.count() > 1:
                    child = self.subjects_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                self.subject_cards.clear()

                empty_lbl = QLabel("Нет добавленных предметов")
                empty_lbl.setStyleSheet(f"color: {self.theme['text_muted']}; font-size: 12px; padding: 16px; border: none; background: transparent;")
                empty_lbl.setAlignment(Qt.AlignCenter)
                self.subjects_layout.insertWidget(0, empty_lbl)
                return

            # Если ранее была показана пустая плашка (не карточка), удаляем ее
            if self.subjects_layout.count() > 1 and not isinstance(self.subjects_layout.itemAt(0).widget(), SubjectCard):
                child = self.subjects_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            existing_count = len(self.subject_cards)
            new_count = len(subjects)

            # 1. Обновляем общие карточки in-place
            common_count = min(existing_count, new_count)
            for i in range(common_count):
                subj = subjects[i]
                card = self.subject_cards[i]
                is_sel = (self.current_subject_id == subj.id)
                card.update_subject_data(subj, is_selected=is_sel)
                card.setVisible(True)

            # 2. Если предметов больше, создаем недостающие
            if new_count > existing_count:
                for i in range(existing_count, new_count):
                    subj = subjects[i]
                    is_sel = (self.current_subject_id == subj.id)
                    card = SubjectCard(subj, is_selected=is_sel, theme_key=self.current_theme_key, mode=self.current_theme_mode)
                    card.apply_theme(self.theme, mode=self.current_theme_mode)
                    card.clicked.connect(self._on_subject_clicked)
                    self.subject_cards.append(card)
                    self.subjects_layout.insertWidget(i, card)
                    card.show()

            # 3. Если предметов меньше, удаляем лишние
            elif existing_count > new_count:
                for _ in range(existing_count - new_count):
                    card = self.subject_cards.pop()
                    self.subjects_layout.removeWidget(card)
                    card.deleteLater()
        finally:
            self.subjects_container.setUpdatesEnabled(True)

    def load_tasks(self) -> None:
        """Загружает карточки задач в центральный список с быстрым in-place обновлением."""
        status_filter = self.status_filter_combo.currentData()
        search_query = self.search_edit.text().strip() or None

        if getattr(self, "is_dashboard_mode", False):
            # Режим сводного дашборда: все активные работы по всем предметам,
            # отсортированные по близости дедлайна (срочные и просроченные наверху)
            tasks = self.db.get_tasks(
                subject_id=None,
                status_filter=status_filter if status_filter else "ACTIVE",
                search_query=search_query,
                order_by_deadline=True,
                only_hot=(status_filter == "HOT"),
            )
            self.center_title.setText("Горящие дедлайны")
            d_stats = self.db.get_deadline_stats()
            self.center_stats.setText(
                f"Просрочено: {d_stats['overdue']}  •  Осталось <24ч: {d_stats['critical_24h']}  •  "
                f"Осталось <3д: {d_stats['warning_3d']}  •  Всего активных: {d_stats['total_active']}"
            )
        elif self.current_subject_id is None:
            tasks = self.db.get_tasks(
                subject_id=None,
                status_filter=status_filter,
                search_query=search_query,
                only_hot=(status_filter == "HOT"),
            )
            self.center_title.setText("Все практические работы")
            total_cnt = len(tasks)
            completed_cnt = sum(1 for t in tasks if t.status == STATUS_COMPLETED)
            in_progress_cnt = total_cnt - completed_cnt
            self.center_stats.setText(
                f"Всего: {total_cnt}  •  В работе: {in_progress_cnt}  •  Сдано: {completed_cnt}"
            )
        else:
            subj = self.db.get_subject(self.current_subject_id)
            tasks = self.db.get_tasks(
                subject_id=self.current_subject_id,
                status_filter=status_filter,
                search_query=search_query,
                only_hot=(status_filter == "HOT"),
            )
            if subj:
                self.center_title.setText(subj.name)
            total_cnt = len(tasks)
            completed_cnt = sum(1 for t in tasks if t.status == STATUS_COMPLETED)
            in_progress_cnt = total_cnt - completed_cnt
            self.center_stats.setText(
                f"Всего: {total_cnt}  •  В работе: {in_progress_cnt}  •  Сдано: {completed_cnt}"
            )

        # Обновляем динамический бейдж на кнопке дашборда в боковом меню
        if hasattr(self, "dashboard_btn"):
            try:
                hot_cnt = self.db.get_deadline_stats()["hot_count"]
                self.dashboard_btn.setText(f"Горящие дедлайны ({hot_cnt})" if hot_cnt > 0 else "Горящие дедлайны")
            except Exception:
                pass

        self.tasks_container.setUpdatesEnabled(False)
        try:
            if not tasks:
                while self.tasks_layout.count() > 1:
                    child = self.tasks_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                self.task_cards.clear()

                empty_lbl = QLabel("Нет практических работ по выбранным критериям")
                empty_lbl.setAlignment(Qt.AlignCenter)
                empty_lbl.setStyleSheet(f"color: {self.theme['text_muted']}; font-size: 13px; padding: 60px; border: none; background: transparent;")
                self.tasks_layout.insertWidget(0, empty_lbl)
                return

            # Если ранее была показана пустая плашка (не карточка), удаляем ее
            if self.tasks_layout.count() > 1 and not isinstance(self.tasks_layout.itemAt(0).widget(), TaskCard):
                child = self.tasks_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            existing_count = len(self.task_cards)
            new_count = len(tasks)

            # 1. Обновляем общие карточки in-place
            common_count = min(existing_count, new_count)
            for i in range(common_count):
                task = tasks[i]
                card = self.task_cards[i]
                is_sel = (self.selected_task is not None and self.selected_task.id == task.id)
                card.update_task_data(task, is_selected=is_sel)
                card.setVisible(True)

            # 2. Если задач больше, создаем недостающие
            if new_count > existing_count:
                for i in range(existing_count, new_count):
                    task = tasks[i]
                    is_sel = (self.selected_task is not None and self.selected_task.id == task.id)
                    card = TaskCard(task, is_selected=is_sel, theme_key=self.current_theme_key, mode=self.current_theme_mode)
                    card.apply_theme(self.theme, mode=self.current_theme_mode)
                    card.clicked.connect(self._on_task_card_clicked)
                    card.status_changed.connect(self._on_task_status_changed)
                    card.open_folder_requested.connect(self._on_open_task_folder)
                    self.task_cards.append(card)
                    self.tasks_layout.insertWidget(i, card)
                    card.show()

            # 3. Если задач меньше, удаляем лишние
            elif existing_count > new_count:
                for _ in range(existing_count - new_count):
                    card = self.task_cards.pop()
                    self.tasks_layout.removeWidget(card)
                    card.deleteLater()
        finally:
            self.tasks_container.setUpdatesEnabled(True)

    # ==========================================================================
    # Обработчики событий и навигации
    # ==========================================================================

    def _animate_section_switch(self) -> None:
        """
        Плавная анимация переключения разделов (Fade-In + Spring Slide).
        Мягко переводит фокус, анимируя прозрачность и микро-смещение карточек и заголовка.
        После завершения анимации эффекты прозрачности снимаются (setGraphicsEffect(None)),
        чтобы карточки задач со своими тенями не исчезали при наведении мыши.
        """
        # 1. Завершаем активную анимацию раздела, если она выполняется
        if hasattr(self, "_section_anim") and self._section_anim is not None:
            try:
                self._section_anim.stop()
            except Exception:
                pass
            self._section_anim = None
            if hasattr(self, "tasks_container") and self.tasks_container:
                self.tasks_container.setGraphicsEffect(None)
            if hasattr(self, "hero_text_container") and self.hero_text_container:
                self.hero_text_container.setGraphicsEffect(None)
            self._tasks_opacity_effect = None
            self._hero_opacity_effect = None

        # 2. Сбрасываем скролл наверх и загружаем задачи нового раздела
        self.tasks_scroll.verticalScrollBar().setValue(0)
        self.load_tasks()

        # 3. Для offscreen/headless режима пропускаем визуальную анимацию
        if not self.isVisible() or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            if hasattr(self, "tasks_container") and self.tasks_container:
                self.tasks_container.setGraphicsEffect(None)
            if hasattr(self, "hero_text_container") and self.hero_text_container:
                self.hero_text_container.setGraphicsEffect(None)
            return

        # 4. Инициализируем временные эффекты прозрачности на время анимации
        self._tasks_opacity_effect = QGraphicsOpacityEffect(self.tasks_container)
        self.tasks_container.setGraphicsEffect(self._tasks_opacity_effect)

        self._hero_opacity_effect = QGraphicsOpacityEffect(self.hero_text_container)
        self.hero_text_container.setGraphicsEffect(self._hero_opacity_effect)

        # 5. Начальное состояние: нулевая прозрачность
        self._tasks_opacity_effect.setOpacity(0.0)
        self._hero_opacity_effect.setOpacity(0.0)

        # 6. Запускаем пружинящую интерполяцию (0.0 -> 1.0)
        self._section_anim = QVariantAnimation(self)
        self._section_anim.setDuration(180)
        self._section_anim.setStartValue(0.0)
        self._section_anim.setEndValue(1.0)
        self._section_anim.setEasingCurve(QEasingCurve.OutCubic)

        last_y = [-1]

        def _on_step(val: float) -> None:
            if hasattr(self, "_tasks_opacity_effect") and self._tasks_opacity_effect:
                self._tasks_opacity_effect.setOpacity(val)
            if hasattr(self, "_hero_opacity_effect") and self._hero_opacity_effect:
                self._hero_opacity_effect.setOpacity(val)
            y_offset = int((1.0 - val) * 14)
            if y_offset != last_y[0]:
                last_y[0] = y_offset
                self.tasks_layout.setContentsMargins(0, 8 + y_offset, 0, 6)
                if hasattr(self, "hero_text_layout"):
                    self.hero_text_layout.setContentsMargins(0, int((1.0 - val) * 6), 0, 0)

        def _on_done() -> None:
            # Снимаем QGraphicsOpacityEffect после завершения перехода, восстанавливая
            # прямое аппаратное рисование виджетов без конфликта с дочерними QGraphicsDropShadowEffect
            if hasattr(self, "tasks_container") and self.tasks_container:
                self.tasks_container.setGraphicsEffect(None)
            if hasattr(self, "hero_text_container") and self.hero_text_container:
                self.hero_text_container.setGraphicsEffect(None)
            self._tasks_opacity_effect = None
            self._hero_opacity_effect = None

            self.tasks_layout.setContentsMargins(0, 8, 0, 6)
            if hasattr(self, "hero_text_layout"):
                self.hero_text_layout.setContentsMargins(0, 0, 0, 0)
            self._section_anim = None

        self._section_anim.valueChanged.connect(_on_step)
        self._section_anim.finished.connect(_on_done)
        self._section_anim.start()

    def _select_dashboard(self, close_inspector: bool = True) -> None:
        """Переключает центральную область в режим сводного дашборда горящих дедлайнов."""
        if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 1:
            self._close_settings_page()
        if close_inspector:
            self.selected_task = None
            for card in self.task_cards:
                card.set_selected(False)
            self._close_inspector_animated()
        self.is_dashboard_mode = True
        self.current_subject_id = None
        self._style_dashboard_btn(is_active=True)
        self._style_all_tasks_btn()
        for card in self.subject_cards:
            card.set_selected(False)
        self._animate_section_switch()

    def _select_all_tasks(self) -> None:
        if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 1:
            self._close_settings_page()
        self.selected_task = None
        for card in self.task_cards:
            card.set_selected(False)
        self._close_inspector_animated()
        if self.current_subject_id is None and not getattr(self, "is_dashboard_mode", False):
            return
        self.is_dashboard_mode = False
        self.current_subject_id = None
        self._style_dashboard_btn(is_active=False)
        self._style_all_tasks_btn()
        for card in self.subject_cards:
            card.set_selected(False)
        self._animate_section_switch()

    def _on_subject_clicked(self, subject_id: int) -> None:
        if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 1:
            self._close_settings_page()
        if self.current_subject_id == subject_id and not getattr(self, "is_dashboard_mode", False):
            return
        self.is_dashboard_mode = False
        self.current_subject_id = subject_id
        self._style_dashboard_btn(is_active=False)
        self._style_all_tasks_btn()
        for card in self.subject_cards:
            card.set_selected(card.subject.id == subject_id)
        self._animate_section_switch()

        # Если у выбранного предмета есть практические работы — автоматически выбираем первую и плавно раскрываем инспектор
        tasks = self.db.get_tasks(subject_id=subject_id)
        if tasks:
            first_task = tasks[0]
            self.selected_task = first_task
            for card in self.task_cards:
                card.set_selected(card.task.id == first_task.id)
            self._update_inspector(first_task)
            self._open_inspector_animated()
        else:
            self.selected_task = None
            self._close_inspector_animated()

    def _open_add_subject_dialog(self) -> None:
        dialog = AddSubjectDialog(
            parent=self.modal_overlay,
            theme_key=self.current_theme_key,
            mode=self.current_theme_mode,
        )
        self._active_dialog = dialog

        def _on_accepted():
            data = dialog.get_data()
            folder_name = self.fs.create_subject_folder(
                data["name"], data["short_name"]
            )
            self.db.add_subject(
                name=data["name"],
                short_name=data["short_name"],
                teacher_name=data["teacher_name"],
                exam_type=data["exam_type"],
                folder_path=folder_name,
                color_hex=data["color_hex"],
            )
            self.load_subjects()
            self.modal_overlay.close_animated()
            self._active_dialog = None

        def _on_rejected():
            self.modal_overlay.close_animated()
            self._active_dialog = None

        dialog.accepted.connect(_on_accepted)
        dialog.rejected.connect(_on_rejected)
        self.modal_overlay.show_dialog(dialog)

    def _open_add_task_dialog(self) -> None:
        subjects = self.db.get_subjects()
        if not subjects:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Сначала добавьте хотя бы один учебный предмет!",
            )
            self._open_add_subject_dialog()
            return

        dialog = AddTaskDialog(
            db=self.db,
            default_subject_id=self.current_subject_id,
            parent=self.modal_overlay,
            theme_key=self.current_theme_key,
            mode=self.current_theme_mode,
        )
        self._active_dialog = dialog

        def _on_accepted():
            data = dialog.get_data()
            subj = self.db.get_subject(data["subject_id"])
            if not subj:
                self.modal_overlay.close_animated()
                self._active_dialog = None
                return

            folder_name = self.fs.create_task_folders(
                subject_folder=subj.folder_path,
                number=data["number"],
                task_type=data["type"],
                title=data["title"],
            )

            self.db.add_task(
                subject_id=data["subject_id"],
                number=data["number"],
                task_type=data["type"],
                title=data["title"],
                variant=data["variant"],
                status=data["status"],
                progress_percent=0,
                deadline_date=data["deadline_date"],
                notes=data["notes"],
                folder_path=folder_name,
            )
            self.load_subjects()
            self.load_tasks()
            self.modal_overlay.close_animated()
            self._active_dialog = None

        def _on_rejected():
            self.modal_overlay.close_animated()
            self._active_dialog = None

        dialog.accepted.connect(_on_accepted)
        dialog.rejected.connect(_on_rejected)
        self.modal_overlay.show_dialog(dialog)

    def _on_task_status_changed(self, task_id: int, new_status: str) -> None:
        """Слушатель изменения статуса задачи."""
        self.db.update_task_status(task_id, new_status)
        self.load_subjects()
        # Синхронизируем карточку в центральном списке
        for card in self.task_cards:
            if card.task.id == task_id:
                prog = 100 if new_status == STATUS_COMPLETED else None
                card.update_status(new_status, progress_percent=prog)
        if self.selected_task and self.selected_task.id == task_id:
            updated = self.db.get_task(task_id)
            if updated:
                self.selected_task = updated
                if hasattr(self, "inspector_widget") and self.inspector_widget is not None and self.right_widget.isVisible():
                    subj = self.db.get_subject(updated.subject_id)
                    self.inspector_widget.update_task(updated, subj)

        # Сбрасываем уровень оповещений для измененной задачи
        if hasattr(self, "_last_notified_tiers"):
            self._last_notified_tiers.pop(task_id, None)

        # Обновляем счетчик горящих дедлайнов на кнопке бокового меню
        if hasattr(self, "dashboard_btn"):
            self._style_dashboard_btn()

        # Если находимся в дашборде или активна фильтрация по статусу — обновляем список и статистику
        curr_filter = self.status_filter_combo.currentData() if hasattr(self, "status_filter_combo") else None
        if getattr(self, "is_dashboard_mode", False) or curr_filter in ("HOT", "ACTIVE", "COMPLETED"):
            self.load_tasks()
            if self.selected_task and not any(c.task.id == self.selected_task.id for c in self.task_cards):
                self._close_inspector_animated()
                self.selected_task = None

    def _on_task_progress_changed(self, task_id: int, progress: int) -> None:
        """Слушатель изменения прогресса задачи."""
        self.db.update_task_progress(task_id, progress)
        for card in self.task_cards:
            if card.task.id == task_id:
                card.update_progress(progress)

    def _on_task_files_changed(self, task_id: int) -> None:
        """Слушатель добавления/удаления файлов в задаче."""
        pass

    def _on_task_deadline_changed(self, task_id: int, new_deadline: str) -> None:
        """Слушатель интерактивного изменения дедлайна задачи из инспектора."""
        for card in self.task_cards:
            if card.task.id == task_id:
                card.update_deadline(new_deadline)
        if hasattr(self, "_last_notified_tiers"):
            self._last_notified_tiers.pop(task_id, None)
        if hasattr(self, "_last_notified_timestamps"):
            self._last_notified_timestamps.pop(task_id, None)
        if hasattr(self, "dashboard_btn"):
            self._style_dashboard_btn()
        if getattr(self, "is_dashboard_mode", False):
            self.load_tasks()
            for card in self.task_cards:
                if card.task.id == task_id:
                    card.set_selected(True)
                    break

    def _on_open_task_folder(self, task_id: int) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        subj = self.db.get_subject(task.subject_id)
        if not subj:
            return
        task_dir = self.fs.get_task_dir(subj.folder_path, task.folder_path)
        self.fs.open_path_in_explorer(task_dir)

    def _on_task_card_clicked(self, task_id: int) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        self.selected_task = task

        for card in self.task_cards:
            card.set_selected(card.task.id == task_id)

        self._update_inspector(task)
        self._open_inspector_animated()

    def _open_inspector_animated(self) -> None:
        """Плавно раскрывает панель инспектора с анимацией изменения ширины (Width Slide-In)."""
        if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 1:
            return

        if not self.isVisible() or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            self.right_widget.show()
            self.right_widget.setFixedWidth(self.TARGET_INSPECTOR_WIDTH)
            if hasattr(self, "main_splitter"):
                sidebar_w = self.sidebar_widget.width() if hasattr(self, "sidebar_widget") else 290
                total_w = self.main_splitter.width()
                if total_w > 0:
                    center_w = max(100, total_w - sidebar_w - self.TARGET_INSPECTOR_WIDTH)
                    self.main_splitter.setSizes([sidebar_w, center_w, self.TARGET_INSPECTOR_WIDTH])
            return

        if hasattr(self, "_inspector_slide_anim") and self._inspector_slide_anim:
            try:
                self._inspector_slide_anim.stop()
            except Exception:
                pass

        if not self.right_widget.isVisible():
            self.right_widget.setFixedWidth(0)
            self.right_widget.show()

        start_w = self.right_widget.width()
        if start_w >= self.TARGET_INSPECTOR_WIDTH:
            return

        self._inspector_slide_anim = QVariantAnimation(self)
        self._inspector_slide_anim.setDuration(180)
        self._inspector_slide_anim.setStartValue(start_w)
        self._inspector_slide_anim.setEndValue(self.TARGET_INSPECTOR_WIDTH)
        self._inspector_slide_anim.setEasingCurve(QEasingCurve.OutCubic)

        last_w = [-1]

        def _on_step(val: int) -> None:
            current_w = int(val)
            if current_w == last_w[0]:
                return
            last_w[0] = current_w
            self.right_widget.setFixedWidth(current_w)
            if hasattr(self, "main_splitter"):
                sidebar_w = self.sidebar_widget.width() if hasattr(self, "sidebar_widget") else 290
                total_w = self.main_splitter.width()
                if total_w > 0:
                    center_w = max(100, total_w - sidebar_w - current_w)
                    self.main_splitter.setSizes([sidebar_w, center_w, current_w])

        def _on_done() -> None:
            self.right_widget.setFixedWidth(self.TARGET_INSPECTOR_WIDTH)
            self._inspector_slide_anim = None
            if hasattr(self, "main_splitter"):
                sidebar_w = self.sidebar_widget.width() if hasattr(self, "sidebar_widget") else 290
                total_w = self.main_splitter.width()
                if total_w > 0:
                    center_w = max(100, total_w - sidebar_w - self.TARGET_INSPECTOR_WIDTH)
                    self.main_splitter.setSizes([sidebar_w, center_w, self.TARGET_INSPECTOR_WIDTH])

        self._inspector_slide_anim.valueChanged.connect(_on_step)
        self._inspector_slide_anim.finished.connect(_on_done)
        self._inspector_slide_anim.start()

    def _close_inspector_animated(self) -> None:
        """Плавно сворачивает панель инспектора (Width Slide-Out)."""
        if hasattr(self, "_inspector_slide_anim") and self._inspector_slide_anim:
            try:
                self._inspector_slide_anim.stop()
            except Exception:
                pass
            self._inspector_slide_anim = None

        if not self.right_widget.isVisible() or self.right_widget.width() == 0:
            self.right_widget.hide()
            self.right_widget.setFixedWidth(0)
            if hasattr(self, "main_splitter"):
                sidebar_w = self.sidebar_widget.width() if hasattr(self, "sidebar_widget") else 290
                total_w = self.main_splitter.width()
                if total_w > 0:
                    self.main_splitter.setSizes([sidebar_w, max(100, total_w - sidebar_w), 0])
            return

        if not self.isVisible() or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            self.right_widget.setFixedWidth(0)
            self.right_widget.hide()
            if hasattr(self, "main_splitter"):
                sidebar_w = self.sidebar_widget.width() if hasattr(self, "sidebar_widget") else 290
                total_w = self.main_splitter.width()
                if total_w > 0:
                    self.main_splitter.setSizes([sidebar_w, max(100, total_w - sidebar_w), 0])
            return

        start_w = self.right_widget.width()
        self._inspector_slide_anim = QVariantAnimation(self)
        self._inspector_slide_anim.setDuration(160)
        self._inspector_slide_anim.setStartValue(start_w)
        self._inspector_slide_anim.setEndValue(0)
        self._inspector_slide_anim.setEasingCurve(QEasingCurve.InCubic)

        last_w = [-1]

        def _on_step(val: int) -> None:
            current_w = int(val)
            if current_w == last_w[0]:
                return
            last_w[0] = current_w
            self.right_widget.setFixedWidth(current_w)
            if hasattr(self, "main_splitter"):
                sidebar_w = self.sidebar_widget.width() if hasattr(self, "sidebar_widget") else 290
                total_w = self.main_splitter.width()
                if total_w > 0:
                    center_w = max(100, total_w - sidebar_w - current_w)
                    self.main_splitter.setSizes([sidebar_w, center_w, current_w])

        def _on_done() -> None:
            self.right_widget.setFixedWidth(0)
            self.right_widget.hide()
            self._inspector_slide_anim = None
            if hasattr(self, "main_splitter"):
                sidebar_w = self.sidebar_widget.width() if hasattr(self, "sidebar_widget") else 290
                total_w = self.main_splitter.width()
                if total_w > 0:
                    self.main_splitter.setSizes([sidebar_w, max(100, total_w - sidebar_w), 0])

        self._inspector_slide_anim.valueChanged.connect(_on_step)
        self._inspector_slide_anim.finished.connect(_on_done)
        self._inspector_slide_anim.start()

    def _on_close_inspector_btn_clicked(self) -> None:
        """Скрывает инспектор по нажатию кнопки-крестика в шапке."""
        self.selected_task = None
        for card in self.task_cards:
            card.set_selected(False)
        self._close_inspector_animated()

    # ==========================================================================
    # 4. Обновление содержимого Inspector Sheet (Шаг 3: Drag & Drop и файлы)
    # ==========================================================================

    def _update_inspector(self, task: Task) -> None:
        """Отображает интерактивный инспектор с быстрым in-place обновлением данных."""
        if hasattr(self, "_inspector_empty_box") and self._inspector_empty_box is not None:
            self._inspector_empty_box.hide()

        subj = self.db.get_subject(task.subject_id)

        if hasattr(self, "inspector_widget") and self.inspector_widget is not None:
            self.inspector_widget.apply_theme(self.theme, self.current_theme_mode)
            self.inspector_widget.update_task(task, subj)
            self.inspector_widget.show()
            return

        self.inspector_widget = TaskInspectorWidget(
            task=task,
            subject=subj,
            db=self.db,
            fs=self.fs,
            theme=self.theme,
            current_theme_mode=self.current_theme_mode,
            parent=self.inspector_content,
        )
        self.inspector_widget.task_status_changed.connect(self._on_task_status_changed)
        self.inspector_widget.task_progress_changed.connect(self._on_task_progress_changed)
        self.inspector_widget.task_files_changed.connect(self._on_task_files_changed)
        self.inspector_widget.task_deadline_changed.connect(self._on_task_deadline_changed)

        idx = max(0, self.inspector_layout.count() - 1)
        self.inspector_layout.insertWidget(idx, self.inspector_widget)
        self.inspector_widget.show()

    # ==========================================================================
    # 5. Системный трей Windows и уведомления о дедлайнах (Шаг 5)
    # ==========================================================================

    def _init_tray_icon(self) -> None:
        """Инициализирует системный трей Windows с контекстным меню и действиями."""
        self.tray_icon = QSystemTrayIcon(self)
        primary_col = self.theme.get("primary", "#8AB4F8")
        tray_pix = get_material_pixmap("school", color=primary_col, size=32)
        self.tray_icon.setIcon(QIcon(tray_pix))
        self.tray_icon.setToolTip("UniVault — Менеджер учебных задач и дедлайнов")

        tray_menu = QMenu()
        tray_menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: {self.theme.get('panel_bg', '#1E1B2E')};
                color: {self.theme.get('text_primary', '#E2E2E9')};
                border: 1px solid {self.theme.get('primary', '#8AB4F8')};
                border-radius: 12px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 6px;
                font-size: 13px;
            }}
            QMenu::item:selected {{
                background-color: {self.theme.get('secondary_container', 'rgba(255,255,255,0.1)')};
                color: {self.theme.get('primary', '#8AB4F8')};
            }}
            """
        )

        act_open = tray_menu.addAction("Открыть UniVault")
        act_open.triggered.connect(self.show_and_activate)

        act_dashboard = tray_menu.addAction("Горящие дедлайны")
        act_dashboard.triggered.connect(self._open_dashboard_from_tray)

        tray_menu.addSeparator()

        act_check = tray_menu.addAction("Проверить дедлайны")
        act_check.triggered.connect(lambda: self.check_deadlines_and_notify(force=True))

        tray_menu.addSeparator()

        act_quit = tray_menu.addAction("Выход")
        act_quit.triggered.connect(self._force_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.messageClicked.connect(self._on_tray_message_clicked)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()

        app = QApplication.instance()
        if app:
            app.setQuitOnLastWindowClosed(False)

    def _init_notification_timer(self) -> None:
        """Запускает периодическую фоновую проверку дедлайнов каждые 2 часа и при старте."""
        self.notification_timer = QTimer(self)
        self.notification_timer.setInterval(2 * 3600 * 1000)  # 2 часа = 7200000 мс
        self.notification_timer.timeout.connect(self.check_deadlines_and_notify)
        self.notification_timer.start()

        # Первичная проверка через 1.5 секунды после запуска
        QTimer.singleShot(1500, self.check_deadlines_and_notify)

    def show_and_activate(self) -> None:
        """Восстанавливает и разворачивает окно приложения на передний план."""
        self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        self.show()
        self.raise_()
        self.activateWindow()

    def _open_dashboard_from_tray(self) -> None:
        """Открывает экран горящих дедлайнов из системного трея."""
        self.show_and_activate()
        self._select_dashboard()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Обрабатывает клик пользователя по значку приложения в системном трее."""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_and_activate()

    def _on_tray_message_clicked(self) -> None:
        """При клике на системное уведомление разворачивает окно и открывает карточку нужной работы."""
        self.show_and_activate()
        if self._last_notified_task_id is not None:
            self._select_task_by_id(self._last_notified_task_id)
        else:
            self._select_dashboard()

    def _select_task_by_id(self, task_id: int) -> None:
        """Выбирает задачу по ID, отображает её в списке и открывает панель инспектора."""
        task = self.db.get_task(task_id)
        if not task:
            self._select_dashboard(close_inspector=True)
            return

        # Сбрасываем фильтры, чтобы задача гарантированно была видна
        if hasattr(self, "status_filter_combo"):
            self.status_filter_combo.blockSignals(True)
            self.status_filter_combo.setCurrentIndex(0)
            self.status_filter_combo.blockSignals(False)
        if hasattr(self, "search_edit") and self.search_edit.text():
            self.search_edit.blockSignals(True)
            self.search_edit.clear()
            self.search_edit.blockSignals(False)

        self._select_dashboard(close_inspector=False)
        self.selected_task = task
        for card in self.task_cards:
            if card.task.id == task_id:
                card.set_selected(True)
                self.tasks_scroll.ensureWidgetVisible(card)
            else:
                card.set_selected(False)
        self._update_inspector(task)
        self._open_inspector_animated()

    def check_deadlines_and_notify(self, force: bool = False) -> None:
        """
        Проверяет сроки дедлайнов всех активных работ и отправляет системное уведомление (Windows Toast).
        Условия отправки согласно спецификации:
        1. До дедлайна осталось менее 72 часов (3 дня), а статус не COMPLETED и не WAIT_DEFENSE.
        2. До дедлайна осталось менее 24 часов.
        3. Дедлайн просрочен.
        """
        notify_enabled = self.db.get_setting("notifications_enabled", "1") == "1"
        if not notify_enabled:
            return

        tasks = self.db.get_tasks(status_filter="ACTIVE", order_by_deadline=True)
        now = datetime.now()
        urgent_tasks: List[Tuple[Task, str, str, str, float]] = []

        if not hasattr(self, "_last_notified_timestamps"):
            self._last_notified_timestamps = {}
        if not hasattr(self, "_last_notified_tiers"):
            self._last_notified_tiers = {}

        for task in tasks:
            if task.status in (STATUS_COMPLETED, STATUS_WAIT_DEFENSE):
                continue
            if not task.deadline_date:
                continue
            try:
                dl = parse_deadline_datetime(task.deadline_date)
                if dl is None:
                    continue

                delta = dl - now
                secs = delta.total_seconds()

                tier: Optional[str] = None
                title: str = ""
                msg: str = ""
                subj_str = f" ({task.subject_name})" if task.subject_name else ""

                if secs < 0:
                    tier = "OVERDUE"
                    title = "⚠️ Дедлайн просрочен!"
                    msg = f"[{task.type} №{task.number}] {task.title}{subj_str}\nСрок истек: {task.deadline_date}"
                elif secs <= 24 * 3600:
                    tier = "CRITICAL"
                    if secs < 3600:
                        mins = max(1, int(secs // 60))
                        rem_str = f"~{mins} мин"
                    else:
                        hours = max(1, int(secs // 3600))
                        rem_str = f"~{hours} ч"
                    title = "🔥 Горящий дедлайн (< 24 ч)!"
                    msg = f"[{task.type} №{task.number}] {task.title}{subj_str}\nОсталось {rem_str} (до {task.deadline_date})"
                elif secs <= 72 * 3600:
                    tier = "WARNING"
                    days = max(1, int(secs // 86400))
                    title = "⏰ Приближается дедлайн (до 3 дней)"
                    msg = f"[{task.type} №{task.number}] {task.title}{subj_str}\nОсталось ~{days} дн (до {task.deadline_date})"

                if tier:
                    prev_tier = self._last_notified_tiers.get(task.id)
                    last_time = self._last_notified_timestamps.get(task.id)
                    time_elapsed = (now - last_time).total_seconds() if last_time else 1e9

                    if force or prev_tier != tier or time_elapsed >= 2 * 3600:
                        self._last_notified_tiers[task.id] = tier
                        self._last_notified_timestamps[task.id] = now
                        urgent_tasks.append((task, tier, title, msg, secs))
            except Exception:
                continue

        if not urgent_tasks:
            if force and hasattr(self, "tray_icon") and self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
                self.tray_icon.showMessage(
                    "Дедлайны в порядке",
                    "Нет горящих или просроченных задач по всем предметам.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )
            return

        # Сортируем задачи строго по степени срочности:
        # Наиболее просроченные (наименьший secs < 0), затем ближайшие (<24ч), затем (<72ч)
        urgent_tasks.sort(key=lambda item: item[4])

        target_task, top_tier, top_title, top_msg, _ = urgent_tasks[0]
        self._last_notified_task_id = target_task.id

        if hasattr(self, "tray_icon") and self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
            icon_type = (
                QSystemTrayIcon.MessageIcon.Warning
                if top_tier in ("OVERDUE", "CRITICAL")
                else QSystemTrayIcon.MessageIcon.Information
            )

            if len(urgent_tasks) == 1:
                self.tray_icon.showMessage(top_title, top_msg, icon_type, 6000)
            else:
                multi_title = f"🔥 Горящие дедлайны UniVault: {len(urgent_tasks)}"
                multi_msg = f"{top_title}\n{top_msg}\n+ еще {len(urgent_tasks) - 1} активных работ. Нажмите для перехода."
                self.tray_icon.showMessage(multi_title, multi_msg, icon_type, 6000)

    def _force_quit(self) -> None:
        """Полный выход из приложения из меню трея."""
        self._is_quitting = True
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.hide()
        self.close()
        app = QApplication.instance()
        if app:
            app.quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Перехват закрытия окна: если включена опция сворачивания в трей,
        окно скрывается, а приложение продолжает работу в фоне.
        """
        minimize_to_tray = self.db.get_setting("minimize_to_tray", "1") == "1"
        tray_available = (
            hasattr(self, "tray_icon")
            and self.tray_icon is not None
            and (QSystemTrayIcon.isSystemTrayAvailable() or os.environ.get("QT_QPA_PLATFORM") == "offscreen")
        )
        if getattr(self, "_is_quitting", False) or not minimize_to_tray or not tray_available:
            if hasattr(self, "tray_icon") and self.tray_icon:
                self.tray_icon.hide()
            event.accept()
        else:
            event.ignore()
            self.hide()
            first_tip = self.db.get_setting("tray_tip_shown", "0") != "1"
            if first_tip and hasattr(self, "tray_icon") and self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
                self.db.set_setting("tray_tip_shown", "1")
                self.tray_icon.showMessage(
                    "UniVault свернут в трей",
                    "Приложение продолжает отслеживать дедлайны в фоне. Для выхода используйте меню значка в трее.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )

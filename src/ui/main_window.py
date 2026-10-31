"""Главное окно приложения UniVault в стилистике Google Material Design 3 Expressive & Pixel Monet.
Zero-Border архитектура, аппаратное матовое стекло Windows 11 DWM Acrylic, реактивный движок тем.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QColor,
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
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..database import (
    Database,
    STATUS_COMPLETED,
    STATUS_LABELS,
    Subject,
    Task,
)
from ..fs_manager import FSManager
from .cards import SubjectCard, SubjectCardWidget, TaskCard, TaskCardWidget, ThemeSwatchButton
from .dialogs import AddSubjectDialog, AddTaskDialog, SettingsDialog
from .file_inspector import TaskInspectorWidget
from .icons import get_material_icon
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

        # Предварительно сгенерированная таблица псевдослучайного шума (зернистости)
        # Фиксированный seed обеспечивает детерминированную и красивую фактуру без задержек
        import random
        rng = random.Random(1337)
        self._noise_samples: List[Tuple[float, float, float, float]] = []
        for i in range(160):
            angle = (i / 160.0) * (2.0 * math.pi) + (rng.random() - 0.5) * 0.08
            radial_offset = (rng.random() - 0.5) * 26.0
            dot_size = rng.uniform(1.2, 2.6)
            alpha_factor = rng.uniform(0.35, 0.85)
            self._noise_samples.append((angle, radial_offset, dot_size, alpha_factor))

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
        old_theme_path = full_path.subtracted(wave_path)

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
            saved_theme if (saved_theme in PIXEL_THEMES_DARK or saved_theme in PIXEL_THEMES_LIGHT) else DEFAULT_THEME
        )
        saved_mode = self.db.get_setting("theme_mode", DEFAULT_MODE)
        self.current_theme_mode: str = saved_mode if saved_mode in ("dark", "light") else DEFAULT_MODE
        self.theme: Dict[str, Any] = get_theme(self.current_theme_key, mode=self.current_theme_mode)

        # 2. Состояние приложения
        self.current_subject_id: Optional[int] = None
        self.selected_task: Optional[Task] = None
        self.subject_cards: List[SubjectCard] = []
        self.task_cards: List[TaskCard] = []
        self.theme_swatches: Dict[str, ThemeSwatchButton] = {}
        self._active_ripple: Optional[ThemeRippleOverlay] = None
        self._section_anim: Optional[QVariantAnimation] = None
        self._inspector_anim: Optional[QPropertyAnimation] = None
        self._tasks_opacity_effect: Optional[QGraphicsOpacityEffect] = None
        self._hero_opacity_effect: Optional[QGraphicsOpacityEffect] = None

        # 3. Базовая конфигурация окна
        self.setWindowTitle("UniVault — Academic Workspace")
        self.resize(1320, 860)
        self.setMinimumSize(1040, 680)

        # 4. Применяем глобальную Zero-Border QSS таблицу стилей
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(self.current_theme_key, mode=self.current_theme_mode))
        else:
            self.setStyleSheet(get_stylesheet(self.current_theme_key, mode=self.current_theme_mode))

        # 5. Инициализация интерфейса и загрузка данных
        self._init_ui()
        self.load_subjects()
        self.load_tasks()

        # 6. Включение аппаратного матового стекла Windows 11 DWM Acrylic
        apply_windows_acrylic(self, is_dark=(self.current_theme_mode == "dark"))

    def showEvent(self, event) -> None:
        """Повторный вызов Acrylic при показе окна для гарантированного эффекта DWM."""
        super().showEvent(event)
        apply_windows_acrylic(self, is_dark=(self.current_theme_mode == "dark"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._active_ripple is not None:
            self._active_ripple.setGeometry(self.center_widget.rect())

    def paintEvent(self, event: QPaintEvent) -> None:
        """Отрисовывает атмосферный матовый рассеянный фон (Frosted Glass Ambient Mesh)."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        is_dark = (self.current_theme_mode == "dark")

        from PySide6.QtGui import QRadialGradient
        grad = QRadialGradient(w * 0.20, h * 0.16, max(w, h) * 0.95)

        top_col = QColor(self.theme.get("ambient_top", "#251E34" if is_dark else "#F4EBFC"))
        bot_col = QColor(self.theme.get("ambient_bottom", "#14101E" if is_dark else "#ECE0F8"))

        top_col.setAlpha(155 if is_dark else 140)
        bot_col.setAlpha(135 if is_dark else 120)

        grad.setColorAt(0.0, top_col)
        grad.setColorAt(0.55, bot_col)
        edge_col = QColor(top_col)
        edge_col.setAlpha(max(0, top_col.alpha() - 40))
        grad.setColorAt(1.0, edge_col)

        painter.fillRect(self.rect(), grad)

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

        # 2. Центральная рабочая область (Main Workspace), лежащая на подложке
        self.workspace_content = self._create_center_panel()
        self.main_splitter.addWidget(self.workspace_content)

        # 3. Правая колонка (Inspector Sheet — 340px), расположенная поверх подложки
        self.right_widget = self._create_right_panel()
        self.main_splitter.addWidget(self.right_widget)

        # Начальные пропорции сплиттера
        self.main_splitter.setSizes([290, 690, 340])
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)
        self.main_splitter.setCollapsible(2, False)

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

        # 1.1 Кнопка Настроек (включая настройку тем Google Pixel Monet)
        self.settings_btn = QPushButton("Настройки")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setFixedHeight(42)
        self._style_settings_btn()
        self.settings_btn.clicked.connect(self._open_settings_dialog)
        layout.addWidget(self.settings_btn)

        # 1.2 Навигационная таблетка «Все практические работы»
        self.all_tasks_btn = QPushButton("Все практические работы")
        self.all_tasks_btn.setCursor(Qt.PointingHandCursor)
        self.all_tasks_btn.setFixedHeight(48)
        self._style_all_tasks_btn()
        self.all_tasks_btn.clicked.connect(self._select_all_tasks)
        layout.addWidget(self.all_tasks_btn)

        # 1.3 Заголовок секции предметов + Tonal кнопка «Добавить»
        subj_header = QHBoxLayout()
        subj_title = QLabel("ПРЕДМЕТЫ")
        subj_title.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.theme['text_secondary']}; letter-spacing: 1px; border: none; background: transparent;"
        )
        subj_header.addWidget(subj_title)
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
        self.subjects_layout.setContentsMargins(0, 0, 0, 0)
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
        self.search_edit.addAction(
            get_material_icon("search", color=self.theme["text_secondary"], size=18),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.search_edit.textChanged.connect(self.load_tasks)
        filter_row.addWidget(self.search_edit, 2)

        self.status_filter_combo = QComboBox()
        self.status_filter_combo.setFixedHeight(44)
        self.status_filter_combo.addItem("Все статусы", userData=None)
        self.status_filter_combo.addItem("В работе", userData="ACTIVE")
        self.status_filter_combo.addItem("Сдано", userData="COMPLETED")
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
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(12)
        self.tasks_layout.addStretch()

        self._tasks_opacity_effect = None
        self._hero_opacity_effect = None

        self.tasks_scroll.setWidget(self.tasks_container)
        layout.addWidget(self.tasks_scroll, 1)

        return widget

    # ==========================================================================
    # 3. Правая колонка: Inspector Sheet (360px)
    # ==========================================================================

    def _create_right_panel(self) -> QWidget:
        widget = QFrame()
        widget.setObjectName("rightInspector")
        widget.setFixedWidth(360)
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
        layout.setContentsMargins(14, 18, 14, 16)
        layout.setSpacing(14)

        self.inspector_header = QLabel("Инспектор")
        self.inspector_header.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {self.theme['text_primary']}; border: none; background: transparent;"
        )
        layout.addWidget(self.inspector_header)

        # Скролл-область содержимого инспектора
        self.inspector_scroll = QScrollArea()
        self.inspector_scroll.setWidgetResizable(True)
        self.inspector_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.inspector_scroll.setStyleSheet("background: transparent; border: none;")

        self.inspector_content = QWidget()
        self.inspector_content.setMinimumWidth(0)
        self.inspector_content.setStyleSheet("background: transparent; border: none;")
        self.inspector_layout = QVBoxLayout(self.inspector_content)
        self.inspector_layout.setContentsMargins(0, 0, 0, 0)
        self.inspector_layout.setSpacing(14)

        self._show_inspector_empty_state()

        self.inspector_scroll.setWidget(self.inspector_content)
        layout.addWidget(self.inspector_scroll, 1)

        return widget

    def _show_inspector_empty_state(self) -> None:
        """Отображает минималистичное состояние, когда ни одна задача не выбрана."""
        while self.inspector_layout.count() > 0:
            child = self.inspector_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        empty_box = QWidget()
        empty_box.setStyleSheet("background: transparent; border: none;")
        empty_layout = QVBoxLayout(empty_box)
        empty_layout.setContentsMargins(10, 80, 10, 40)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(Qt.AlignCenter)

        empty_title = QLabel("Работа не выбрана")
        empty_title.setAlignment(Qt.AlignCenter)
        empty_title.setStyleSheet(
            f"font-size: 16px; font-weight: 600; color: {self.theme['text_primary']}; border: none; background: transparent;"
        )

        empty_desc = QLabel("Выберите практическую работу из центрального списка для доступа к файлам и заметкам")
        empty_desc.setWordWrap(True)
        empty_desc.setAlignment(Qt.AlignCenter)
        empty_desc.setStyleSheet(
            f"font-size: 12px; color: {self.theme['text_secondary']}; line-height: 1.5; border: none; background: transparent;"
        )

        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_desc)
        self.inspector_layout.addWidget(empty_box)
        self.inspector_layout.addStretch()

    # ==========================================================================
    # Стилизация кнопок под активную палитру Monet
    # ==========================================================================

    def _style_settings_btn(self) -> None:
        icon = get_material_icon("settings", color=self.theme["primary"], size=18)
        self.settings_btn.setIcon(icon)
        is_dark = self.current_theme_mode == "dark"
        hover_bg = "rgba(255, 255, 255, 0.20)" if is_dark else "rgba(255, 255, 255, 0.90)"
        hover_color = "#FFFFFF" if is_dark else self.theme["primary"]
        pressed_bg = "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.08)"
        self.settings_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme['secondary_container']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 20px;
                min-height: 40px;
                max-height: 40px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 13px;
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

    def _style_all_tasks_btn(self) -> None:
        is_dark = self.current_theme_mode == "dark"
        is_selected = (self.current_subject_id is None)
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
        dialog = SettingsDialog(
            main_window=self,
            theme_key=self.current_theme_key,
            theme_mode=self.current_theme_mode,
        )
        self.theme_swatches = dialog.theme_swatches
        dialog.exec()

    # ==========================================================================
    # Переключение тем Google Pixel Monet
    # ==========================================================================

    def set_active_theme(self, theme_key: str, mode: Optional[str] = None) -> None:
        """Реактивно переключает тему оформления без перезапуска программы."""
        if mode in ("dark", "light"):
            self.current_theme_mode = mode
        if theme_key in PIXEL_THEMES_DARK or theme_key in PIXEL_THEMES_LIGHT:
            self.current_theme_key = theme_key

        self.theme = get_theme(self.current_theme_key, mode=self.current_theme_mode)
        self.db.set_setting("theme_name", self.current_theme_key)
        self.db.set_setting("theme_mode", self.current_theme_mode)

        # 1. Обновляем глобальный QSS
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(self.current_theme_key, mode=self.current_theme_mode))
        else:
            self.setStyleSheet(get_stylesheet(self.current_theme_key, mode=self.current_theme_mode))

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

        if hasattr(self, "settings_btn"):
            self._style_settings_btn()
        self._style_all_tasks_btn()
        self._style_add_task_btn()
        self._style_add_subj_btn()
        self._style_ws_info_btn()

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
            tcard.apply_theme(self.current_theme_key, mode=self.current_theme_mode)

        # 6. Обновляем инспектор
        if self.selected_task:
            self._update_inspector(self.selected_task)

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

    # ==========================================================================
    # Загрузка данных (Предметы и Задачи)
    # ==========================================================================

    def load_subjects(self) -> None:
        """Перезагружает кастомные карточки предметов в левой панели."""
        while self.subjects_layout.count() > 1:
            child = self.subjects_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.subject_cards.clear()
        subjects = self.db.get_subjects()

        if not subjects:
            empty_lbl = QLabel("Нет добавленных предметов")
            empty_lbl.setStyleSheet(f"color: {self.theme['text_muted']}; font-size: 12px; padding: 16px; border: none; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.subjects_layout.insertWidget(0, empty_lbl)
            return

        for idx, subj in enumerate(subjects):
            is_selected = (self.current_subject_id == subj.id)
            card = SubjectCard(subj, is_selected=is_selected, theme_key=self.current_theme_key, mode=self.current_theme_mode)
            card.clicked.connect(self._on_subject_clicked)
            self.subject_cards.append(card)
            self.subjects_layout.insertWidget(idx, card)
            card.show()

    def load_tasks(self) -> None:
        """Загружает карточки задач в центральный список."""
        while self.tasks_layout.count() > 1:
            child = self.tasks_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.task_cards.clear()

        status_filter = self.status_filter_combo.currentData()
        search_query = self.search_edit.text().strip() or None

        tasks = self.db.get_tasks(
            subject_id=self.current_subject_id,
            status_filter=status_filter,
            search_query=search_query,
        )

        if self.current_subject_id is None:
            self.center_title.setText("Все практические работы")
        else:
            subj = self.db.get_subject(self.current_subject_id)
            if subj:
                self.center_title.setText(subj.name)

        total_cnt = len(tasks)
        completed_cnt = sum(1 for t in tasks if t.status == STATUS_COMPLETED)
        in_progress_cnt = sum(1 for t in tasks if t.status != STATUS_COMPLETED)
        self.center_stats.setText(
            f"Всего: {total_cnt}  •  В работе: {in_progress_cnt}  •  Сдано: {completed_cnt}"
        )

        if not tasks:
            empty_lbl = QLabel("Нет практических работ по выбранным критериям")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet(f"color: {self.theme['text_muted']}; font-size: 13px; padding: 60px; border: none; background: transparent;")
            self.tasks_layout.insertWidget(0, empty_lbl)
            return

        for idx, task in enumerate(tasks):
            is_sel = (self.selected_task is not None and self.selected_task.id == task.id)
            card = TaskCard(task, is_selected=is_sel, theme_key=self.current_theme_key, mode=self.current_theme_mode)
            card.clicked.connect(self._on_task_card_clicked)
            card.status_changed.connect(self._on_task_status_changed)
            card.open_folder_requested.connect(self._on_open_task_folder)
            self.task_cards.append(card)
            self.tasks_layout.insertWidget(idx, card)
            card.show()

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
        self._section_anim.setDuration(240)
        self._section_anim.setStartValue(0.0)
        self._section_anim.setEndValue(1.0)
        self._section_anim.setEasingCurve(QEasingCurve.OutCubic)

        def _on_step(val: float) -> None:
            if hasattr(self, "_tasks_opacity_effect") and self._tasks_opacity_effect:
                self._tasks_opacity_effect.setOpacity(val)
            if hasattr(self, "_hero_opacity_effect") and self._hero_opacity_effect:
                self._hero_opacity_effect.setOpacity(val)
            y_offset = int((1.0 - val) * 14)
            self.tasks_layout.setContentsMargins(0, y_offset, 0, 0)
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

            self.tasks_layout.setContentsMargins(0, 0, 0, 0)
            if hasattr(self, "hero_text_layout"):
                self.hero_text_layout.setContentsMargins(0, 0, 0, 0)
            self._section_anim = None

        self._section_anim.valueChanged.connect(_on_step)
        self._section_anim.finished.connect(_on_done)
        self._section_anim.start()

    def _select_all_tasks(self) -> None:
        if self.current_subject_id is None:
            return
        self.current_subject_id = None
        self._style_all_tasks_btn()
        for card in self.subject_cards:
            card.set_selected(False)
        self._show_inspector_empty_state()
        self._animate_section_switch()

    def _on_subject_clicked(self, subject_id: int) -> None:
        if self.current_subject_id == subject_id:
            return
        self.current_subject_id = subject_id
        self._style_all_tasks_btn()
        for card in self.subject_cards:
            card.set_selected(card.subject.id == subject_id)
        self._show_inspector_empty_state()
        self._animate_section_switch()

    def _open_add_subject_dialog(self) -> None:
        dialog = AddSubjectDialog(
            parent=self,
            theme_key=self.current_theme_key,
            mode=self.current_theme_mode,
        )
        if dialog.exec():
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
            parent=self,
            theme_key=self.current_theme_key,
            mode=self.current_theme_mode,
        )
        if dialog.exec():
            data = dialog.get_data()
            subj = self.db.get_subject(data["subject_id"])
            if not subj:
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

    def _on_task_progress_changed(self, task_id: int, progress: int) -> None:
        """Слушатель изменения прогресса задачи."""
        self.db.update_task_progress(task_id, progress)
        for card in self.task_cards:
            if card.task.id == task_id:
                card.update_progress(progress)

    def _on_task_files_changed(self, task_id: int) -> None:
        """Слушатель добавления/удаления файлов в задаче."""
        pass

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

    # ==========================================================================
    # 4. Обновление содержимого Inspector Sheet (Шаг 3: Drag & Drop и файлы)
    # ==========================================================================

    def _update_inspector(self, task: Task) -> None:
        """Отображает интерактивный инспектор с плавным появлением (Fade-In)."""
        while self.inspector_layout.count() > 0:
            child = self.inspector_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        subj = self.db.get_subject(task.subject_id)
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

        self.inspector_layout.addWidget(self.inspector_widget)
        self.inspector_layout.addStretch()

        if self.isVisible() and os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            inspector_effect = QGraphicsOpacityEffect(self.inspector_widget)
            self.inspector_widget.setGraphicsEffect(inspector_effect)
            self._inspector_anim = QPropertyAnimation(inspector_effect, b"opacity", self)
            self._inspector_anim.setDuration(220)
            self._inspector_anim.setStartValue(0.0)
            self._inspector_anim.setEndValue(1.0)
            self._inspector_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._inspector_anim.finished.connect(
                lambda: self.inspector_widget.setGraphicsEffect(None)
                if hasattr(self, "inspector_widget") and self.inspector_widget
                else None
            )
            self._inspector_anim.start()

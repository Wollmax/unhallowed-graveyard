"""Вкладка настроек приложения UniVault (Material Design 3 Expressive).
Открывается внутри главного окна как полноценная страница вместо отдельного окна Windows.
Включает выбор темы Monet, тёмную/светлую тему, кастомный выбор цвета через пикер с сохранением и удалением свотчей,
ползунок регулировки прозрачности интерфейса, данные студента и параметры Workspace.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..database import Database
from ..fs_manager import FSManager
from .cards import CustomThemeSwatchButton, ThemeSwatchButton
from .icons import get_material_icon, get_material_pixmap
from .theme import DEFAULT_MODE, DEFAULT_THEME, PIXEL_THEMES_DARK, get_theme


class SettingsPageWidget(QWidget):
    """Страница настроек приложения, встроенная в центральную область MainWindow."""

    back_clicked = Signal()
    theme_updated = Signal(str, str, str, float)  # theme_key, mode, custom_color, opacity
    settings_saved = Signal()

    def __init__(
        self,
        db: Database,
        fs: FSManager,
        theme: Dict[str, Any],
        theme_key: str = DEFAULT_THEME,
        mode: str = DEFAULT_MODE,
        custom_color: Optional[str] = None,
        opacity: float = 1.0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.db = db
        self.fs = fs
        self.theme = theme
        self.theme_key = theme_key
        self.mode = mode
        self.custom_color = custom_color or self.db.get_setting("custom_theme_color", "#8AB4F8")
        self.opacity = opacity

        # Загрузка сохранённых пользовательских цветов
        raw_colors = self.db.get_setting("custom_colors_list", "[]")
        try:
            self.saved_custom_colors: List[str] = json.loads(raw_colors)
            if not isinstance(self.saved_custom_colors, list):
                self.saved_custom_colors = []
        except Exception:
            self.saved_custom_colors = []

        # Гарантируем, что текущий активный кастомный цвет есть в сохранённых
        if self.custom_color and self.custom_color.startswith("#"):
            c_upper = self.custom_color.upper()
            if c_upper not in self.saved_custom_colors:
                self.saved_custom_colors.append(c_upper)
                self.db.set_setting("custom_colors_list", json.dumps(self.saved_custom_colors))

        self.theme_swatches: Dict[str, ThemeSwatchButton] = {}
        self.custom_swatches: Dict[str, CustomThemeSwatchButton] = {}
        self.cards: List[QFrame] = []
        self.section_headers: List[Tuple[QLabel, str, QLabel]] = []
        self.desc_labels: List[QLabel] = []
        self.profile_labels: List[QLabel] = []

        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("background: transparent; border: none;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(14)

        # 1. Шапка страницы: кнопка Назад и заголовок
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 4, 0, 6)
        header_row.setSpacing(12)

        self.back_btn = QPushButton("Назад к работам")
        self.back_btn.setIcon(get_material_icon("arrow_back", color=self.theme["primary"], size=16))
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setFixedHeight(38)
        self.back_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                color: {self.theme.get('primary', '#8AB4F8')};
                font-size: 12px;
                font-weight: 600;
                border-radius: 19px;
                padding: 0 16px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {'rgba(255, 255, 255, 0.18)' if self.mode == 'dark' else 'rgba(0, 0, 0, 0.08)'};
            }}
            """
        )
        self.back_btn.clicked.connect(self.back_clicked.emit)
        header_row.addWidget(self.back_btn)

        self.page_title = QLabel("Настройки приложения")
        self.page_title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {self.theme['text_primary']}; letter-spacing: -0.5px; border: none; background: transparent;"
        )
        header_row.addWidget(self.page_title)
        header_row.addStretch()

        main_layout.addLayout(header_row)

        # 2. Скролл-область с карточками настроек
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            """
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.18);
                min-height: 24px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            """
        )

        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(16, 6, 16, 20)
        content_layout.setSpacing(16)

        # ----------------------------------------------------------------------
        # Карточка 1: Режим темы (Тёмная / Светлая)
        # ----------------------------------------------------------------------
        mode_card = self._create_card()
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setContentsMargins(22, 18, 22, 18)
        mode_layout.setSpacing(12)

        mode_header = self._create_section_header("palette", "РЕЖИМ ОФОРМЛЕНИЯ")
        mode_layout.addLayout(mode_header)

        mode_btn_row = QHBoxLayout()
        mode_btn_row.setSpacing(12)

        self.dark_btn = QPushButton("Тёмная тема")
        self.dark_btn.setCursor(Qt.PointingHandCursor)
        self.dark_btn.setFixedHeight(40)
        self.dark_btn.clicked.connect(lambda: self._set_mode("dark"))
        mode_btn_row.addWidget(self.dark_btn, 1)

        self.light_btn = QPushButton("Светлая тема")
        self.light_btn.setCursor(Qt.PointingHandCursor)
        self.light_btn.setFixedHeight(40)
        self.light_btn.clicked.connect(lambda: self._set_mode("light"))
        mode_btn_row.addWidget(self.light_btn, 1)

        mode_layout.addLayout(mode_btn_row)
        content_layout.addWidget(mode_card)

        # ----------------------------------------------------------------------
        # Карточка 2: Цветовая палитра Monet + Свой цвет с сохранением
        # ----------------------------------------------------------------------
        theme_card = self._create_card()
        theme_layout = QVBoxLayout(theme_card)
        theme_layout.setContentsMargins(22, 18, 22, 18)
        theme_layout.setSpacing(12)

        theme_header = self._create_section_header("color_lens", "ЦВЕТОВАЯ ПАЛИТРА (MONET ENGINE)")
        theme_layout.addLayout(theme_header)

        desc_lbl = QLabel("Выберите акцентный тон Google Pixel или задайте собственный цвет:")
        desc_lbl.setStyleSheet(f"font-size: 12px; color: {self.theme['text_secondary']}; background: transparent; border: none;")
        self.desc_labels.append(desc_lbl)
        theme_layout.addWidget(desc_lbl)

        self.swatches_row = QHBoxLayout()
        self.swatches_row.setSpacing(10)

        # Стандартные палитры Pixel
        for key, pdata in PIXEL_THEMES_DARK.items():
            palette = get_theme(key, mode=self.mode)
            is_active = (key == self.theme_key)
            swatch_btn = ThemeSwatchButton(
                theme_key=key,
                swatch_color=palette["swatch"],
                is_selected=is_active,
                theme_name=palette["name"],
                is_dark=(self.mode == "dark"),
                parent=self,
            )
            swatch_btn.clicked.connect(self._on_preset_swatch_clicked)
            self.theme_swatches[key] = swatch_btn
            self.swatches_row.addWidget(swatch_btn)

        # Ряд сохраненных кастомных цветов
        self.custom_swatches_layout = QHBoxLayout()
        self.custom_swatches_layout.setSpacing(10)
        self.swatches_row.addLayout(self.custom_swatches_layout)

        # Свой цвет (кнопка пикера)
        self.custom_color_btn = QPushButton("+ Свой цвет")
        self.custom_color_btn.setCursor(Qt.PointingHandCursor)
        self.custom_color_btn.setFixedHeight(38)
        self.custom_color_btn.clicked.connect(self._open_custom_color_dialog)
        self.swatches_row.addWidget(self.custom_color_btn)

        # Индикатор текущего кастомного цвета
        self.custom_preview = QLabel()
        self.custom_preview.setFixedSize(28, 28)
        self.custom_preview.setToolTip(f"Текущий кастомный цвет: {self.custom_color}")
        self.swatches_row.addWidget(self.custom_preview)

        self.swatches_row.addStretch()
        theme_layout.addLayout(self.swatches_row)
        content_layout.addWidget(theme_card)

        # Перестраиваем сохранённые кастомные свотчи
        self._rebuild_custom_swatches()

        # ----------------------------------------------------------------------
        # Карточка 3: Ползунок прозрачности (Frosted Glass Opacity)
        # ----------------------------------------------------------------------
        opacity_card = self._create_card()
        op_layout = QVBoxLayout(opacity_card)
        op_layout.setContentsMargins(22, 18, 22, 18)
        op_layout.setSpacing(12)

        op_header = self._create_section_header("opacity", "ПРОЗРАЧНОСТЬ ИНТЕРФЕЙСА (FROSTED GLASS)")
        op_layout.addLayout(op_header)

        op_desc = QLabel("Регулирует силу матового стекла и прозрачность подложек и боковых панелей:")
        op_desc.setStyleSheet(f"font-size: 12px; color: {self.theme['text_secondary']}; background: transparent; border: none;")
        self.desc_labels.append(op_desc)
        op_layout.addWidget(op_desc)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(12)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(35, 100)
        current_percent = int(self.opacity * 100)
        self.opacity_slider.setValue(current_percent)
        self.opacity_slider.setFixedHeight(24)
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        slider_row.addWidget(self.opacity_slider, 1)

        self.opacity_badge = QLabel(f"{current_percent}%")
        self.opacity_badge.setFixedWidth(52)
        self.opacity_badge.setAlignment(Qt.AlignCenter)
        self.opacity_badge.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                color: {self.theme.get('primary', '#8AB4F8')};
                border-radius: 10px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 700;
                border: none;
            }}
            """
        )
        slider_row.addWidget(self.opacity_badge)

        op_layout.addLayout(slider_row)
        content_layout.addWidget(opacity_card)

        # ----------------------------------------------------------------------
        # Карточка 4: Профиль студента (для титульных листов и отчетов)
        # ----------------------------------------------------------------------
        student_card = self._create_card()
        st_layout = QVBoxLayout(student_card)
        st_layout.setContentsMargins(22, 18, 22, 18)
        st_layout.setSpacing(12)

        st_header = self._create_section_header("person", "ПРОФИЛЬ СТУДЕНТА (ДЛЯ ОТЧЕТОВ)")
        st_layout.addLayout(st_header)

        st_form = QFormLayout()
        st_form.setSpacing(12)

        curr_name = self.db.get_setting("student_name", "")
        curr_grp = self.db.get_setting("student_group", "")
        curr_var = self.db.get_setting("student_variant", "")

        lbl_name = QLabel("ФИО студента:")
        lbl_name.setStyleSheet(f"color: {self.theme['text_primary']}; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        self.profile_labels.append(lbl_name)
        self.name_edit = QLineEdit(curr_name)
        self.name_edit.setFixedHeight(38)
        self.name_edit.setPlaceholderText("Иванов Иван Иванович")
        st_form.addRow(lbl_name, self.name_edit)

        lbl_grp = QLabel("Учебная группа:")
        lbl_grp.setStyleSheet(f"color: {self.theme['text_primary']}; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        self.profile_labels.append(lbl_grp)
        self.group_edit = QLineEdit(curr_grp)
        self.group_edit.setFixedHeight(38)
        self.group_edit.setPlaceholderText("ИВТ-21")
        st_form.addRow(lbl_grp, self.group_edit)

        lbl_var = QLabel("Вариант по списку:")
        lbl_var.setStyleSheet(f"color: {self.theme['text_primary']}; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        self.profile_labels.append(lbl_var)
        self.variant_edit = QLineEdit(curr_var)
        self.variant_edit.setFixedHeight(38)
        self.variant_edit.setPlaceholderText("Вариант 1")
        st_form.addRow(lbl_var, self.variant_edit)

        st_layout.addLayout(st_form)

        save_btn_row = QHBoxLayout()
        save_btn_row.addStretch()

        self.save_profile_btn = QPushButton("Сохранить профиль")
        self.save_profile_btn.setFixedHeight(38)
        self.save_profile_btn.setCursor(Qt.PointingHandCursor)
        self._style_save_profile_btn()
        self.save_profile_btn.clicked.connect(self._save_student_profile)
        save_btn_row.addWidget(self.save_profile_btn)
        st_layout.addLayout(save_btn_row)

        content_layout.addWidget(student_card)

        # ----------------------------------------------------------------------
        # Карточка 5: Рабочая область (Workspace)
        # ----------------------------------------------------------------------
        ws_card = self._create_card()
        ws_layout = QVBoxLayout(ws_card)
        ws_layout.setContentsMargins(22, 18, 22, 18)
        ws_layout.setSpacing(12)

        ws_header = self._create_section_header("folder", "РАБОЧАЯ ОБЛАСТЬ (WORKSPACE)")
        ws_layout.addLayout(ws_header)

        self.ws_path_lbl = QLabel(str(self.fs.root_path))
        self.ws_path_lbl.setWordWrap(True)
        self.ws_path_lbl.setStyleSheet(
            f"font-size: 12px; color: {self.theme['text_secondary']}; background: transparent; border: none;"
        )
        ws_layout.addWidget(self.ws_path_lbl)

        ws_btn_row = QHBoxLayout()
        ws_btn_row.setSpacing(10)

        self.open_folder_btn = QPushButton("Открыть в Проводнике")
        self.open_folder_btn.setIcon(get_material_icon("folder_open", color=self.theme["primary"], size=16))
        self.open_folder_btn.setFixedHeight(36)
        self.open_folder_btn.setCursor(Qt.PointingHandCursor)
        self.open_folder_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                color: {self.theme.get('primary', '#8AB4F8')};
                font-size: 11px;
                font-weight: 600;
                border-radius: 18px;
                padding: 0 14px;
                border: none;
            }}
            """
        )
        self.open_folder_btn.clicked.connect(lambda: self.fs.open_path_in_explorer(self.fs.root_path))
        ws_btn_row.addWidget(self.open_folder_btn)

        self.change_folder_btn = QPushButton("Сменить папку...")
        self.change_folder_btn.setIcon(get_material_icon("drive_file_move", color=self.theme["primary"], size=16))
        self.change_folder_btn.setFixedHeight(36)
        self.change_folder_btn.setCursor(Qt.PointingHandCursor)
        self.change_folder_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme.get('primary', '#8AB4F8')};
                font-size: 11px;
                font-weight: 600;
                border-radius: 18px;
                padding: 0 14px;
                border: 1px solid {self.theme.get('primary', '#8AB4F8')};
            }}
            """
        )
        self.change_folder_btn.clicked.connect(self._change_workspace_folder)
        ws_btn_row.addWidget(self.change_folder_btn)

        ws_btn_row.addStretch()
        ws_layout.addLayout(ws_btn_row)
        content_layout.addWidget(ws_card)

        # 6. Карточка: Уведомления и Системный трей (Шаг 5)
        notify_card = self._create_card()
        notify_layout = QVBoxLayout(notify_card)
        notify_layout.setContentsMargins(20, 18, 20, 18)
        notify_layout.setSpacing(14)

        notify_header = self._create_section_header("notifications_active", "УВЕДОМЛЕНИЯ И СИСТЕМНЫЙ ТРЕЙ")
        notify_layout.addLayout(notify_header)

        notify_desc = QLabel("Фоновый мониторинг дедлайнов и сворачивание в системную область Windows")
        notify_desc.setStyleSheet(f"color: {self.theme.get('text_secondary', '#C4C7D0')}; font-size: 12px; border: none; background: transparent;")
        self.desc_labels.append(notify_desc)
        notify_layout.addWidget(notify_desc)

        # Чекбокс сворачивания в трей
        self.tray_checkbox = QCheckBox("Сворачивать приложение в системный трей при закрытии окна")
        self.tray_checkbox.setChecked(self.db.get_setting("minimize_to_tray", "1") == "1")
        self.tray_checkbox.setCursor(Qt.PointingHandCursor)
        self.tray_checkbox.setStyleSheet(
            f"""
            QCheckBox {{
                color: {self.theme.get('text_primary', '#E2E2E9')};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {self.theme.get('outline_variant', 'rgba(255,255,255,0.2)')};
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.theme.get('primary', '#8AB4F8')};
                border-color: {self.theme.get('primary', '#8AB4F8')};
            }}
            """
        )
        self.tray_checkbox.stateChanged.connect(self._on_tray_checkbox_changed)
        notify_layout.addWidget(self.tray_checkbox)

        # Чекбокс системных уведомлений
        self.notify_checkbox = QCheckBox("Отправлять системные уведомления Windows о горящих дедлайнах")
        self.notify_checkbox.setChecked(self.db.get_setting("notifications_enabled", "1") == "1")
        self.notify_checkbox.setCursor(Qt.PointingHandCursor)
        self.notify_checkbox.setStyleSheet(
            f"""
            QCheckBox {{
                color: {self.theme.get('text_primary', '#E2E2E9')};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {self.theme.get('outline_variant', 'rgba(255,255,255,0.2)')};
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.theme.get('primary', '#8AB4F8')};
                border-color: {self.theme.get('primary', '#8AB4F8')};
            }}
            """
        )
        self.notify_checkbox.stateChanged.connect(self._on_notify_checkbox_changed)
        notify_layout.addWidget(self.notify_checkbox)

        # Кнопка ручной проверки дедлайнов
        notify_btn_row = QHBoxLayout()
        self.check_deadlines_btn = QPushButton("Проверить дедлайны сейчас")
        self.check_deadlines_btn.setIcon(get_material_icon("notifications", color=self.theme["primary"], size=16))
        self.check_deadlines_btn.setFixedHeight(36)
        self.check_deadlines_btn.setCursor(Qt.PointingHandCursor)
        self.check_deadlines_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                color: {self.theme.get('primary', '#8AB4F8')};
                font-size: 11px;
                font-weight: 600;
                border-radius: 18px;
                padding: 0 14px;
                border: none;
                min-height: 36px;
                max-height: 36px;
            }}
            """
        )
        self.check_deadlines_btn.clicked.connect(self._on_check_deadlines_clicked)
        notify_btn_row.addWidget(self.check_deadlines_btn)
        notify_btn_row.addStretch()
        notify_layout.addLayout(notify_btn_row)

        content_layout.addWidget(notify_card)

        content_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

        self._update_mode_buttons_style()
        self._update_custom_button_style()
        self._update_custom_preview()
        self._update_line_edits_style()

    def _create_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.theme.get('card_bg', 'rgba(255, 255, 255, 0.06)')};
                border-radius: 20px;
                border: none;
            }}
            """
        )
        self.cards.append(card)
        return card

    def _create_section_header(self, icon_name: str, title: str) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(8)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_material_pixmap(icon_name, color=self.theme["primary"], size=18))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.theme['text_secondary']}; letter-spacing: 0.8px; border: none; background: transparent;"
        )
        layout.addWidget(title_lbl)
        layout.addStretch()

        self.section_headers.append((icon_lbl, icon_name, title_lbl))
        return layout

    def _style_save_profile_btn(self) -> None:
        primary = self.theme.get("primary", "#8AB4F8")
        on_primary = self.theme.get("on_primary", "#000000")
        self.save_profile_btn.setIcon(get_material_icon("check", color=on_primary, size=16))
        self.save_profile_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {primary};
                color: {on_primary};
                font-size: 12px;
                font-weight: 700;
                border-radius: 19px;
                padding: 0 18px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get('primary_hover', primary)};
            }}
            """
        )

    def _update_line_edits_style(self) -> None:
        is_dark = (self.mode == "dark")
        edit_bg = "rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.04)"
        edit_border = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
        focus_border = self.theme.get("primary", "#8AB4F8")
        text_col = self.theme.get("text_primary", "#FFFFFF")
        placeholder_col = self.theme.get("text_secondary", "#C4C7D0")
        on_primary = self.theme.get("on_primary", "#000000")

        qss = f"""
        QLineEdit {{
            background-color: {edit_bg};
            color: {text_col};
            placeholder-text-color: {placeholder_col};
            selection-background-color: {focus_border};
            selection-color: {on_primary};
            border: 1px solid {edit_border};
            border-radius: 14px;
            padding: 0 14px;
            font-size: 13px;
        }}
        QLineEdit:focus {{
            border: 1.5px solid {focus_border};
        }}
        """
        if hasattr(self, "name_edit"):
            self.name_edit.setStyleSheet(qss)
        if hasattr(self, "group_edit"):
            self.group_edit.setStyleSheet(qss)
        if hasattr(self, "variant_edit"):
            self.variant_edit.setStyleSheet(qss)

    def _rebuild_custom_swatches(self) -> None:
        """Перестраивает кнопки сохранённых кастомных цветов."""
        # Очищаем старые
        while self.custom_swatches_layout.count() > 0:
            child = self.custom_swatches_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.custom_swatches.clear()

        # Добавляем каждый сохраненный цвет
        for hex_c in self.saved_custom_colors:
            key = f"custom:{hex_c.upper()}"
            is_active = (self.theme_key == key or self.theme_key == "custom") and (self.custom_color.upper() == hex_c.upper())
            swatch = CustomThemeSwatchButton(
                hex_color=hex_c.upper(),
                is_selected=is_active,
                is_dark=(self.mode == "dark"),
                parent=self,
            )
            swatch.clicked.connect(self._on_custom_swatch_clicked)
            swatch.delete_requested.connect(self._on_custom_swatch_deleted)
            self.custom_swatches[hex_c.upper()] = swatch
            self.custom_swatches_layout.addWidget(swatch)

    def _on_custom_swatch_clicked(self, theme_key: str) -> None:
        hex_c = theme_key.split(":", 1)[1] if ":" in theme_key else self.custom_color
        self.set_custom_color(hex_c)

    def _on_custom_swatch_deleted(self, hex_color: str) -> None:
        """Удаляет кастомный цвет из сохранённых."""
        hex_upper = hex_color.upper()
        if hex_upper in self.saved_custom_colors:
            self.saved_custom_colors.remove(hex_upper)
            self.db.set_setting("custom_colors_list", json.dumps(self.saved_custom_colors))

        # Если удаленный цвет был активным — переключаем на тему по умолчанию
        if self.custom_color.upper() == hex_upper:
            self.theme_key = DEFAULT_THEME
            for key, btn in self.theme_swatches.items():
                btn.set_selected(key == DEFAULT_THEME)
            self.theme_updated.emit(self.theme_key, self.mode, self.custom_color, self.opacity)

        self._rebuild_custom_swatches()

    def _update_mode_buttons_style(self) -> None:
        primary = self.theme.get("primary", "#8AB4F8")
        on_primary = self.theme.get("on_primary", "#000000")
        sec_bg = self.theme.get("secondary_container", "rgba(255, 255, 255, 0.08)")

        if self.mode == "dark":
            self.dark_btn.setStyleSheet(
                f"background-color: {primary}; color: {on_primary}; font-weight: 700; border-radius: 20px; border: none; font-size: 12px;"
            )
            self.light_btn.setStyleSheet(
                f"background-color: {sec_bg}; color: {self.theme['text_secondary']}; font-weight: 500; border-radius: 20px; border: none; font-size: 12px;"
            )
        else:
            self.dark_btn.setStyleSheet(
                f"background-color: {sec_bg}; color: {self.theme['text_secondary']}; font-weight: 500; border-radius: 20px; border: none; font-size: 12px;"
            )
            self.light_btn.setStyleSheet(
                f"background-color: {primary}; color: {on_primary}; font-weight: 700; border-radius: 20px; border: none; font-size: 12px;"
            )

    def _update_custom_button_style(self) -> None:
        is_custom = self.theme_key.startswith("custom")
        primary = self.theme.get("primary", "#8AB4F8")
        sec_bg = self.theme.get("secondary_container", "rgba(255, 255, 255, 0.08)")

        if is_custom:
            self.custom_color_btn.setStyleSheet(
                f"background-color: {primary}; color: {self.theme['on_primary']}; font-weight: 700; border-radius: 19px; padding: 0 14px; border: none; font-size: 12px;"
            )
        else:
            self.custom_color_btn.setStyleSheet(
                f"background-color: {sec_bg}; color: {self.theme['text_primary']}; font-weight: 500; border-radius: 19px; padding: 0 14px; border: none; font-size: 12px;"
            )

    def _update_custom_preview(self) -> None:
        c = self.custom_color or "#8AB4F8"
        is_custom = self.theme_key.startswith("custom")
        border = "2px solid #FFFFFF" if is_custom else "1px solid rgba(255, 255, 255, 0.3)"
        self.custom_preview.setStyleSheet(
            f"background-color: {c}; border-radius: 14px; border: {border};"
        )

    def _set_mode(self, new_mode: str) -> None:
        if new_mode == self.mode:
            return
        self.mode = new_mode
        self._update_mode_buttons_style()
        self.theme_updated.emit(self.theme_key, self.mode, self.custom_color, self.opacity)

    def _on_preset_swatch_clicked(self, key: str) -> None:
        self.theme_key = key
        for k, btn in self.theme_swatches.items():
            btn.set_selected(k == key)
        for btn in self.custom_swatches.values():
            btn.set_selected(False)
        self._update_custom_button_style()
        self._update_custom_preview()
        self.theme_updated.emit(self.theme_key, self.mode, self.custom_color, self.opacity)

    def set_custom_color(self, hex_color: str) -> None:
        """Применяет кастомный HEX цвет темы и добавляет в сохраненные."""
        self.custom_color = hex_color.upper()
        self.theme_key = f"custom:{self.custom_color}"
        self.db.set_setting("custom_theme_color", self.custom_color)

        if self.custom_color not in self.saved_custom_colors:
            self.saved_custom_colors.insert(0, self.custom_color)
            if len(self.saved_custom_colors) > 6:
                self.saved_custom_colors = self.saved_custom_colors[:6]
            self.db.set_setting("custom_colors_list", json.dumps(self.saved_custom_colors))

        for btn in self.theme_swatches.values():
            btn.set_selected(False)

        self._rebuild_custom_swatches()
        self._update_custom_button_style()
        self._update_custom_preview()
        self.theme_updated.emit(self.theme_key, self.mode, self.custom_color, self.opacity)

    def _open_custom_color_dialog(self) -> None:
        """Открывает диалог палитры для выбора любого цвета."""
        initial = QColor(self.custom_color or "#8AB4F8")
        color = QColorDialog.getColor(initial, self, "Выберите кастомный цвет темы")
        if color.isValid():
            self.set_custom_color(color.name())

    def _on_opacity_slider_changed(self, value: int) -> None:
        """Реактивно меняет прозрачность интерфейса при движении ползунка."""
        self.opacity = value / 100.0
        self.opacity_badge.setText(f"{value}%")
        self.db.set_setting("panel_opacity", str(self.opacity))
        self.theme_updated.emit(self.theme_key, self.mode, self.custom_color, self.opacity)

    def _save_student_profile(self) -> None:
        """Сохраняет профиль студента в SQLite."""
        self.db.set_setting("student_name", self.name_edit.text().strip())
        self.db.set_setting("student_group", self.group_edit.text().strip())
        self.db.set_setting("student_variant", self.variant_edit.text().strip())
        self.save_profile_btn.setText("Сохранено ✓")
        self.settings_saved.emit()

    def _change_workspace_folder(self) -> None:
        """Диалог смены директории Workspace."""
        new_dir = QFileDialog.getExistingDirectory(
            self,
            "Выберите новую корневую директорию для работ",
            str(self.fs.root_path),
        )
        if new_dir:
            self.fs.root_path = Path(new_dir)
            self.db.set_setting("workspace_path", str(self.fs.root_path))
            self.ws_path_lbl.setText(str(self.fs.root_path))

    def _on_tray_checkbox_changed(self, state: int) -> None:
        val = "1" if (state == Qt.CheckState.Checked.value or state == 2) else "0"
        self.db.set_setting("minimize_to_tray", val)

    def _on_notify_checkbox_changed(self, state: int) -> None:
        val = "1" if (state == Qt.CheckState.Checked.value or state == 2) else "0"
        self.db.set_setting("notifications_enabled", val)

    def _on_check_deadlines_clicked(self) -> None:
        parent_window = self.window()
        if hasattr(parent_window, "check_deadlines_and_notify"):
            parent_window.check_deadlines_and_notify(force=True)

    def apply_theme(self, theme: Dict[str, Any], mode: str, custom_color: Optional[str] = None, opacity: float = 1.0) -> None:
        """Обновляет оформление всех элементов страницы настроек при смене темы."""
        self.theme = theme
        self.mode = mode
        if custom_color:
            self.custom_color = custom_color
        self.opacity = opacity

        self.page_title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {self.theme['text_primary']}; letter-spacing: -0.5px; border: none; background: transparent;"
        )
        self.back_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                color: {self.theme.get('primary', '#8AB4F8')};
                font-size: 12px;
                font-weight: 600;
                border-radius: 19px;
                padding: 0 16px;
                border: none;
            }}
            """
        )
        self.back_btn.setIcon(get_material_icon("arrow_back", color=self.theme["primary"], size=16))

        # Обновляем все карточки настроек
        card_bg = self.theme.get('card_bg', 'rgba(255, 255, 255, 0.06)')
        for card in self.cards:
            card.setStyleSheet(
                f"QFrame {{ background-color: {card_bg}; border-radius: 20px; border: none; }}"
            )

        # Обновляем все заголовки секций и их иконки
        for icon_lbl, icon_name, title_lbl in self.section_headers:
            icon_lbl.setPixmap(get_material_pixmap(icon_name, color=self.theme["primary"], size=18))
            title_lbl.setStyleSheet(
                f"font-size: 11px; font-weight: 700; color: {self.theme['text_secondary']}; letter-spacing: 0.8px; border: none; background: transparent;"
            )

        # Обновляем все поясняющие подписи и метки формы профиля
        for lbl in getattr(self, "desc_labels", []):
            lbl.setStyleSheet(f"font-size: 12px; color: {self.theme['text_secondary']}; background: transparent; border: none;")
        for lbl in getattr(self, "profile_labels", []):
            lbl.setStyleSheet(f"color: {self.theme['text_primary']}; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        if hasattr(self, "ws_path_lbl"):
            self.ws_path_lbl.setStyleSheet(f"font-size: 12px; color: {self.theme['text_secondary']}; background: transparent; border: none;")

        # Обновляем кнопку Сохранить профиль
        self._style_save_profile_btn()

        # Обновляем поля ввода
        self._update_line_edits_style()

        # Обновляем кнопки режимов и свой цвет
        self._update_mode_buttons_style()
        self._update_custom_button_style()
        self._update_custom_preview()

        # Обновляем бейдж прозрачности
        self.opacity_badge.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                color: {self.theme.get('primary', '#8AB4F8')};
                border-radius: 10px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 700;
                border: none;
            }}
            """
        )

        # Обновляем кнопки директории
        if hasattr(self, "open_folder_btn"):
            self.open_folder_btn.setIcon(get_material_icon("folder_open", color=self.theme["primary"], size=16))
            self.open_folder_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                    color: {self.theme.get('primary', '#8AB4F8')};
                    font-size: 11px;
                    font-weight: 600;
                    border-radius: 18px;
                    padding: 0 14px;
                    border: none;
                }}
                """
            )
        if hasattr(self, "change_folder_btn"):
            self.change_folder_btn.setIcon(get_material_icon("drive_file_move", color=self.theme["primary"], size=16))
            self.change_folder_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.theme.get('primary', '#8AB4F8')};
                    font-size: 11px;
                    font-weight: 600;
                    border-radius: 18px;
                    padding: 0 14px;
                    border: 1px solid {self.theme.get('primary', '#8AB4F8')};
                }}
                """
            )

        # Обновляем элементы трея и уведомлений
        if hasattr(self, "tray_checkbox"):
            self.tray_checkbox.setStyleSheet(
                f"""
                QCheckBox {{
                    color: {self.theme.get('text_primary', '#E2E2E9')};
                    font-size: 13px;
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border-radius: 4px;
                    border: 1px solid {self.theme.get('outline_variant', 'rgba(255,255,255,0.2)')};
                    background: transparent;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {self.theme.get('primary', '#8AB4F8')};
                    border-color: {self.theme.get('primary', '#8AB4F8')};
                }}
                """
            )
        if hasattr(self, "notify_checkbox"):
            self.notify_checkbox.setStyleSheet(
                f"""
                QCheckBox {{
                    color: {self.theme.get('text_primary', '#E2E2E9')};
                    font-size: 13px;
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border-radius: 4px;
                    border: 1px solid {self.theme.get('outline_variant', 'rgba(255,255,255,0.2)')};
                    background: transparent;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {self.theme.get('primary', '#8AB4F8')};
                    border-color: {self.theme.get('primary', '#8AB4F8')};
                }}
                """
            )
        if hasattr(self, "check_deadlines_btn"):
            self.check_deadlines_btn.setIcon(get_material_icon("notifications", color=self.theme["primary"], size=16))
            self.check_deadlines_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {self.theme.get('secondary_container', 'rgba(255, 255, 255, 0.08)')};
                    color: {self.theme.get('primary', '#8AB4F8')};
                    font-size: 11px;
                    font-weight: 600;
                    border-radius: 18px;
                    padding: 0 14px;
                    border: none;
                    min-height: 36px;
                    max-height: 36px;
                }}
                """
            )

        # Обновляем стандартные свотчи
        for key, swatch in self.theme_swatches.items():
            pal = get_theme(key, mode=self.mode)
            swatch.set_swatch_color(pal["swatch"])
            swatch.set_is_dark(self.mode == "dark")
            swatch.set_selected(key == self.theme_key)

        # Обновляем кастомные свотчи
        for hex_c, swatch in self.custom_swatches.items():
            swatch.set_is_dark(self.mode == "dark")
            is_active = (self.theme_key.startswith("custom") and self.custom_color.upper() == hex_c.upper())
            swatch.set_selected(is_active)

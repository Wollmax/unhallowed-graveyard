"""Google Material Design 3 Expressive (Monet Engine) + Windows 11 Acrylic Blur.
Единый источник палитр Pixel Monet, управления темами, шрифтов Roboto и Zero-Border стилей.
"""

from __future__ import annotations

import ctypes
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Tuple

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QWidget


# ==============================================================================
# 1. 5 фирменных динамических палитр Google Pixel (Monet Engine) Dark & Light
# ==============================================================================

PIXEL_THEMES_DARK: Dict[str, Dict[str, Any]] = {
    "pixel_blue": {
        "name": "Pixel Sapphire",
        "swatch": "#A8C7FA",
        "panel_bg": "rgba(24, 28, 42, 140)",
        "center_bg": "rgba(16, 20, 32, 115)",
        "card_bg": "rgba(34, 40, 60, 145)",
        "card_hover": "rgba(44, 52, 78, 185)",
        "card_selected": "rgba(54, 66, 96, 200)",
        "card_border": "transparent",
        "card_border_hover": "transparent",
        "panel_border": "transparent",
        "center_border": "transparent",
        "ambient_top": "#1B2234",
        "ambient_bottom": "#101420",
        "primary": "#A8C7FA",
        "primary_hover": "#BED7FE",
        "on_primary": "#062E6F",
        "secondary_container": "rgba(168, 199, 250, 35)",
        "on_secondary_container": "#D3E4FF",
        "on_secondary": "#D3E4FF",
        "text_primary": "#E2E2E9",
        "text_secondary": "#C4C7D0",
        "text_muted": "#9DA1AA",
        "dialog_bg": "rgba(26, 30, 44, 220)",
        "dialog_card": "rgba(255, 255, 255, 0.06)",
        "scrollbar_handle": "rgba(255, 255, 255, 0.18)",
        "scrollbar_hover": "rgba(255, 255, 255, 0.35)",
        "is_dark": True,
    },
    "emerald": {
        "name": "Pixel Emerald",
        "swatch": "#80D999",
        "panel_bg": "rgba(20, 32, 26, 140)",
        "center_bg": "rgba(14, 24, 19, 115)",
        "card_bg": "rgba(28, 48, 38, 145)",
        "card_hover": "rgba(38, 62, 50, 185)",
        "card_selected": "rgba(48, 76, 62, 200)",
        "card_border": "transparent",
        "card_border_hover": "transparent",
        "panel_border": "transparent",
        "center_border": "transparent",
        "ambient_top": "#182820",
        "ambient_bottom": "#0E1A14",
        "primary": "#80D999",
        "primary_hover": "#98E4AD",
        "on_primary": "#003919",
        "secondary_container": "rgba(128, 217, 153, 35)",
        "on_secondary_container": "#9DF6B3",
        "on_secondary": "#9DF6B3",
        "text_primary": "#E1E3DF",
        "text_secondary": "#C1C8C2",
        "text_muted": "#99A19A",
        "dialog_bg": "rgba(22, 33, 27, 220)",
        "dialog_card": "rgba(255, 255, 255, 0.06)",
        "scrollbar_handle": "rgba(255, 255, 255, 0.18)",
        "scrollbar_hover": "rgba(255, 255, 255, 0.35)",
        "is_dark": True,
    },
    "lavender": {
        "name": "Pixel Lavender",
        "swatch": "#D0BCFF",
        "panel_bg": "rgba(30, 24, 42, 140)",
        "center_bg": "rgba(22, 18, 32, 115)",
        "card_bg": "rgba(42, 35, 58, 145)",
        "card_hover": "rgba(56, 46, 76, 185)",
        "card_selected": "rgba(68, 56, 92, 200)",
        "card_border": "transparent",
        "card_border_hover": "transparent",
        "panel_border": "transparent",
        "center_border": "transparent",
        "ambient_top": "#251E34",
        "ambient_bottom": "#14101E",
        "primary": "#D0BCFF",
        "primary_hover": "#DFCFFF",
        "on_primary": "#381E72",
        "secondary_container": "rgba(208, 188, 255, 35)",
        "on_secondary_container": "#EADDFF",
        "on_secondary": "#EADDFF",
        "text_primary": "#E6E1E5",
        "text_secondary": "#CAC4D0",
        "text_muted": "#A29CA9",
        "dialog_bg": "rgba(32, 26, 44, 220)",
        "dialog_card": "rgba(255, 255, 255, 0.06)",
        "scrollbar_handle": "rgba(255, 255, 255, 0.18)",
        "scrollbar_hover": "rgba(255, 255, 255, 0.35)",
        "is_dark": True,
    },
    "rose": {
        "name": "Pixel Rose",
        "swatch": "#FFB2BE",
        "panel_bg": "rgba(36, 24, 28, 140)",
        "center_bg": "rgba(26, 17, 20, 115)",
        "card_bg": "rgba(52, 34, 40, 145)",
        "card_hover": "rgba(66, 44, 52, 185)",
        "card_selected": "rgba(80, 54, 64, 200)",
        "card_border": "transparent",
        "card_border_hover": "transparent",
        "panel_border": "transparent",
        "center_border": "transparent",
        "ambient_top": "#2B1C22",
        "ambient_bottom": "#180F13",
        "primary": "#FFB2BE",
        "primary_hover": "#FFC4CD",
        "on_primary": "#5F1124",
        "secondary_container": "rgba(255, 178, 190, 35)",
        "on_secondary_container": "#FFD9DE",
        "on_secondary": "#FFD9DE",
        "text_primary": "#ECE0E1",
        "text_secondary": "#D2C2C4",
        "text_muted": "#A8989A",
        "dialog_bg": "rgba(38, 26, 30, 220)",
        "dialog_card": "rgba(255, 255, 255, 0.06)",
        "scrollbar_handle": "rgba(255, 255, 255, 0.18)",
        "scrollbar_hover": "rgba(255, 255, 255, 0.35)",
        "is_dark": True,
    },
    "amber": {
        "name": "Pixel Gold",
        "swatch": "#F5BF42",
        "panel_bg": "rgba(34, 28, 20, 140)",
        "center_bg": "rgba(24, 20, 14, 115)",
        "card_bg": "rgba(48, 40, 30, 145)",
        "card_hover": "rgba(62, 52, 38, 185)",
        "card_selected": "rgba(76, 64, 48, 200)",
        "card_border": "transparent",
        "card_border_hover": "transparent",
        "panel_border": "transparent",
        "center_border": "transparent",
        "ambient_top": "#2B2216",
        "ambient_bottom": "#17130C",
        "primary": "#F5BF42",
        "primary_hover": "#FFCC5C",
        "on_primary": "#402D00",
        "secondary_container": "rgba(245, 191, 66, 35)",
        "on_secondary_container": "#FFDF9E",
        "on_secondary": "#FFDF9E",
        "text_primary": "#EAE1D9",
        "text_secondary": "#CEC5B8",
        "text_muted": "#A49C90",
        "dialog_bg": "rgba(38, 32, 22, 220)",
        "dialog_card": "rgba(255, 255, 255, 0.06)",
        "scrollbar_handle": "rgba(255, 255, 255, 0.18)",
        "scrollbar_hover": "rgba(255, 255, 255, 0.35)",
        "is_dark": True,
    },
}

PIXEL_THEMES_LIGHT: Dict[str, Dict[str, Any]] = {
    "pixel_blue": {
        "name": "Pixel Sapphire (Светлая)",
        "swatch": "#0B57D0",
        "panel_bg": "rgba(240, 245, 255, 145)",
        "center_bg": "rgba(248, 251, 255, 115)",
        "card_bg": "rgba(255, 255, 255, 175)",
        "card_hover": "rgba(255, 255, 255, 225)",
        "card_selected": "rgba(225, 236, 255, 205)",
        "card_border": "transparent",
        "card_border_hover": "transparent",
        "panel_border": "transparent",
        "center_border": "transparent",
        "ambient_top": "#EBF2FF",
        "ambient_bottom": "#DFECFE",
        "primary": "#0B57D0",
        "primary_hover": "#1264E8",
        "on_primary": "#FFFFFF",
        "secondary_container": "rgba(11, 87, 208, 24)",
        "on_secondary_container": "#041E49",
        "on_secondary": "#041E49",
        "text_primary": "#1A1C1E",
        "text_secondary": "#44474E",
        "text_muted": "#74777F",
        "dialog_bg": "rgba(245, 248, 255, 225)",
        "dialog_card": "rgba(255, 255, 255, 0.70)",
        "scrollbar_handle": "rgba(0, 0, 0, 0.16)",
        "scrollbar_hover": "rgba(0, 0, 0, 0.32)",
        "is_dark": False,
    },
    "emerald": {
        "name": "Pixel Emerald (Светлая)",
        "swatch": "#0F6D38",
        "panel_bg": "rgba(238, 248, 242, 145)",
        "center_bg": "rgba(246, 253, 248, 115)",
        "card_bg": "rgba(255, 255, 255, 175)",
        "card_hover": "rgba(255, 255, 255, 225)",
        "card_selected": "rgba(215, 244, 224, 205)",
        "card_border": "transparent",
        "card_border_hover": "transparent",
        "panel_border": "transparent",
        "center_border": "transparent",
        "ambient_top": "#E8F6ED",
        "ambient_bottom": "#DCF2E4",
        "primary": "#0F6D38",
        "primary_hover": "#158746",
        "on_primary": "#FFFFFF",
        "secondary_container": "rgba(15, 109, 56, 24)",
        "on_secondary_container": "#00210B",
        "on_secondary": "#00210B",
        "text_primary": "#191C19",
        "text_secondary": "#404943",
        "text_muted": "#707973",
        "dialog_bg": "rgba(242, 250, 245, 225)",
        "dialog_card": "rgba(255, 255, 255, 0.70)",
        "scrollbar_handle": "rgba(0, 0, 0, 0.16)",
        "scrollbar_hover": "rgba(0, 0, 0, 0.32)",
        "is_dark": False,
    },
    "lavender": {
        "name": "Pixel Lavender (Светлая)",
        "swatch": "#6750A4",
        "panel_bg": "rgba(246, 240, 254, 145)",
        "center_bg": "rgba(252, 248, 255, 115)",
        "card_bg": "rgba(255, 255, 255, 175)",
        "card_hover": "rgba(255, 255, 255, 225)",
        "card_selected": "rgba(238, 226, 255, 205)",
        "card_border": "transparent",
        "card_border_hover": "transparent",
        "panel_border": "transparent",
        "center_border": "transparent",
        "ambient_top": "#F4EBFC",
        "ambient_bottom": "#ECE0F8",
        "primary": "#6750A4",
        "primary_hover": "#7B62BC",
        "on_primary": "#FFFFFF",
        "secondary_container": "rgba(103, 80, 164, 24)",
        "on_secondary_container": "#21005D",
        "on_secondary": "#21005D",
        "text_primary": "#1D1B20",
        "text_secondary": "#49454E",
        "text_muted": "#7A757F",
        "dialog_bg": "rgba(248, 243, 254, 225)",
        "dialog_card": "rgba(255, 255, 255, 0.70)",
        "scrollbar_handle": "rgba(0, 0, 0, 0.16)",
        "scrollbar_hover": "rgba(0, 0, 0, 0.32)",
        "is_dark": False,
    },
    "rose": {
        "name": "Pixel Rose (Светлая)",
        "swatch": "#9C3A4D",
        "panel_bg": "rgba(254, 242, 244, 145)",
        "center_bg": "rgba(255, 249, 250, 115)",
        "card_bg": "rgba(255, 255, 255, 175)",
        "card_hover": "rgba(255, 255, 255, 225)",
        "card_selected": "rgba(255, 225, 230, 205)",
        "card_border": "transparent",
        "card_border_hover": "transparent",
        "panel_border": "transparent",
        "center_border": "transparent",
        "ambient_top": "#FCE8EC",
        "ambient_bottom": "#F8DCE2",
        "primary": "#9C3A4D",
        "primary_hover": "#B4465B",
        "on_primary": "#FFFFFF",
        "secondary_container": "rgba(156, 58, 77, 24)",
        "on_secondary_container": "#3B0714",
        "on_secondary": "#3B0714",
        "text_primary": "#201A1B",
        "text_secondary": "#524345",
        "text_muted": "#847375",
        "dialog_bg": "rgba(252, 244, 246, 225)",
        "dialog_card": "rgba(255, 255, 255, 0.70)",
        "scrollbar_handle": "rgba(0, 0, 0, 0.16)",
        "scrollbar_hover": "rgba(0, 0, 0, 0.32)",
        "is_dark": False,
    },
    "amber": {
        "name": "Pixel Gold (Светлая)",
        "swatch": "#7D5700",
        "panel_bg": "rgba(254, 245, 232, 145)",
        "center_bg": "rgba(255, 251, 245, 115)",
        "card_bg": "rgba(255, 255, 255, 175)",
        "card_hover": "rgba(255, 255, 255, 225)",
        "card_selected": "rgba(255, 230, 185, 205)",
        "card_border": "transparent",
        "card_border_hover": "transparent",
        "panel_border": "transparent",
        "center_border": "transparent",
        "ambient_top": "#FAECD6",
        "ambient_bottom": "#F5E0C2",
        "primary": "#7D5700",
        "primary_hover": "#946700",
        "on_primary": "#FFFFFF",
        "secondary_container": "rgba(125, 87, 0, 24)",
        "on_secondary_container": "#281800",
        "on_secondary": "#281800",
        "text_primary": "#1F1B16",
        "text_secondary": "#4F4539",
        "text_muted": "#817567",
        "dialog_bg": "rgba(252, 246, 236, 225)",
        "dialog_card": "rgba(255, 255, 255, 0.70)",
        "scrollbar_handle": "rgba(0, 0, 0, 0.16)",
        "scrollbar_hover": "rgba(0, 0, 0, 0.32)",
        "is_dark": False,
    },
}

# Для обратной совместимости
PIXEL_THEMES: Dict[str, Dict[str, Any]] = PIXEL_THEMES_DARK
PIXEL_THEMES_BY_MODE: Dict[str, Dict[str, Dict[str, Any]]] = {
    "dark": PIXEL_THEMES_DARK,
    "light": PIXEL_THEMES_LIGHT,
}

DEFAULT_THEME = "pixel_blue"
DEFAULT_MODE = "dark"


def get_theme(theme_key: str = DEFAULT_THEME, mode: str = "dark") -> Dict[str, Any]:
    """Возвращает палитру тонов для заданной темы Monet и режима (dark/light)."""
    table = PIXEL_THEMES_LIGHT if mode == "light" else PIXEL_THEMES_DARK
    return table.get(theme_key, table.get(DEFAULT_THEME, PIXEL_THEMES_DARK[DEFAULT_THEME]))


# ==============================================================================
# 2. Семантические цвета статусов и срочности дедлайнов (Zero Borders)
# ==============================================================================

STATUS_COLORS_MD3: Dict[str, Dict[str, str]] = {
    "NOT_STARTED":  {"bg": "rgba(142, 144, 153, 30)", "fg": "#C6C6CD"},
    "IN_PROGRESS":  {"bg": "rgba(168, 199, 250, 35)", "fg": "#A8C7FA"},
    "REPORTING":    {"bg": "rgba(208, 188, 255, 35)", "fg": "#D0BCFF"},
    "WAIT_DEFENSE": {"bg": "rgba(245, 191, 66, 35)",  "fg": "#F5BF42"},
    "REWORK":       {"bg": "rgba(255, 180, 160, 35)", "fg": "#FFB4A0"},
    "COMPLETED":    {"bg": "rgba(128, 217, 153, 35)", "fg": "#80D999"},
}

SUBJECT_PRESET_COLORS_MD3 = [
    "#A8C7FA",  # Sapphire
    "#80D999",  # Emerald
    "#D0BCFF",  # Amethyst
    "#FFB2BE",  # Rose
    "#F5BF42",  # Amber
    "#7DDCF9",  # Cyan
    "#FFB4A0",  # Coral
    "#B1C5FF",  # Periwinkle
]


def get_md3_urgency(deadline_str: Optional[str], is_completed: bool = False, is_dark: bool = True) -> Tuple[str, str, str]:
    """
    Возвращает (код_срочности, цвет_текста, полупрозрачный_фон_бейджа).
    Zero Borders: используется контраст тона без линий обводок.
    """
    if is_completed:
        fg = "#80D999" if is_dark else "#0F6D38"
        bg = "rgba(128, 217, 153, 35)" if is_dark else "rgba(15, 109, 56, 26)"
        return "COMPLETED", fg, bg

    neutral_fg = "#C4C7D0" if is_dark else "#44474E"
    neutral_bg = "rgba(142, 144, 153, 24)" if is_dark else "rgba(90, 94, 105, 20)"

    if not deadline_str:
        return "NO_DEADLINE", neutral_fg, neutral_bg

    try:
        if len(deadline_str) == 10:
            dl = datetime.strptime(deadline_str, "%Y-%m-%d")
        else:
            dl = datetime.strptime(deadline_str[:16], "%Y-%m-%d %H:%M")

        now = datetime.now()
        delta = dl - now
        seconds = delta.total_seconds()

        if seconds < 0 or seconds <= 24 * 3600:
            crit_fg = "#FFB4AB" if is_dark else "#BA1A1A"
            crit_bg = "rgba(255, 180, 171, 35)" if is_dark else "rgba(186, 26, 26, 26)"
            return ("OVERDUE" if seconds < 0 else "CRITICAL"), crit_fg, crit_bg
        elif seconds <= 3 * 24 * 3600:
            warn_fg = "#FFDF99" if is_dark else "#8C5800"
            warn_bg = "rgba(255, 223, 153, 35)" if is_dark else "rgba(178, 108, 0, 26)"
            return "WARNING", warn_fg, warn_bg
        else:
            return "NORMAL", neutral_fg, neutral_bg
    except Exception:
        return "NORMAL", neutral_fg, neutral_bg


# ==============================================================================
# 3. Подгрузка шрифтов Roboto
# ==============================================================================

def load_custom_fonts() -> int:
    """Загружает все шрифты .ttf из src/resources/fonts/ в QFontDatabase."""
    fonts_dir = Path(__file__).resolve().parent.parent / "resources" / "fonts"
    if not fonts_dir.exists():
        return 0

    count = 0
    for font_file in fonts_dir.rglob("*.ttf"):
        try:
            font_id = QFontDatabase.addApplicationFont(str(font_file))
            if font_id != -1:
                count += 1
        except Exception:
            pass
    return count


load_application_fonts = load_custom_fonts


# ==============================================================================
# 4. Нативное матовое стекло (Windows 11 DWM Acrylic Blur)
# ==============================================================================

class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


def apply_windows_acrylic(window: QWidget, is_dark: bool = True) -> bool:
    """
    Включает аппаратный Windows 11 Acrylic blur через dwmapi.
    Применяет темный или светлый заголовок окна и расширяет рамку в клиентскую область.
    """
    if sys.platform != "win32":
        return False

    try:
        window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        hwnd = int(window.winId())
        dwmapi = ctypes.windll.dwmapi

        # 1. Заголовок окна Windows (DWMWA_USE_IMMERSIVE_DARK_MODE = 20)
        dark_mode = ctypes.c_int(1 if is_dark else 0)
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))

        # 2. Расширение рамки на всю клиентскую область окна
        margins = MARGINS(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

        # 3. Аппаратный Acrylic (DWMWA_SYSTEMBACKDROP_TYPE = 38, значение 3 = Acrylic)
        backdrop_type = ctypes.c_int(3)
        res = dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop_type), ctypes.sizeof(backdrop_type))

        # Fallback для старых версий Windows 10
        if res != 0:
            class ACCENT_POLICY(ctypes.Structure):
                _fields_ = [
                    ("AccentState", ctypes.c_int),
                    ("AccentFlags", ctypes.c_int),
                    ("GradientColor", ctypes.c_uint),
                    ("AnimationId", ctypes.c_int),
                ]

            class WINCOMPATTRDATA(ctypes.Structure):
                _fields_ = [
                    ("Attribute", ctypes.c_int),
                    ("Data", ctypes.POINTER(ACCENT_POLICY)),
                    ("SizeOfData", ctypes.c_size_t),
                ]

            tint = 0x99111318 if is_dark else 0x99F5F7FA
            policy = ACCENT_POLICY(3, 0, tint, 0)
            data = WINCOMPATTRDATA(19, ctypes.pointer(policy), ctypes.sizeof(policy))
            ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))

        return True
    except Exception:
        return False


apply_window_blur = apply_windows_acrylic


# ==============================================================================
# 5. Реактивный менеджер тем Google Pixel Monet
# ==============================================================================

class ThemeManager(QObject):
    """
    Реактивный менеджер тем Google Pixel Monet.
    Оповещает все компоненты об изменении темы и обновляет глобальный QSS.
    """

    theme_changed = Signal(str)

    _instance: Optional[ThemeManager] = None

    @classmethod
    def get_instance(cls, initial_key: str = DEFAULT_THEME, initial_mode: str = DEFAULT_MODE) -> ThemeManager:
        if cls._instance is None:
            cls._instance = ThemeManager(initial_key=initial_key, initial_mode=initial_mode)
        return cls._instance

    def __init__(self, initial_key: str = DEFAULT_THEME, initial_mode: str = DEFAULT_MODE, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._current_key = initial_key if initial_key in PIXEL_THEMES_DARK else DEFAULT_THEME
        self._current_mode = initial_mode if initial_mode in ("dark", "light") else DEFAULT_MODE

    @property
    def current_key(self) -> str:
        return self._current_key

    @property
    def current_mode(self) -> str:
        return self._current_mode

    @property
    def palette(self) -> Dict[str, Any]:
        return get_theme(self._current_key, mode=self._current_mode)

    def set_theme(self, theme_key: str, mode: Optional[str] = None) -> None:
        new_mode = mode or self._current_mode
        if theme_key == self._current_key and new_mode == self._current_mode:
            return
        if theme_key in PIXEL_THEMES_DARK:
            self._current_key = theme_key
        if new_mode in ("dark", "light"):
            self._current_mode = new_mode

        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(self._current_key, mode=self._current_mode))
        self.theme_changed.emit(self._current_key)


# ==============================================================================
# 6. Генерация Zero-Border QSS таблицы стилей
# ==============================================================================

def get_stylesheet(theme_key: str = DEFAULT_THEME, mode: str = "dark") -> str:
    """Генерирует QSS-стили для Material 3 Expressive с эстетикой матового стекла (Frosted Glass)."""
    t = get_theme(theme_key, mode=mode)
    panel_bg = t["panel_bg"]
    center_bg = t["center_bg"]
    card_bg = t["card_bg"]
    card_hover = t["card_hover"]
    panel_border = t.get("panel_border", "transparent")
    center_border = t.get("center_border", "transparent")
    card_border = t.get("card_border", "transparent")
    card_border_hover = t.get("card_border_hover", "transparent")
    primary = t["primary"]
    primary_hover = t.get("primary_hover", primary)
    on_primary = t["on_primary"]
    secondary_container = t["secondary_container"]
    on_secondary = t["on_secondary"]
    text_primary = t["text_primary"]
    text_secondary = t["text_secondary"]
    sb_handle = t.get("scrollbar_handle", "rgba(255, 255, 255, 0.16)")
    sb_hover = t.get("scrollbar_hover", "rgba(255, 255, 255, 0.32)")
    is_dark = t.get("is_dark", True)

    dropdown_bg = "#1A1D24" if is_dark else "#FFFFFF"
    menu_bg = "#1E222B" if is_dark else "#FFFFFF"
    tooltip_bg = "#252932" if is_dark else "#313033"
    tooltip_fg = "#E2E2E9" if is_dark else "#F4EFF4"
    pb_bg = "rgba(255, 255, 255, 25)" if is_dark else "rgba(0, 0, 0, 20)"
    btn_hover_bg = "rgba(255, 255, 255, 0.22)" if is_dark else "rgba(0, 0, 0, 0.08)"
    btn_pressed_bg = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.14)"
    placeholder_fg = "rgba(255, 255, 255, 0.45)" if is_dark else "rgba(0, 0, 0, 0.40)"
    slider_handle_bg = "#22252D" if is_dark else "#FFFFFF"

    return f"""
/* 1. Базовые свойства окна и прозрачность подложки */
QMainWindow, QDialog {{
    background: transparent;
    color: {text_primary};
    font-family: 'Roboto', 'Segoe UI Variable Display', 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
    border: none;
}}

QWidget {{
    color: {text_primary};
    font-family: 'Roboto', 'Segoe UI Variable Display', 'Segoe UI', -apple-system, sans-serif;
    outline: none;
}}

QWidget#centralWidget, QWidget#rootContainer {{
    background: transparent;
    border: none;
}}

/* 2. Контейнеры основных колонок (Матовое стекло без белых рамок) */
QFrame#LeftPanel, QFrame#RightPanel, QFrame#sidebarCard, QFrame#rightInspector {{
    background-color: {panel_bg};
    border-radius: 24px;
    border: none;
}}

QFrame#CenterPanel, QFrame#centerCard {{
    background-color: {center_bg};
    border-radius: 28px;
    border: none;
}}

/* 3. Сплиттер без визуальных разделителей */
QSplitter::handle {{
    background-color: transparent;
    width: 0px;
    height: 0px;
    border: none;
}}

/* 4. Сверхтонкие полупрозрачные скроллбары (6px, без рамок и стрелок) */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 4px 2px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {sb_handle};
    min-height: 32px;
    border-radius: 3px;
    border: none;
}}
QScrollBar::handle:vertical:hover {{
    background: {sb_hover};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0px;
    border: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 2px 4px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {sb_handle};
    min-width: 32px;
    border-radius: 3px;
    border: none;
}}
QScrollBar::handle:horizontal:hover {{
    background: {sb_hover};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
    width: 0px;
    border: none;
}}

/* 5. Кнопки действий: Primary Extended FAB (капсулы 44px, radius 22px, Zero Border) */
QPushButton#PrimaryFAB, QPushButton[primary="true"], QPushButton#primaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {primary}, stop:1 {primary_hover});
    color: {on_primary};
    border: none;
    border-radius: 22px;
    min-height: 44px;
    max-height: 44px;
    padding: 0 24px;
    font-weight: 600;
    font-size: 14px;
}}
QPushButton#PrimaryFAB:hover, QPushButton[primary="true"]:hover, QPushButton#primaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {primary_hover}, stop:1 {primary});
    color: {on_primary};
    border: none;
    border-radius: 22px;
}}
QPushButton#PrimaryFAB:pressed, QPushButton[primary="true"]:pressed, QPushButton#primaryButton:pressed {{
    background-color: {primary};
    color: {on_primary};
    border: none;
    border-radius: 22px;
}}

/* 6. Тональные кнопки: TonalButton (капсулы 32px, radius 16px, Zero Border) */
QPushButton#TonalButton {{
    background-color: {secondary_container};
    color: {on_secondary};
    border: none;
    border-radius: 16px;
    min-height: 32px;
    max-height: 32px;
    padding: 0 14px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton#TonalButton:hover {{
    background-color: {card_hover};
    border: none;
    border-radius: 16px;
}}
QPushButton#TonalButton:pressed {{
    background-color: {btn_pressed_bg};
    border: none;
    border-radius: 16px;
}}

/* Кнопки по умолчанию */
QPushButton {{
    background-color: {secondary_container};
    color: {on_secondary};
    border: none;
    border-radius: 21px;
    min-height: 42px;
    padding: 0 20px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {card_hover};
    border: none;
}}
QPushButton:pressed {{
    background-color: {btn_pressed_bg};
    border: none;
}}

/* 7. Поля ввода и поисковая строка (капсулы 44px, radius 22px, матовое стекло, Zero Border) */
QLineEdit#SearchBar {{
    background-color: {card_bg};
    border: none;
    border-radius: 22px;
    min-height: 44px;
    max-height: 44px;
    padding: 0 20px;
    color: {text_primary};
    placeholder-text-color: {placeholder_fg};
    font-size: 14px;
}}
QLineEdit#SearchBar:hover {{
    background-color: {card_hover};
    border: none;
}}
QLineEdit#SearchBar:focus {{
    background-color: {card_hover};
    border: 1.5px solid {primary};
}}

QLineEdit, QDateTimeEdit, QSpinBox, QTextEdit, QPlainTextEdit {{
    background-color: {card_bg};
    border: none;
    border-radius: 18px;
    padding: 0 18px;
    color: {text_primary};
    placeholder-text-color: {placeholder_fg};
    font-size: 13px;
    selection-background-color: {primary};
    selection-color: {on_primary};
}}
QLineEdit:hover, QDateTimeEdit:hover, QSpinBox:hover, QTextEdit:hover, QPlainTextEdit:hover {{
    background-color: {card_hover};
    border: none;
}}
QLineEdit:focus, QDateTimeEdit:focus, QSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    background-color: {card_hover};
    border: 1.5px solid {primary};
}}

/* 8. Выпадающие списки (Pill ComboBox из матового стекла, Zero Border) */
QComboBox {{
    background-color: {card_bg};
    border: none;
    border-radius: 22px;
    padding: 0 16px;
    color: {text_primary};
    font-size: 13px;
    font-weight: 500;
}}
QComboBox:hover {{
    background-color: {card_hover};
    border: 1px solid {primary};
}}
QComboBox:focus {{
    background-color: {card_hover};
    border: 1.5px solid {primary};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px;
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {dropdown_bg};
    border: none;
    border-radius: 16px;
    padding: 8px;
    selection-background-color: {secondary_container};
    selection-color: {on_secondary};
    color: {text_primary};
}}

/* 9. Тонкий мини прогресс-бар Material 3 Expressive (6px, скругление 3px, скрытый текст) */
QProgressBar {{
    background-color: {pb_bg};
    border: none;
    border-radius: 3px;
    height: 6px;
    max-height: 6px;
    min-height: 6px;
    text-align: center;
    font-size: 1px;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {primary};
    border-radius: 3px;
    border: none;
}}

/* 9.1 Интерактивный ползунок QSlider Material 3 Expressive */
QSlider {{
    min-height: 22px;
    max-height: 22px;
    background: transparent;
}}
QSlider::groove:horizontal {{
    border: none;
    height: 6px;
    background-color: {pb_bg};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background-color: {primary};
    border-radius: 3px;
}}
QSlider::add-page:horizontal {{
    background-color: {pb_bg};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background-color: {slider_handle_bg};
    border: 3px solid {primary};
    width: 14px;
    height: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background-color: {primary};
    border: 2px solid {slider_handle_bg};
    width: 16px;
    height: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}}

/* 10. Всплывающие подсказки Tooltips (Матовое стекло) */
QToolTip {{
    background-color: {tooltip_bg};
    color: {tooltip_fg};
    border: none;
    border-radius: 10px;
    padding: 6px 12px;
    font-size: 11px;
}}

/* 11. Контекстные меню */
QMenu {{
    background-color: {menu_bg};
    color: {text_primary};
    border: none;
    border-radius: 14px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 16px;
    border-radius: 8px;
    border: none;
}}
QMenu::item:selected {{
    background-color: {secondary_container};
    color: {on_secondary};
}}
QMenu::item {{
    padding: 8px 16px;
    border-radius: 8px;
    border: none;
}}
QMenu::item:selected {{
    background-color: {secondary_container};
    color: {on_secondary};
}}
"""


get_md3_stylesheet = get_stylesheet

# Константы для обратной совместимости со styles.py и диалогами
MD3_PRIMARY = PIXEL_THEMES["pixel_blue"]["primary"]
MD3_ON_PRIMARY = PIXEL_THEMES["pixel_blue"]["on_primary"]
MD3_PRIMARY_CONTAINER = "rgba(168, 199, 250, 0.24)"
MD3_SECONDARY_CONTAINER = PIXEL_THEMES["pixel_blue"]["secondary_container"]
MD3_ON_PRIMARY_CONTAINER = "#D3E4FF"
MD3_ON_SECONDARY_CONTAINER = "#D3E4FF"
MD3_SURFACE = "#0E1117"
MD3_SURFACE_CONTAINER_LOW = PIXEL_THEMES["pixel_blue"]["panel_bg"]
MD3_SURFACE_CONTAINER = PIXEL_THEMES["pixel_blue"]["center_bg"]
MD3_SURFACE_CONTAINER_HIGH = "rgba(48, 57, 76, 215)"
MD3_BORDER = "none"
MD3_BORDER_HOVER = "none"
MD3_BORDER_FOCUS = "none"
MD3_TEXT_PRIMARY = "#E2E2E9"
MD3_TEXT_SECONDARY = "#8E9099"
MD3_TEXT_MUTED = "#6B6E76"

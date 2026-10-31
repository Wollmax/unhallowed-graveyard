"""UniVault UI package — Google Material 3 Expressive & Pixel Monet."""

from .theme import (
    DEFAULT_MODE,
    DEFAULT_THEME,
    PIXEL_THEMES,
    PIXEL_THEMES_BY_MODE,
    PIXEL_THEMES_DARK,
    PIXEL_THEMES_LIGHT,
    ThemeManager,
    apply_windows_acrylic,
    get_stylesheet,
    get_theme,
    load_application_fonts,
)
from .cards import (
    SubjectCard,
    SubjectCardWidget,
    TaskCard,
    TaskCardWidget,
    ThemeSwatchButton,
)
from .dialogs import AddSubjectDialog, AddTaskDialog, SettingsDialog
from .file_inspector import (
    FileDropZoneSection,
    FileItemWidget,
    TaskInspectorWidget,
)
from .icons import (
    MATERIAL_SVG_PATHS,
    get_material_icon,
    get_material_pixmap,
    get_material_svg,
)
from .main_window import MainWindow

__all__ = [
    "DEFAULT_THEME",
    "PIXEL_THEMES",
    "ThemeManager",
    "apply_windows_acrylic",
    "get_stylesheet",
    "get_theme",
    "load_application_fonts",
    "SubjectCard",
    "SubjectCardWidget",
    "TaskCard",
    "TaskCardWidget",
    "ThemeSwatchButton",
    "AddSubjectDialog",
    "AddTaskDialog",
    "SettingsDialog",
    "FileItemWidget",
    "FileDropZoneSection",
    "TaskInspectorWidget",
    "MATERIAL_SVG_PATHS",
    "get_material_icon",
    "get_material_pixmap",
    "get_material_svg",
    "MainWindow",
]

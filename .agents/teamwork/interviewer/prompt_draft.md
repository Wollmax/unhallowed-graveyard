Fix UI styling, clipping, popup dismissal, theme colors, and layout defects across components in UniVault (PySide6 / Material 3 Expressive desktop application).

Working directory: c:\Prog
Integrity mode: development

## Requirements

### R1. Settings button visual styling
Align the Settings button ("Настройки") outline and hover/active highlight styling to match the visual standard of the other action buttons in the main window.

### R2. Top card hover clipping prevention
Ensure that when hovering over the top subject card and it elevates (e.g. -4px translation), the card and its shadow/borders are not clipped at the top boundary.

### R3. Transparency and foreground contrast balance
Adjust window transparency handling so that increasing transparency affects the background window surface more strongly while preserving opacity and contrast on foreground elements (cards, text, inputs), preventing the UI from becoming dark or muddy in the light theme when transparency is high (e.g. at 35%).

### R4. "New work" popup menu dismissal fix
Fix the issue where triggering "Новая работа" (add new assignment/practical) causes the popup menu to flash for a second and immediately disappear, ensuring it stays open until user interaction or selection.

### R5. Settings page colors and profile text background
Correct text colors in the settings page to properly follow the active theme, and eliminate the unwanted solid white background behind text and input fields in the profile settings section.

### R6. Settings menu margin alignment
Equalize and balance the left and right margins/paddings of the settings menu and its content areas.

### R7. File inspector checklist button styling
Fix the appearance of the checklist add button (+) in the file inspector so its shape, icon alignment, and styling match the design system.

### R8. Project constraints
Do NOT touch or modify any files in `c:\prog anitg`. Do NOT modify the report generator `FSManager.generate_task_report` in `src/fs_manager.py`.

## Verification Resources
- Existing test suites: `python test_ui.py` and `python test_core.py` run from `c:\Prog`.
- Application startup and standalone verification: launch `python -m src.main` or PySide6 test scripts to inspect widget styling, clipping, menus, and transparency behavior.

## Acceptance Criteria

### Visual and Layout
- [ ] The Settings button outline and highlight match the other action buttons in the header/main window.
- [ ] The top subject card does not clip at the top boundary during hover elevation.
- [ ] Settings page left and right content margins are equal and symmetrical.
- [ ] The checklist add button (+) in the file inspector renders with proper Material 3 Expressive styling without visual artifacts.

### Theming and Functionality
- [ ] In light theme with transparency enabled (up to 35% or higher), foreground cards, inputs, and text remain clean, bright, and legible while background opacity decreases.
- [ ] Clicking "Новая работа" keeps the popup menu visible and responsive until an action is selected or the user clicks away.
- [ ] Profile settings text and input fields render with transparent/theme-compliant backgrounds without opaque white boxes.
- [ ] All settings page labels and values match the theme text colors in both light and dark themes.

### Integrity and Verification
- [ ] Existing tests in `test_ui.py` and `test_core.py` pass without regressions.
- [ ] The directory `c:\prog anitg` is untouched.
- [ ] `FSManager.generate_task_report` in `src/fs_manager.py` remains unchanged.

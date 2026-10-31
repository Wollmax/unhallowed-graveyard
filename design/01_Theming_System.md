## 2. Theming System

### 2.1 Color Schemes

Material 3 provides comprehensive color theming through `ColorScheme`. You can use predefined light and dark color schemes or create dynamic color schemes that adapt to the user's device.

**Available Color Scheme APIs:**
- `lightColorScheme()` - Creates a light color scheme
- `darkColorScheme()` - Creates a dark color scheme
- `dynamicLightColorScheme(context)` - Creates a dynamic light color scheme (API 31+)
- `dynamicDarkColorScheme(context)` - Creates a dynamic dark color scheme (API 31+)

Dynamic color schemes automatically adapt to the user's wallpaper and system preferences, providing a personalized experience.

**See also:**
- [ColorScheme API](#colorscheme) - Detailed API reference
- [MaterialTheme](#materialtheme) - Apply color schemes to your app
- [Dynamic Color APIs](#55-dynamic-color-apis) - Implementation details for dynamic colors

### 2.2 Typography

The `Typography` class defines the typographic hierarchy for your app, ensuring consistent text styling across all components.

**See also:**
- [MaterialTheme](#materialtheme) - Apply typography to your app
- [ProvideTextStyle](#providetextstyle) - Override text styles locally

### 2.3 Shapes

The `Shapes` class defines the shape system for your app, controlling corner radii and other shape properties for components.

**See also:**
- [MaterialTheme](#materialtheme) - Apply shapes to your app
- [Button with Shape Morphing](#button-expressive-with-shape-morphing) - Example of expressive shape animations

---

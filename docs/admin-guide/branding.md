# ColdFront Branding

This document explains how to change the ColdFront theme and its colors.

## Themes

A theme is a set of colors and sizes. ColdFront uses the DaisyUI theme system. ColdFront ships two themes:

| Theme | Use |
|-------|-----|
| `cflight` | The light theme. It is the default. |
| `cfdark` | The dark theme. It is used for dark mode. |

The stock ColdFront themes are defined in `src/frontend/src/styles/coldfront.css`.

## How to customize the default themes

To customize a theme, use the same structure as the theme. Set the color variables that you want to change. Each theme defines the standard daisyUI color set: `base-100` to `base-300`, `primary`, `secondary`, `accent`, `neutral`, `info`, `success`, `warning`, `error`, and the `-content` color of each. You can override any of these variables.

Use DaisyUI's theme generator to create your custom theme colors [here](https://daisyui.com/theme-generator).

### Example: change the accent color and the primary color

This example changes two colors: the accent color and the primary color. It changes them for both themes.

```css
/* Light theme (cflight) */
:root,
[data-theme="cflight"] {
  --color-accent: oklch(70% 0.15 200);
  --color-accent-content: oklch(30% 0.05 200);
  --color-primary: oklch(55% 0.2 270);
  --color-primary-content: oklch(95% 0.02 270);
}

/* Dark theme (cfdark) */
[data-theme="cfdark"] {
  --color-accent: oklch(85% 0.1 200);
  --color-accent-content: oklch(20% 0.04 200);
  --color-primary: oklch(75% 0.15 270);
  --color-primary-content: oklch(20% 0.04 270);
}
```

Always change a color and its `-content` color together. The `-content` color is the color of text and icons on the color. If you do not change both, the contrast may fail. Use a valid CSS color value. ColdFront uses the `oklch()` color format. You can use `oklch()`, `hex`, or `rgb()`.

In system mode, the browser chooses the theme. To change the dark colors in system mode, add this block:

```css
@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) {
    --color-accent: oklch(85% 0.1 200);
    --color-accent-content: oklch(20% 0.04 200);
    --color-primary: oklch(75% 0.15 270);
    --color-primary-content: oklch(20% 0.04 270);
  }
}
```

Put your color changes in this file and run `collectstatic` to copy the file to the static root.

`/usr/share/coldfront/site/static/assets/css/coldfront-site.css`


> Note: The `SITE_STATIC` environment variable can point to a different site static directory. If it is set, put the file in that directory instead.

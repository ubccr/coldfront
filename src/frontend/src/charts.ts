// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0
//
// daisyUI-themed Chart.js charts for the c-cf.chart cotton components.
//
// The cotton components render a <canvas> carrying data-cf-chart-* attributes
// (type, legend, data, options). initCharts() scans for those canvases and
// builds a Chart.js chart themed to the active daisyUI theme (cflight/cfdark).
//
//   - datasets/slices are auto-colored from the daisyUI palette unless the
//     payload already supplies a color
//   - explicit colors accept daisyUI names ("success"), "--color-x" CSS vars,
//     "-light" alpha variants, or any raw CSS color
//   - hover colors are set explicitly so Chart.js never runs getHoverColor()
//     (which can't parse oklch() and falls back to black)
//   - charts rebuild from their pristine raw data on theme changes so palette
//     and resolved colors always reflect the active theme
//
// themeColor()/resolveColor() resolve CSS custom properties (full oklch()
// strings in ColdFront's themes) to plain rgba() strings Chart.js can draw.

import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  type ChartData,
  type ChartType,
  DoughnutController,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";

Chart.register(
  BarController,
  BarElement,
  LineController,
  LineElement,
  PointElement,
  DoughnutController,
  ArcElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
);

// DaisyUI palette used to auto-color datasets/slices. Cycles
// primary → secondary → accent → info → success → warning → error.
const PALETTE = [
  "primary",
  "secondary",
  "accent",
  "info",
  "success",
  "warning",
  "error",
];

// daisyUI color names → CSS custom properties on <html>.
const CSS_VARS: Record<string, string> = {
  primary: "--color-primary",
  "primary-content": "--color-primary-content",
  secondary: "--color-secondary",
  "secondary-content": "--color-secondary-content",
  accent: "--color-accent",
  "accent-content": "--color-accent-content",
  neutral: "--color-neutral",
  "neutral-content": "--color-neutral-content",
  info: "--color-info",
  "info-content": "--color-info-content",
  success: "--color-success",
  "success-content": "--color-success-content",
  warning: "--color-warning",
  "warning-content": "--color-warning-content",
  error: "--color-error",
  "error-content": "--color-error-content",
  "base-100": "--color-base-100",
  "base-200": "--color-base-200",
  "base-300": "--color-base-300",
  "base-content": "--color-base-content",
};

// Alpha applied to "-light" color variants (e.g. "primary-light").
const LIGHT_ALPHA = 0.4;

// Round charts color one palette entry per slice; cartesian charts color per
// dataset.
const POLAR_TYPES = ["pie", "doughnut", "polarArea"];

// Minimal shape of the dataset fields we assign (datasets are a union type).
interface ThemedDataset {
  data: unknown[];
  backgroundColor?: string | string[];
  borderColor?: string | string[];
  hoverBackgroundColor?: string | string[];
  hoverBorderColor?: string | string[];
}

interface ChartSpec {
  type: ChartType;
  data: ChartData;
  options: object;
  legend: string;
}

interface ChartEntry {
  spec: ChartSpec;
  chart: Chart;
}

/** Return a throwaway 2D context used only to resolve colors to rgba(). */
function getProbeContext(): CanvasRenderingContext2D {
  const c = document
    .createElement("canvas")
    .getContext("2d", { willReadFrequently: true });
  if (!c) {
    throw new Error("2D canvas context is not available");
  }
  return c;
}

const ctx = getProbeContext();

/** Resolve any CSS color (including oklch) to a plain rgba() string. */
function toRgb(cssColor: string): string {
  ctx.clearRect(0, 0, 1, 1);
  ctx.fillStyle = cssColor;
  ctx.fillRect(0, 0, 1, 1);
  const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
  return `rgba(${r}, ${g}, ${b}, ${a / 255})`;
}

function themeColor(name: string): string {
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return toRgb(value);
}

/** Replace a color's alpha component (rgba(...)) with a fixed value. */
function withAlpha(rgb: string, alpha: number): string {
  return rgb.replace(/[\d.]+\)$/, `${alpha})`);
}

/**
 * Resolve a single color value to a string Chart.js can draw:
 *   "success"        → live --color-success CSS value
 *   "primary-light"  → live --color-primary at 40% alpha
 *   "--color-x"      → live CSS value of that var
 *   hex/rgb/oklch/…  → passed through unchanged
 */
function resolveColor(val: string): string {
  const isLight = val.length > 6 && val.endsWith("-light");
  const base = isLight ? val.slice(0, -6) : val;
  const varName = CSS_VARS[base] ?? (base.startsWith("--") ? base : null);

  if (varName) {
    const rgb = themeColor(varName);
    return isLight ? withAlpha(rgb, LIGHT_ALPHA) : rgb;
  }
  // Raw CSS color (hex, rgb, oklch, named color).
  return isLight ? withAlpha(toRgb(val), LIGHT_ALPHA) : val;
}

/** Resolve a color or an array of colors (e.g. one per bar/slice). */
function resolveColors(val: string | string[]): string | string[] {
  if (Array.isArray(val)) {
    return val.map((c) => resolveColor(c));
  }
  return resolveColor(val);
}

/** Deep-clone via JSON so Chart.js mutations never touch the pristine raw data. */
function clone<T>(val: T): T {
  try {
    return JSON.parse(JSON.stringify(val)) as T;
  } catch {
    return {} as T;
  }
}

/** Parse a JSON string with a fallback so a malformed payload never throws. */
function parseJson(
  text: string | null | undefined,
  fallback: unknown,
): unknown {
  if (!text) return fallback;
  try {
    return JSON.parse(text);
  } catch {
    return fallback;
  }
}

/**
 * Color a cloned ChartData object in place before Chart.js builds it.
 * Auto-color from the palette when absent, otherwise resolve explicit colors;
 * set hover colors only if missing.
 */
function colorizeData(type: ChartType, data: ChartData): void {
  const isPolar = POLAR_TYPES.includes(type);
  const labels = data.labels ?? [];
  const datasets = data.datasets as unknown as ThemedDataset[];

  datasets.forEach((ds, i) => {
    // ── backgroundColor ──────────────────────────────────────────────────────
    if (!ds.backgroundColor) {
      if (isPolar) {
        // Polar types need one color per slice.
        ds.backgroundColor = labels.length
          ? labels.map((_, j) => resolveColor(PALETTE[j % PALETTE.length]))
          : resolveColor(PALETTE[i % PALETTE.length]);
      } else {
        ds.backgroundColor = resolveColor(PALETTE[i % PALETTE.length]);
      }
    } else {
      ds.backgroundColor = resolveColors(ds.backgroundColor);
    }

    // ── borderColor ──────────────────────────────────────────────────────────
    if (!ds.borderColor) {
      if (type === "polarArea") {
        // Solid per-slice border over the translucent fill.
        ds.borderColor = labels.length
          ? labels.map((_, j) => resolveColor(PALETTE[j % PALETTE.length]))
          : resolveColor(PALETTE[i % PALETTE.length]);
      } else if (!isPolar) {
        ds.borderColor = resolveColor(PALETTE[i % PALETTE.length]);
      }
    } else {
      ds.borderColor = resolveColors(ds.borderColor);
    }

    // ── hover colors ─────────────────────────────────────────────────────────
    // Set explicitly to prevent Chart.js from running getHoverColor() which
    // uses @kurkle/color — a library that can't parse oklch() values and falls
    // back to black.
    if (!ds.hoverBackgroundColor) {
      ds.hoverBackgroundColor = ds.backgroundColor;
    }
    if (!ds.hoverBorderColor) {
      ds.hoverBorderColor = ds.borderColor;
    }
  });
}

/**
 * Set Chart.js global defaults to match the daisyUI theme (text, grid, tooltip,
 * legend, arcs/bars/lines/points). Re-run on theme changes so color-dependent
 * defaults (text, grid, tooltip backgrounds) track the active theme.
 */
function applyGlobalDefaults(): void {
  const text = themeColor("--color-base-content");
  const grid = themeColor("--color-base-300");

  Chart.defaults.font.family = "inherit";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = text;
  Chart.defaults.borderColor = grid;

  // Cartesian scales: hide grid lines by default.
  Chart.defaults.scales.linear.grid = { display: false };
  Chart.defaults.scales.category.grid = { display: false };

  // Radial scale (radar/polarArea): keep rings and spokes framing the shape.
  // Chart.js may not have initialised these sub-objects yet, so ensure they
  // exist before mutating in place (replacing them would wipe Chart.js's own
  // radial defaults). The defaults shape is too loose to type tightly.
  if (Chart.defaults.scales.radialLinear) {
    // biome-ignore lint/suspicious/noExplicitAny: Chart.js defaults shape is loose
    const radial = Chart.defaults.scales.radialLinear as any;
    radial.ticks ??= {};
    radial.grid ??= {};
    radial.angleLines ??= {};
    radial.ticks.backdropColor = "transparent";
    radial.grid.display = true;
    radial.angleLines.display = true;
  }

  // Tooltip: base-200 background, base-content text, subtle border.
  if (Chart.defaults.plugins.tooltip) {
    Chart.defaults.plugins.tooltip.backgroundColor =
      themeColor("--color-base-200");
    Chart.defaults.plugins.tooltip.titleColor = text;
    Chart.defaults.plugins.tooltip.bodyColor = text;
    Chart.defaults.plugins.tooltip.borderColor = grid;
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.padding = 12;
  }

  // Legend: text color and compact box height.
  if (Chart.defaults.plugins.legend) {
    Chart.defaults.plugins.legend.labels.color = text;
    Chart.defaults.plugins.legend.labels.boxHeight = 8;
  }

  // Arcs (pie/doughnut/polarArea): no borders so slices read as one shape.
  if (Chart.defaults.elements.arc) {
    Chart.defaults.elements.arc.borderWidth = 0;
  }

  // Bars: rounded corners, no borders.
  if (Chart.defaults.elements.bar) {
    Chart.defaults.elements.bar.borderRadius = 4;
    Chart.defaults.elements.bar.borderWidth = 0;
  }

  // Lines: smooth, 2px, no fill.
  if (Chart.defaults.elements.line) {
    Chart.defaults.elements.line.tension = 0.35;
    Chart.defaults.elements.line.borderWidth = 2;
    Chart.defaults.elements.line.fill = false;
  }

  // Points: generous hit/hover area.
  if (Chart.defaults.elements.point) {
    Chart.defaults.elements.point.hoverRadius = 4;
    Chart.defaults.elements.point.hitRadius = 12;
  }

  // Line charts: hide point markers and show tooltips on nearest x without an
  // exact point hit. Same ensure-exists mutation pattern as the radial scale.
  if (Chart.overrides.line) {
    // biome-ignore lint/suspicious/noExplicitAny: Chart.js overrides shape is loose
    const line = Chart.overrides.line as any;
    line.elements ??= {};
    line.elements.point ??= {};
    line.elements.point.radius = 0;
    line.interaction = { mode: "index", intersect: false };
    line.plugins ??= {};
    line.plugins.tooltip = {
      ...line.plugins.tooltip,
      mode: "index",
      intersect: false,
    };
  }
}

/** Build a Chart.js chart from a pristine spec, coloring a clone of the data. */
function buildChart(canvas: HTMLCanvasElement, spec: ChartSpec): Chart {
  const data = clone(spec.data);
  colorizeData(spec.type, data);
  return new Chart(canvas, {
    type: spec.type,
    data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend:
          spec.legend === "none"
            ? { display: false }
            : { position: spec.legend as "top" | "bottom" | "left" | "right" },
      },
      ...clone(spec.options),
    },
  });
}

// Live chart registry, keyed by canvas. Charts rebuild from their pristine raw
// data on theme changes, so a WeakMap (which can't be walked) isn't enough.
const entries = new Map<HTMLCanvasElement, ChartEntry>();

/**
 * Initialise charts inside a root (document or an htmx-swapped fragment).
 * Each canvas[data-cf-chart-type] becomes one Chart.js chart; data and options
 * are inline JSON in the data-cf-chart-data/options attributes.
 */
export function initCharts(root: Document | HTMLElement = document): void {
  root
    .querySelectorAll<HTMLCanvasElement>("canvas[data-cf-chart-type]")
    .forEach((canvas) => {
      if (entries.has(canvas)) return; // already initialised

      const type = canvas.dataset.cfChartType as ChartType | undefined;
      if (!type) return;

      const data = parseJson(canvas.dataset.cfChartData, {}) as ChartData;
      const options = parseJson(canvas.dataset.cfChartOptions, {}) as object;
      const legend = canvas.dataset.cfChartLegend ?? "top";

      const spec = { type, data, options, legend };
      entries.set(canvas, { spec, chart: buildChart(canvas, spec) });
    });
}

/** Re-theme every live chart: re-apply defaults and rebuild from raw data. */
function retheme(): void {
  applyGlobalDefaults();
  for (const [canvas, entry] of entries) {
    if (!canvas.isConnected) {
      entry.chart.destroy(); // canvas was removed (e.g. by an htmx swap)
      entries.delete(canvas);
    } else {
      entry.chart.destroy();
      entry.chart = buildChart(canvas, entry.spec);
    }
  }
}

applyGlobalDefaults();

// Theme changes: the data-theme attribute (cflight/cfdark, set by c-cf.mode_toggle)
// and OS preference both re-theme live charts.
new MutationObserver(retheme).observe(document.documentElement, {
  attributes: true,
  attributeFilter: ["data-theme"],
});

matchMedia("(prefers-color-scheme: dark)").addEventListener("change", retheme);

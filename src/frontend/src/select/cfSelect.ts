// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import Alpine from "alpinejs";

export interface CfOption {
  value: string;
  label: string;
  depth?: number | null;
  parent?: string | null;
  count?: number | string | null;
  description?: string | null;
  extraColumns?: string[] | null;
  disabled?: boolean | null;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"|'/g, (c) => (c === '"' ? "&quot;" : "&#39;"));
}

/**
 * Register the ColdFront Select `cfSelect` Alpine component.
 *
 * The markup lives in the custom alpine select widget; this module only
 * provides the client UI state. A hidden native <select> is the value sink:
 * options and the initial selection are parsed from it, and every change is
 * written back to it + a bubbling `change` event.
 *
 * Two modes:
 *  - local: options are parsed from the hidden select and filtered client-side.
 *  - remote (API-backed, `data-cf-remote`): options are empty initially and
 *    fetched from `data-url` on focus (load-on-focus) and on search (backend
 *    search via `q`). Static/dynamic query params + `{{var}}` path tokens come
 *    from `data-static-params` / `data-dynamic-params` and the URL; dependency
 *    fields are subscribed to via their bubbling `change` events.
 *
 * The trigger is a WAI-ARIA 1.2 combobox: the search <input> is the combobox
 * element carrying role/aria-* and keyboard handling.
 *
 * Registered at module load — before `Alpine.start()` — so the initial DOM is
 * initialized (see coldfront.ts). HTMX-swapped fragments are re-initialized via
 * `Alpine.initTree()` in the htmx afterSettle hook.
 */
export function registerCfSelect(): void {
  Alpine.data("cfSelect", () => ({
    open: false,
    search: "",
    options: [] as CfOption[],
    selected: [] as CfOption[],
    activeIndex: -1,
    invalid: false,
    disabled: false,

    fieldId: "",
    label: "",
    placeholder: "",
    multiple: false,
    required: false,
    minSearch: 0,
    colorMode: false,
    noSearch: false,

    // Remote (API-backed) mode
    remote: false,
    apiUrl: "",
    nullOption: "",
    valueField: "id",
    labelField: "display",
    disabledField: "",
    descriptionField: "description",
    depthField: "_depth",
    parentField: "",
    countField: "",
    extraColumns: [] as string[],
    staticParams: {} as Record<string, string[]>,
    queryParams: {} as Record<string, string[]>,
    dynamicParams: [] as { fieldName: string; queryParam: string }[],
    pathValues: {} as Record<string, string>,
    loading: false,
    lastSearch: null as string | null,
    maxOptions: 100,
    _searchTimer: 0 as number,
    _abort: null as AbortController | null,
    _select: null as HTMLSelectElement | null,

    init() {
      // The root contains exactly one <select>: the hidden native widget sink.
      this._select = this.$el.querySelector<HTMLSelectElement>("select");
      if (!this._select) return;

      this.fieldId = this.$el.dataset.cfFieldId || "";
      this.label = this.$el.dataset.cfLabel || "";
      this.placeholder = this.$el.dataset.cfPlaceholder || "";
      this.minSearch = parseInt(this.$el.dataset.cfMinSearch || "0", 10);
      this.colorMode = this.$el.dataset.cfColor === "1";
      this.remote = this.$el.dataset.cfRemote === "1";
      this.noSearch = this.$el.dataset.cfSearch === "0";

      this.multiple = this._select.multiple;
      this.required = this._select.required;
      this.disabled = this._select.disabled;
      this.invalid = this.$el.dataset.cfInvalid === "1";

      // Keep the hidden native select out of the tab order (the visible trigger
      // carries tab focus) but still focusable, so browser native validation can
      // run on it and fire `invalid` for required fields.
      this._select.tabIndex = -1;
      this._select.addEventListener("invalid", () => {
        this.invalid = true;
      });

      if (this.multiple) {
        this.selected = Array.from(this._select.selectedOptions)
          .filter((o) => o.value !== "")
          .map((o) => ({
            value: o.value,
            label: o.textContent || "",
          }));
      } else {
        const si = this._select.selectedIndex;
        const o = si >= 0 ? this._select.options[si] : null;
        if (o && o.value !== "") {
          this.selected = [{ value: o.value, label: o.textContent || "" }];
        }
      }

      if (this.remote) {
        this.apiUrl = this._select.dataset.url || "";
        this.nullOption = this._select.dataset.nullOption || "";
        this.valueField = this._select.dataset.cfValueField || "id";
        this.labelField = this._select.dataset.cfLabelField || "display";
        this.disabledField = this._select.dataset.cfDisabledField || "";
        this.descriptionField =
          this._select.dataset.cfDescriptionField || "description";
        this.depthField = this._select.dataset.cfDepthField || "_depth";
        this.parentField = this._select.dataset.cfParentField || "";
        this.countField = this._select.dataset.cfCountField || "";
        this.extraColumns = (this._select.dataset.cfExtraColumnsField || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        this.parseParams();
        this.setupDependencies();
        this.options = []; // populated server-side on load
      } else {
        const opts = Array.from(this._select.options).map((o) => ({
          value: o.value,
          label: o.textContent || "",
        }));
        // A blank choice is a placeholder, not a selectable value: show its
        // label when the trigger is empty and keep it out of the selectable
        // options list.
        const blank = opts.find((o) => o.value === "" || o.value === "unknown");
        if (blank) {
          this.placeholder = blank.label || this.placeholder;
          this.options = opts.filter((o) => o !== blank);
        } else {
          this.options = opts;
        }
      }

      // Quick-add / object-selector push an externally created option in via
      // this custom event (dispatched on the hidden sink), then select it.
      this._select.addEventListener("cf-select:add-option", (e: Event) => {
        const detail = (e as CustomEvent).detail;
        const value = detail?.value;
        const label = detail?.label;
        if (!value || !label) return;
        if (!this.options.some((o) => o.value === value)) {
          this.options.push({ value, label });
        }
        this.selectOption({ value, label });
      });
    },

    parseParams() {
      try {
        const sp = JSON.parse(this._select?.dataset.staticParams || "[]");
        if (Array.isArray(sp)) {
          for (const { queryParam, queryValue } of sp) {
            this.staticParams[queryParam] = Array.isArray(queryValue)
              ? queryValue
              : [queryValue];
          }
        }
      } catch {
        /* ignore malformed JSON */
      }
      this.queryParams = { ...this.staticParams };
      try {
        const dp = JSON.parse(this._select?.dataset.dynamicParams || "[]");
        if (Array.isArray(dp)) {
          this.dynamicParams = dp
            .filter((d) => d?.fieldName && d.queryParam)
            .map((d) => ({ fieldName: d.fieldName, queryParam: d.queryParam }));
        }
      } catch {
        /* ignore */
      }
      for (const m of this.apiUrl.matchAll(/\{\{(.+?)\}\}/g)) {
        this.pathValues[m[1]] = "";
      }
    },

    setupDependencies() {
      const deps = new Set([
        ...this.dynamicParams.map((d) => d.fieldName),
        ...Object.keys(this.pathValues),
      ]);
      for (const dep of deps) {
        const el = document.querySelector(`[name="${dep}"]`);
        if (el) el.addEventListener("change", () => this.handleDependency(dep));
      }
    },

    handleDependency(dep: string) {
      this.updateQueryParams(dep);
      this.updatePathValues(dep);
      this.selected = [];
      this.writeBack();
      this.load(this.lastSearch || "");
    },

    updateQueryParams(fieldName: string) {
      const el = document.querySelector<HTMLSelectElement>(
        `[name="${fieldName}"]`,
      );
      if (!el) return;
      let values: string[] = [];
      if (el.multiple) {
        values = Array.from(el.options)
          .filter((o) => o.selected)
          .map((o) => o.value);
      } else if (el.value !== "") {
        values = [el.value];
      }
      const dp = this.dynamicParams.find((d) => d.fieldName === fieldName);
      if (!dp) return;
      const { queryParam } = dp;
      let value: string[];
      if (this.staticParams[queryParam]) {
        value = [...this.staticParams[queryParam], ...values];
      } else {
        value = values;
      }
      if (value.length) this.queryParams[queryParam] = value;
      else delete this.queryParams[queryParam];
    },

    updatePathValues(id: string) {
      const el = document.querySelector<HTMLSelectElement>(`[name="${id}"]`);
      if (!el) return;
      if (this.apiUrl.includes(`{{${id}}}`)) {
        this.pathValues[id] = el.value || "";
      }
    },

    filtered(): CfOption[] {
      if (this.remote) return this.options;
      if (this.noSearch) return this.options;
      if (!this.search) return this.options;
      const q = this.search.toLowerCase();
      return this.options.filter((o) => o.label.toLowerCase().includes(q));
    },

    renderOption(option: CfOption): string {
      if (this.colorMode) {
        return `<span class="badge badge-${option.value}"></span> <span>${escapeHtml(option.label)}</span>`;
      }
      if (this.remote) {
        let html = "";
        if (option.extraColumns?.length) html = '<div class="flex">';
        html += '<div class="flex-1">';
        if (typeof option.depth === "number" && option.depth > 0) {
          html += `${"─".repeat(option.depth)} `;
        }
        html += escapeHtml(option.label);
        if (option.parent) {
          html += ` <span class="text-base-content/50">${escapeHtml(option.parent)}</span>`;
        }
        if (option.count) {
          html += ` <span class="badge badge-ghost">${escapeHtml(String(option.count))}</span>`;
        }
        if (option.description) {
          html += `<br><small class="text-base-content/50">${escapeHtml(option.description)}</small>`;
        }
        html += "</div>";
        if (option.extraColumns?.length) {
          for (const col of option.extraColumns) {
            html += `<div class="flex-1">${escapeHtml(col)}</div>`;
          }
          html += "</div>";
        }
        return html;
      }
      return escapeHtml(option.label);
    },

    toggle() {
      if (this.disabled) return;
      if (this.open) this.close();
      else this.openDropdown();
    },

    openDropdown() {
      if (this.disabled) return;
      this.open = true;
      this.focusSearch();
      if (this.remote && this.search !== this.lastSearch)
        this.load(this.search);
      if (this.activeIndex < 0 && this.filtered().length > 0) {
        this.activeIndex = 0;
      }
    },

    close(focusTrigger = true) {
      this.open = false;
      this.activeIndex = -1;
      if (this.search) this.search = "";
      if (focusTrigger) {
        this.$el.querySelector<HTMLElement>("[data-cf-trigger]")?.focus();
      }
    },

    focusSearch() {
      if (this.noSearch) return;
      // The panel is hidden via x-show (display:none) until Alpine applies
      // reactivity, so defer the focus to the next tick.
      Alpine.nextTick(() => {
        this.$el.querySelector<HTMLInputElement>("[data-cf-search]")?.focus();
      });
    },

    onSearch(e: Event) {
      if (this.noSearch) return;
      if (!this.remote) return;
      const value = (e.target as HTMLInputElement).value;
      this.search = value;
      window.clearTimeout(this._searchTimer);
      this._searchTimer = window.setTimeout(() => this.load(this.search), 300);
    },

    load(search: string) {
      if (!this.apiUrl) return;
      const url = this.getRequestUrl(search);
      if (!url) return;
      this._abort?.abort();
      this._abort = new AbortController();
      this.loading = true;
      this.activeIndex = -1;
      this.options = [];
      if (!search && this.nullOption) {
        this.options.push({ value: "null", label: this.nullOption });
      }
      fetch(url, { signal: this._abort.signal })
        .then((r) => r.json())
        .then((data) => {
          this.options = this.parseResults(
            (data.results || []) as Record<string, unknown>[],
          );
          if (!search && this.nullOption) {
            this.options.unshift({ value: "null", label: this.nullOption });
          }
          this.loading = false;
        })
        .catch(() => {
          this.loading = false;
        });
      this.lastSearch = search;
    },

    getRequestUrl(search: string): string {
      let url = this.apiUrl;
      for (const [key, value] of Object.entries(this.pathValues)) {
        if (this.apiUrl.includes(`{{${key}}}`)) {
          if (value) url = url.replaceAll(`{{${key}}}`, String(value));
          else return "";
        }
      }
      const u = new URL(url, location.origin);
      for (const [key, vals] of Object.entries(this.queryParams)) {
        for (const v of vals) u.searchParams.append(key, v);
      }
      if (search) u.searchParams.append("q", search);
      u.searchParams.append("brief", "true");
      u.searchParams.append("limit", String(this.maxOptions));
      return u.toString();
    },

    parseResults(results: Record<string, unknown>[]): CfOption[] {
      return results.map((r) => {
        const o: CfOption = {
          value: String(r[this.valueField] ?? ""),
          label: String(r[this.labelField] ?? ""),
          depth:
            typeof r[this.depthField] === "number"
              ? (r[this.depthField] as number)
              : null,
          description:
            r[this.descriptionField] != null
              ? String(r[this.descriptionField])
              : null,
          extraColumns: null,
        };
        if (this.parentField && r[this.parentField]) {
          const parent = r[this.parentField] as Record<string, unknown>;
          o.parent = String(parent[this.labelField] ?? parent);
        }
        if (this.countField && r[this.countField]) {
          o.count = r[this.countField] as number | string;
        }
        if (this.disabledField && r[this.disabledField]) {
          o.disabled = true;
        }
        if (this.extraColumns.length) {
          const cols: string[] = [];
          for (const col of this.extraColumns) {
            cols.push(r[col] != null ? String(r[col]) : "-");
          }
          o.extraColumns = cols;
        }
        return o;
      });
    },

    selectOption(option: CfOption) {
      if (this.disabled || option.disabled) return;
      if (this.multiple) {
        const i = this.selected.findIndex((s) => s.value === option.value);
        if (i >= 0) this.selected.splice(i, 1);
        else this.selected.push(option);
      } else {
        this.selected = [option];
        this.close();
      }
      this.writeBack();
    },

    removeItem(value: string) {
      if (this.disabled) return;
      this.selected = this.selected.filter((s) => s.value !== value);
      this.writeBack();
    },

    clear() {
      if (this.disabled) return;
      this.selected = [];
      this.writeBack();
    },

    writeBack() {
      const select = this._select;
      if (!select) return;
      for (const option of select.options) {
        option.selected = false;
      }
      for (const s of this.selected) {
        let opt = Array.from(select.options).find((o) => o.value === s.value);
        if (!opt) {
          // Remote selections may not be present in the hidden sink yet.
          opt = document.createElement("option");
          opt.value = s.value;
          opt.text = s.label;
          select.appendChild(opt);
        }
        opt.selected = true;
      }
      select.dispatchEvent(new Event("change", { bubbles: true }));
      this.invalid = false;
    },

    keydown(e: KeyboardEvent) {
      if (this.disabled) return;
      // Printable characters: let typing proceed on the search input; typing
      // on the trigger (div combobox) opens the popup and moves focus to search.
      if (e.key.length === 1) {
        if ((e.target as HTMLElement).matches("[data-cf-search]")) return;
        e.preventDefault();
        if (!this.open) this.openDropdown();
        else this.focusSearch();
        return;
      }
      const list = this.filtered();
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          if (!this.open) this.openDropdown();
          this.activeIndex = Math.min(this.activeIndex + 1, list.length - 1);
          break;
        case "ArrowUp":
          e.preventDefault();
          this.activeIndex = Math.max(this.activeIndex - 1, 0);
          break;
        case "Home":
          e.preventDefault();
          this.activeIndex = 0;
          break;
        case "End":
          e.preventDefault();
          this.activeIndex = list.length - 1;
          break;
        case "Enter":
          e.preventDefault();
          if (this.open && this.activeIndex >= 0 && list[this.activeIndex]) {
            this.selectOption(list[this.activeIndex]);
          } else {
            this.openDropdown();
          }
          break;
        case "Escape":
          this.close();
          break;
        case "Tab":
          this.close();
          break;
      }
    },
  }));
}
